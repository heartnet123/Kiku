from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.core.auth import AuthenticatedMemberContext
from app.domain.identity import Role, User, Workspace, WorkspaceMember
from app.main import app
from app.services.chat_storage import ChatStorageService

client = TestClient(app)


def _mock_verify_supabase_token(token: str) -> User:
    if "wrong_user" in token:
        return User(id="user_wrong", email="wrong@acme.com", full_name="Wrong User", password_hash="")
    return User(id="user_acme_admin", email="admin@acme.com", full_name="Admin User", password_hash="")


def _mock_get_authenticated_member(
    workspace_id: str,
    user: User,
    access_token: str | None = None,
    required_role: Role | None = None,
) -> AuthenticatedMemberContext:
    if "denied" in (access_token or "") or user.id == "user_wrong":
        raise HTTPException(status_code=403, detail="Access denied. Not a member of workspace.")
    if workspace_id == "ws_other":
        raise HTTPException(status_code=403, detail="Access denied. Workspace mismatch.")

    return AuthenticatedMemberContext(
        user=user,
        membership=WorkspaceMember(
            workspace_id=workspace_id, user_id=user.id, role=Role.ADMIN, joined_at="2026-01-01T00:00:00Z"
        ),
        workspace=Workspace(id=workspace_id, name="Acme Workspace", slug="acme"),
    )


@pytest.fixture(autouse=True)
def setup_auth_mocks(monkeypatch):
    monkeypatch.setattr("app.core.auth._verify_supabase_token", _mock_verify_supabase_token)
    monkeypatch.setattr("app.core.auth.get_authenticated_member", _mock_get_authenticated_member)
    monkeypatch.setattr("app.api.v1.routes.chat.chat_storage_service", ChatStorageService(in_memory=True))


def test_chat_session_crud_routes():
    headers = {"Authorization": "Bearer token_admin_acme"}

    # Create session
    resp = client.post("/api/v1/workspaces/ws_acme/chat/sessions", json={"title": "My Chat"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Chat"
    session_id = data["id"]

    # List sessions and verify created session is present
    list_resp = client.get("/api/v1/workspaces/ws_acme/chat/sessions", headers=headers)
    assert list_resp.status_code == 200
    listed_ids = [s["id"] for s in list_resp.json()]
    assert session_id in listed_ids

    # Delete session
    del_resp = client.delete(f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 200

    # Fetch collection after deletion and verify session_id is absent
    post_del_resp = client.get("/api/v1/workspaces/ws_acme/chat/sessions", headers=headers)
    assert post_del_resp.status_code == 200
    post_listed_ids = [s["id"] for s in post_del_resp.json()]
    assert session_id not in post_listed_ids


def test_chat_stream_endpoint_returns_sse_and_persists_messages():
    """Verify stream endpoint returns text/event-stream, streams deterministic chunks, and persists messages."""
    headers = {"Authorization": "Bearer token_admin_acme"}

    # Create a session to stream into
    session_resp = client.post(
        "/api/v1/workspaces/ws_acme/chat/sessions", json={"title": "Stream Test"}, headers=headers
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    # Mock external LLM response lines for httpx AsyncClient
    async def mock_aiter_lines():
        yield 'data: {"choices":[{"delta":{"content":"Kiku is a "}}]}'
        yield 'data: {"choices":[{"delta":{"content":"knowledge synthesis system."}}]}'
        yield 'data: [DONE]'

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    class MockStreamContext:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_client = MagicMock()
    mock_client.stream.return_value = MockStreamContext()

    class MockClientContext:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient", return_value=MockClientContext()):
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

    # Fetch session's /messages endpoint and verify persisted user query & assistant response
    msg_resp = client.get(f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}/messages", headers=headers)
    assert msg_resp.status_code == 200
    messages = msg_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is Kiku?"
    assert messages[1]["role"] == "assistant"
    assert "Kiku is a knowledge synthesis system." in messages[1]["content"]

    # Cleanup
    client.delete(f"/api/v1/workspaces/ws_acme/chat/sessions/{session_id}", headers=headers)


def test_chat_routes_negative_authorization():
    """Verify requests with non-member token or wrong workspace receive authorization denials."""
    denied_headers = {"Authorization": "Bearer token_denied"}

    # Non-member access request
    resp = client.get("/api/v1/workspaces/ws_acme/chat/sessions", headers=denied_headers)
    assert resp.status_code == 403

    # Access to wrong workspace
    admin_headers = {"Authorization": "Bearer token_admin_acme"}
    wrong_ws_resp = client.get("/api/v1/workspaces/ws_other/chat/sessions", headers=admin_headers)
    assert wrong_ws_resp.status_code == 403
