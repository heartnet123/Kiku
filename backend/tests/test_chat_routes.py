from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.core.auth import AuthenticatedMemberContext
from app.domain.identity import Role, User, Workspace, WorkspaceMember
from app.main import app

client = TestClient(app)


def _mock_verify_supabase_token(token: str) -> User:
    return User(id="user_acme_admin", email="admin@acme.com", full_name="Admin User", password_hash="")


def _mock_get_authenticated_member(workspace_id: str, user: User, access_token: str | None = None, required_role: Role | None = None) -> AuthenticatedMemberContext:
    return AuthenticatedMemberContext(
        user=user,
        membership=WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=Role.ADMIN, joined_at="2026-01-01T00:00:00Z"),
        workspace=Workspace(id=workspace_id, name="Acme Workspace", slug="acme"),
    )


@pytest.fixture(autouse=True)
def setup_auth_mocks(monkeypatch):
    monkeypatch.setattr("app.core.auth._verify_supabase_token", _mock_verify_supabase_token)
    monkeypatch.setattr("app.core.auth.get_authenticated_member", _mock_get_authenticated_member)


def test_chat_session_crud_routes():
    headers = {"Authorization": "Bearer token_admin_acme"}

    # Create session
    resp = client.post("/api/v1/workspaces/ws_acme/chat/sessions", json={"title": "My Chat"}, headers=headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["title"] == "My Chat"
    session_id = data["id"]
    
    # List sessions
    list_resp = client.get("/api/v1/workspaces/ws_acme/chat/sessions", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
    
    # Delete session
    del_resp = client.delete(f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 200


def test_chat_stream_endpoint_returns_sse():
    """G3: Verify the stream endpoint returns text/event-stream and contains expected SSE events."""
    headers = {"Authorization": "Bearer token_admin_acme"}

    # Create a session to stream into
    session_resp = client.post(
        "/api/v1/workspaces/ws_acme/chat/sessions", json={"title": "Stream Test"}, headers=headers
    )
    assert session_resp.status_code in (200, 201)
    session_id = session_resp.json()["id"]

    # Stream a message — use stream=True so TestClient reads the body incrementally
    with client.stream(
        "POST",
        f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}/stream",
        json={"query": "What is Kiku?", "category": None},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        body = response.read().decode("utf-8")
        assert "event: metadata" in body
        assert "event: done" in body

    # Cleanup
    client.delete(f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}", headers=headers)


