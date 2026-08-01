from fastapi.testclient import TestClient
import pytest

from app.core.audit import clear_audit_logs, get_workspace_audit_logs
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_logs():
    clear_audit_logs()


def test_login_success_and_failure():
    # Success
    resp = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["email"] == "admin@acme.com"
    assert len(data["workspaces"]) >= 1

    # Failure
    fail_resp = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "wrongpassword"})
    assert fail_resp.status_code == 401
    assert "Invalid email or password" in fail_resp.json()["detail"]


def test_unauthenticated_request_rejected():
    endpoints = [
        ("POST", "/api/v1/workspaces/ws_acme/search", {"query": "billing"}),
        ("GET", "/api/v1/workspaces/ws_acme/sources", None),
        ("POST", "/api/v1/workspaces/ws_acme/feedback", {"query": "billing", "rating": 5}),
        ("GET", "/api/v1/workspaces/ws_acme/members", None),
        ("POST", "/api/v1/workspaces/ws_acme/members/invite", {"email": "new@acme.com", "role": "member"}),
    ]

    for method, url, payload in endpoints:
        if method == "GET":
            resp = client.get(url)
        else:
            resp = client.post(url, json=payload)
        assert resp.status_code == 401, f"Expected 401 for unauthenticated {method} {url}"


def test_cross_workspace_read_write_blocked():
    # Login as Globex Admin
    login_resp = client.post("/api/v1/auth/login", json={"email": "admin@globex.com", "password": "admin123"})
    globex_token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {globex_token}"}

    # Attempt to access Acme Team (ws_acme) resources
    search_resp = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "secret docs"},
        headers=headers,
    )
    assert search_resp.status_code == 403

    sources_resp = client.get("/api/v1/workspaces/ws_acme/sources", headers=headers)
    assert sources_resp.status_code == 403

    members_resp = client.get("/api/v1/workspaces/ws_acme/members", headers=headers)
    assert members_resp.status_code == 403

    invite_resp = client.post(
        "/api/v1/workspaces/ws_acme/members/invite",
        json={"email": "hacker@globex.com", "role": "admin"},
        headers=headers,
    )
    assert invite_resp.status_code == 403


def test_role_based_access_control():
    # Acme Member token
    login_member = client.post("/api/v1/auth/login", json={"email": "member@acme.com", "password": "member123"})
    member_token = login_member.json()["token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Member can search and view sources
    assert client.post("/api/v1/workspaces/ws_acme/search", json={"query": "plan"}, headers=member_headers).status_code == 200
    assert client.get("/api/v1/workspaces/ws_acme/sources", headers=member_headers).status_code == 200

    # Member CANNOT invite or manage roles
    invite_resp = client.post(
        "/api/v1/workspaces/ws_acme/members/invite",
        json={"email": "guest@acme.com", "role": "member"},
        headers=member_headers,
    )
    assert invite_resp.status_code == 403

    role_resp = client.patch(
        "/api/v1/workspaces/ws_acme/members/user_acme_admin/role",
        json={"role": "member"},
        headers=member_headers,
    )
    assert role_resp.status_code == 403

    audit_resp = client.get("/api/v1/workspaces/ws_acme/audit-logs", headers=member_headers)
    assert audit_resp.status_code == 403


def test_audited_member_management():
    # Login as Acme Admin
    login_admin = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "admin123"})
    admin_token = login_admin.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Invite new member
    invite_resp = client.post(
        "/api/v1/workspaces/ws_acme/members/invite",
        json={"email": "alice@acme.com", "role": "member"},
        headers=admin_headers,
    )
    assert invite_resp.status_code == 201
    new_user_id = invite_resp.json()["user_id"]

    # 2. Change role to admin
    role_resp = client.patch(
        f"/api/v1/workspaces/ws_acme/members/{new_user_id}/role",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert role_resp.status_code == 200
    assert role_resp.json()["role"] == "admin"

    # 3. Remove member
    del_resp = client.delete(
        f"/api/v1/workspaces/ws_acme/members/{new_user_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 204

    # 4. Verify audit logs
    audit_resp = client.get("/api/v1/workspaces/ws_acme/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    actions = [l["action"] for l in logs]
    assert "MEMBER_INVITED" in actions
    assert "ROLE_UPDATED" in actions
    assert "MEMBER_REMOVED" in actions

    # Verify no raw password or secret is in audit log details
    for log in logs:
        assert "password" not in log["details"]
        assert "token" not in log["details"]
