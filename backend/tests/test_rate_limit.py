import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import app.core.rate_limit as rate_limit_module


@pytest.fixture
def client():
    # Clear module-level store so each test starts with a clean slate
    rate_limit_module._store.clear()
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_rate_limit_auth_endpoint(client):
    """11th POST /api/v1/auth/login from same client returns 429 with Retry-After."""
    mock_resp = MagicMock()
    mock_resp.user = MagicMock()
    mock_resp.user.id = "test-id"
    mock_resp.session = MagicMock()
    mock_resp.session.access_token = "test-token"
    mock_resp.session.refresh_token = "test-refresh"

    with patch("app.api.v1.routes.auth_routes.create_supabase_client") as mock_sb:
        sb = MagicMock()
        sb.auth.sign_in_with_password.return_value = mock_resp
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = sb

        for i in range(10):
            r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "pw"})
            assert r.status_code == 200, f"Request {i+1} should succeed"

        r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "pw"})
        assert r.status_code == 429
        assert "Rate limit exceeded" in r.json()["detail"]
        assert "Retry-After" in r.headers
