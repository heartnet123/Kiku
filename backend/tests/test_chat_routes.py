from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_session_crud_routes():
    # Login as admin@acme.com
    login_resp = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "admin123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

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
    login_resp = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "admin123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

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

