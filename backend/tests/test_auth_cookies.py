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


def _assert_access_cookie_hardened(response):
    set_cookie_headers = [v for k, v in response.headers.items() if k.lower() == "set-cookie"]
    access_header = next((h for h in set_cookie_headers if "kiku_access_token" in h), "")
    assert "HttpOnly" in access_header
    assert "samesite=lax" in access_header.lower()


def _assert_refresh_cookie_hardened(response):
    set_cookie_headers = [v for k, v in response.headers.items() if k.lower() == "set-cookie"]
    refresh_header = next((h for h in set_cookie_headers if "kiku_refresh_token" in h), "")
    assert "HttpOnly" in refresh_header
    assert "samesite=lax" in refresh_header.lower()
    assert "path=/" in refresh_header.lower()


def test_login_sets_httponly_cookies(client):
    mock_resp = _mock_login_response()
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        sb = MagicMock()
        sb.auth.sign_in_with_password.return_value = mock_resp
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = sb
        r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "pw"})

    assert r.status_code == 200
    assert "refresh_token" not in r.json()
    set_cookie_headers = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
    access_header = next((h for h in set_cookie_headers if "kiku_access_token" in h), "")
    assert "HttpOnly" in access_header
    assert "SameSite=lax" in access_header.lower() or "samesite=lax" in access_header.lower()
    _assert_refresh_cookie_hardened(r)

def test_register_sets_httponly_cookies(client):
    mock_resp = _mock_login_response()
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        sb = MagicMock()
        sb.auth.sign_up.return_value = mock_resp
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = sb
        r = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password1", "full_name": "Test User"},
        )

    assert r.status_code == 201
    assert "refresh_token" not in r.json()
    _assert_access_cookie_hardened(r)
    _assert_refresh_cookie_hardened(r)

def test_refresh_reads_refresh_cookie(client):
    """POST /auth/refresh must work off the HttpOnly cookie with no request body token."""
    mock_resp = _mock_login_response()
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        sb = MagicMock()
        sb.auth.refresh_session.return_value = mock_resp
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = sb
        r = client.post(
            "/api/v1/auth/refresh",
            json={},
            cookies={"kiku_refresh_token": "cookie-refresh"},
        )
        sb.auth.refresh_session.assert_called_once_with("cookie-refresh")

    assert r.status_code == 200
    assert "refresh_token" not in r.json()
    _assert_access_cookie_hardened(r)
    _assert_refresh_cookie_hardened(r)

def test_refresh_without_token_is_unauthorized(client):
    r = client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 401


def test_logout_clears_cookies(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code in (200, 204)
    set_cookie_headers = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
    access_header = next((h for h in set_cookie_headers if "kiku_access_token" in h), "")
    assert "Max-Age=0" in access_header or "max-age=0" in access_header.lower()


def test_logout_revokes_supabase_session(client):
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        admin = MagicMock()
        mock_sb.return_value = admin
        r = client.post("/api/v1/auth/logout", cookies={"kiku_access_token": "tok-abc"})
        mock_sb.assert_called_once_with(service_role=True)
        admin.auth.admin.sign_out.assert_called_once_with("tok-abc")

    assert r.status_code == 204


def test_logout_reports_revocation_failure_but_still_clears_cookies(client):
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        admin = MagicMock()
        admin.auth.admin.sign_out.side_effect = RuntimeError("gotrue down")
        mock_sb.return_value = admin
        r = client.post("/api/v1/auth/logout", cookies={"kiku_access_token": "tok-abc"})

    assert r.status_code == 502
    set_cookie_headers = [v for k, v in r.headers.items() if k.lower() == "set-cookie"]
    access_header = next((h for h in set_cookie_headers if "kiku_access_token" in h), "")
    assert "Max-Age=0" in access_header or "max-age=0" in access_header.lower()


def test_me_endpoint_reads_cookie(client):
    """GET /auth/me must work when token arrives via cookie, not Bearer header."""
    fake_token = "h.eyJzdWIiOiJ1c2VyLTEyMyIsImV4cCI6OTk5OTk5OTk5OX0.sig"
    with patch("app.core.auth._verify_supabase_token") as mock_verify:
        from app.domain.identity import User
        mock_verify.return_value = User(id="u1", email="t@t.com", full_name="T", password_hash="")
        with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
            sb = MagicMock()
            sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            mock_sb.return_value = sb
            r = client.get("/api/v1/auth/me", cookies={"kiku_access_token": fake_token})
    assert r.status_code == 200
