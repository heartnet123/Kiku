import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _mock_login_response():
    user = MagicMock()
    user.id = "user-123"
    user.email = "test@example.com"
    user.user_metadata = {"full_name": "Test User"}
    session = MagicMock()
    session.access_token = "fake.jwt.token"
    session.refresh_token = "fake-refresh"
    response = MagicMock()
    response.user = user
    response.session = session
    return response


def test_login_sets_httponly_cookies(client):
    mock_resp = _mock_login_response()
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        sb = MagicMock()
        sb.auth.sign_in_with_password.return_value = mock_resp
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = sb
        r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "pw"})

    assert r.status_code == 200
    set_cookie_headers = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
    access_header = next((h for h in set_cookie_headers if "kiku_access_token" in h), "")
    assert "HttpOnly" in access_header
    assert "SameSite=lax" in access_header.lower() or "samesite=lax" in access_header.lower()


def test_logout_clears_cookies(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code in (200, 204)
    set_cookie_headers = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
    access_header = next((h for h in set_cookie_headers if "kiku_access_token" in h), "")
    assert "Max-Age=0" in access_header or "max-age=0" in access_header.lower()
