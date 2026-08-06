import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace
from time import time
from unittest.mock import patch, MagicMock
import app.core.rate_limit as rate_limit_module


@pytest.fixture
def client():
    # Clear module-level store so each test starts with a clean slate
    rate_limit_module._store.clear()
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _login_payload():
    return {"email": "test@example.com", "password": "pw"}


def _patch_login_supabase(mock_sb):
    mock_resp = MagicMock()
    mock_resp.user = MagicMock()
    mock_resp.user.id = "test-id"
    mock_resp.session = MagicMock()
    mock_resp.session.access_token = "test-token"
    mock_resp.session.refresh_token = "test-refresh"
    sb = MagicMock()
    sb.auth.sign_in_with_password.return_value = mock_resp
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    mock_sb.return_value = sb


def test_rate_limit_auth_endpoint(client):
    """11th POST /api/v1/auth/login from same client returns 429 with Retry-After."""
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        _patch_login_supabase(mock_sb)

        for i in range(10):
            r = client.post("/api/v1/auth/login", json=_login_payload())
            assert r.status_code == 200, f"Request {i+1} should succeed"

        r = client.post("/api/v1/auth/login", json=_login_payload())
        assert r.status_code == 429
        assert "Rate limit exceeded" in r.json()["detail"]
        assert "Retry-After" in r.headers


def test_rate_limited_response_exposes_retry_after(client):
    """Rate-limited responses expose Retry-After to allowed browser origins."""
    from app.core.config import settings

    origin = settings.frontend_origin
    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        _patch_login_supabase(mock_sb)

        for i in range(10):
            r = client.post("/api/v1/auth/login", json=_login_payload(), headers={"Origin": origin})
            assert r.status_code == 200, f"Request {i+1} should succeed"

        r = client.post("/api/v1/auth/login", json=_login_payload(), headers={"Origin": origin})

    assert r.status_code == 429
    assert r.headers.get("access-control-allow-origin") == origin
    assert "Retry-After" in r.headers.get("access-control-expose-headers", "")


def _fake_request(method: str, path: str, host: str = "testclient"):
    return SimpleNamespace(
        method=method,
        url=SimpleNamespace(path=path),
        client=SimpleNamespace(host=host),
    )


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("POST", "/api/v1/search", "expensive-ai"),
        ("POST", "/api/v1/workspaces/ws-123/search", "expensive-ai"),
        ("POST", "/api/v1/workspaces/ws-123/chat/sessions", "expensive-ai"),
        ("POST", "/api/v1/workspaces/ws-123/chat/sessions/sess-456/stream", "expensive-ai"),
        ("POST", "/api/v1/workspaces/ws-123/sources", "upload"),
        ("POST", "/api/v1/auth/login", "auth"),
        ("POST", "/api/v1/workspaces", "workspace-write"),
        ("POST", "/api/v1/workspaces/join", "workspace-write"),
        ("GET", "/api/v1/workspaces/ws-123/sources", None),
        ("POST", "/api/v1/workspaces/ws-123/members/invite", None),
        ("POST", "/api/v1/workspaces/ws-123/sources/src-9/retry", None),
        ("POST", "/api/v1/health", None),
    ],
)
def test_match_rule_dynamic_endpoints(method, path, expected):
    """Dynamic workspace/session endpoints resolve to the right rules; others pass through."""
    assert rate_limit_module._match_rule(method, path) == expected


def test_retry_after_rounds_up_and_is_positive(client):
    """Retry-After never drops to 0 while the oldest request is still inside the window."""
    oldest = time() - (rate_limit_module._window_seconds - 0.2)
    rate_limit_module._store["testclient:auth"] = [oldest] * 10

    try:
        retry_after = rate_limit_module.check_rate_limit(_fake_request("POST", "/api/v1/auth/login"))
        assert retry_after == 1
    finally:
        rate_limit_module._store.clear()
