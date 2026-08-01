import pytest
from fastapi.testclient import TestClient

from app.core.audit import clear_audit_logs
from app.core.auth import DEMO_MEMBERSHIPS, DEMO_USERS, _TOKENS
from app.domain.knowledge import FileType
from app.main import app
from app.services.supabase_storage import storage_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_state():
    users_snapshot = DEMO_USERS.copy()
    memberships_snapshot = DEMO_MEMBERSHIPS.copy()
    tokens_snapshot = _TOKENS.copy()
    storage_service.clear_all()
    clear_audit_logs()

    yield

    DEMO_USERS.clear()
    DEMO_USERS.update(users_snapshot)
    DEMO_MEMBERSHIPS.clear()
    DEMO_MEMBERSHIPS.update(memberships_snapshot)
    _TOKENS.clear()
    _TOKENS.update(tokens_snapshot)
    storage_service.clear_all()
    clear_audit_logs()


def _get_admin_headers():
    resp = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _get_member_headers():
    resp = client.post("/api/v1/auth/login", json={"email": "member@acme.com", "password": "member123"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


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

    # Query 1: Security intent
    res1 = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "What is the 2FA rule?"},
        headers=member_headers,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert "2FA authentication" in data1["answer"] or "Security Policy" in data1["answer"]
    assert data1["source"]["title"] == "Security Policy"

    # Query 2: Travel Expense intent
    res2 = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "What is the meals reimbursement limit?"},
        headers=member_headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert "$75 per day" in data2["answer"] or "Travel Policy" in data2["answer"]
    assert data2["source"]["title"] == "Travel Policy"

    # Confirm different queries produced different answers and citations
    assert data1["answer"] != data2["answer"]
    assert data1["source"]["id"] != data2["source"]["id"]


def test_category_filtering_restricts_retrieval_scope():
    """Verify selecting a category restricts the retrieval scope to relevant sources."""
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
