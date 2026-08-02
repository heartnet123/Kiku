import pytest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.audit import clear_audit_logs
from app.core.auth import AuthenticatedMemberContext
from app.domain.identity import Role, User, Workspace, WorkspaceMember
from app.domain.knowledge import FileType
from app.main import app
from app.services.supabase_storage import storage_service

client = TestClient(app)

_member_workspaces = ["ws_acme"]


def _mock_verify_supabase_token(token: str) -> User:
    if "admin" in token:
        user_id = "user_globex_admin" if "globex" in token else "user_acme_admin"
        email = "admin@globex.com" if "globex" in token else "admin@acme.com"
        return User(id=user_id, email=email, full_name="Admin", password_hash="")
    return User(id="user_acme_member", email="member@acme.com", full_name="Member", password_hash="")


def _mock_get_authenticated_member(workspace_id: str, user: User, access_token: str | None = None, required_role: Role | None = None) -> AuthenticatedMemberContext:
    is_globex_token = "globex" in (access_token or "")
    if workspace_id == "ws_acme" and is_globex_token:
        raise HTTPException(status_code=403, detail="Access denied")
    if workspace_id == "ws_globex" and not is_globex_token:
        raise HTTPException(status_code=403, detail="Access denied")

    role = Role.MEMBER if ("member" in (access_token or "") and not is_globex_token) else Role.ADMIN
    if required_role == Role.ADMIN and role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Operation requires ADMIN role")

    return AuthenticatedMemberContext(
        user=user,
        membership=WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role, joined_at="2026-01-01T00:00:00Z"),
        workspace=Workspace(id=workspace_id, name="Workspace", slug=workspace_id),
    )


def _mock_get_user_workspace_id(user: User, token: str) -> str:
    if len(_member_workspaces) > 1:
        raise HTTPException(status_code=409, detail="Multiple workspaces found. Use a workspace-scoped search endpoint.")
    if not _member_workspaces:
        raise HTTPException(status_code=403, detail="No workspace membership found.")
    return _member_workspaces[0]


@pytest.fixture(autouse=True)
def reset_test_state(monkeypatch):
    global _member_workspaces
    _member_workspaces = ["ws_acme"]
    monkeypatch.setattr("app.core.auth._verify_supabase_token", _mock_verify_supabase_token)
    monkeypatch.setattr("app.core.auth.get_authenticated_member", _mock_get_authenticated_member)
    monkeypatch.setattr("app.api.v1.routes.search.get_authenticated_member", _mock_get_authenticated_member)
    monkeypatch.setattr("app.api.v1.routes.search.get_user_workspace_id", _mock_get_user_workspace_id)
    storage_service.clear_all()
    clear_audit_logs()


    yield

    storage_service.clear_all()
    clear_audit_logs()


def _get_admin_headers():
    return {"Authorization": "Bearer token_admin_acme"}


def _get_member_headers():
    return {"Authorization": "Bearer token_member_acme"}


def test_query_dependent_answers_and_evidence():
    """Verify different intent queries return different evidence and answers."""
    admin_headers = _get_admin_headers()
    member_headers = _get_member_headers()

    # Upload Security document
    files_sec = {"file": ("security_policy.md", b"# Security Policy\n\nAll team members must use 2FA authentication for system access.", "text/markdown")}
    resp_sec = client.post("/api/v1/workspaces/ws_acme/sources", files=files_sec, headers=admin_headers)
    assert resp_sec.status_code == 201

    # Upload Travel Expense document
    files_exp = {"file": ("travel_policy.txt", b"Travel Expense Policy: Meals reimbursement maximum is $75 per day.", "text/plain")}
    resp_exp = client.post("/api/v1/workspaces/ws_acme/sources", files=files_exp, headers=admin_headers)
    assert resp_exp.status_code == 201

    admin_headers = _get_admin_headers()
    member_headers = _get_member_headers()

    # Upload Security doc
    client.post(
        "/api/v1/workspaces/ws_acme/sources",
        files={"file": ("security_guide.md", b"# Security Guidelines\n\nEnforce strict password complexity rules.", "text/markdown")},
        headers=admin_headers,
    )

    # Upload Billing doc
    client.post(
        "/api/v1/workspaces/ws_acme/sources",
        files={"file": ("billing_faq.txt", b"Billing FAQ: Payment invoices and rules for pricing are issued on the 1st of every month.", "text/plain")},
        headers=admin_headers,
    )

    # Search with Security category
    sec_resp = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "rules", "category": "Security"},
        headers=member_headers,
    )
    assert sec_resp.status_code == 200
    sec_data = sec_resp.json()
    assert sec_data["source"]["title"] == "Security Guide"
    assert "Billing" not in sec_data["answer"]

    # Search with Billing category
    bill_resp = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "rules", "category": "Billing"},
        headers=member_headers,
    )
    assert bill_resp.status_code == 200
    bill_data = bill_resp.json()
    assert bill_data["source"]["title"] == "Billing Faq"
    assert "Security" not in bill_data["answer"]


def test_no_evidence_behavior():
    """Verify queries with insufficient evidence return clear no-evidence status without fallback to seeded billing answer."""
    member_headers = _get_member_headers()

    # Search in empty workspace or for non-existent concept
    resp = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "quantum computing quantum teleportation algorithm"},
        headers=member_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Must NOT return hard-coded billing answer
    assert "upgrade your plan" not in data["answer"].lower()
    assert "settings > billing" not in data["details"].lower()

    # Must return explicit no-evidence response
    assert "couldn't find" in data["answer"].lower() or "no matching" in data["details"].lower()
    assert data["source"]["id"] == ""
    assert data["source"]["title"] is None


def test_search_endpoint_contracts():
    """Verify both workspace-scoped and top-level search endpoints return valid search responses."""
    member_headers = _get_member_headers()
    admin_headers = _get_admin_headers()

    # Ingest document
    client.post(
        "/api/v1/workspaces/ws_acme/sources",
        files={"file": ("onboarding.md", b"# Team Onboarding\n\nWelcome to the engineering team repository.", "text/markdown")},
        headers=admin_headers,
    )

    # Test workspace-scoped endpoint
    ws_resp = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "engineering team"},
        headers=member_headers,
    )
    assert ws_resp.status_code == 200
    assert ws_resp.json()["query"] == "engineering team"

    # Test top-level endpoint alias authorized
    top_resp = client.post(
        "/api/v1/search",
        json={"query": "engineering team"},
        headers=member_headers,
    )
    assert top_resp.status_code == 200
    assert top_resp.json()["query"] == "engineering team"

    # Test top-level endpoint alias unauthorized (missing token)
    unauth_resp = client.post(
        "/api/v1/search",
        json={"query": "engineering team"},
    )
    assert unauth_resp.status_code == 401


def test_top_level_search_alias_handles_membership_selection_and_revocation():
    """Verify the alias rejects ambiguous or revoked workspace memberships."""
    global _member_workspaces
    member_headers = _get_member_headers()

    _member_workspaces = ["ws_acme", "ws_globex"]

    ambiguous_resp = client.post(
        "/api/v1/search",
        json={"query": "engineering team"},
        headers=member_headers,
    )
    assert ambiguous_resp.status_code == 409

    _member_workspaces = ["ws_acme"]
    single_workspace_resp = client.post(
        "/api/v1/search",
        json={"query": "engineering team"},
        headers=member_headers,
    )
    assert single_workspace_resp.status_code == 200


    _member_workspaces = []
    revoked_resp = client.post(
        "/api/v1/search",
        json={"query": "engineering team"},
        headers=member_headers,
    )
    assert revoked_resp.status_code == 403

