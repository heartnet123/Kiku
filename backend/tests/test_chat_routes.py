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
    assert resp.status_code == 200
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
