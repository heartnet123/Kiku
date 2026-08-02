from fastapi.testclient import TestClient
import pytest
from unittest.mock import MagicMock, patch

from app.core.audit import clear_audit_logs, record_audit_event
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    clear_audit_logs()
    yield
    clear_audit_logs()


def _assert_no_sensitive_keys_recursive(data):
    sensitive_keys = {"password", "token", "credentials", "bearer", "secret", "password_hash"}
    if isinstance(data, dict):
        for k, v in data.items():
            assert k.lower() not in sensitive_keys, f"Found sensitive key '{k}' in audit details"
            _assert_no_sensitive_keys_recursive(v)
    elif isinstance(data, list):
        for item in data:
            _assert_no_sensitive_keys_recursive(item)


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


def test_login_requires_supabase():
    with patch("app.api.v1.routes.auth_routes.create_supabase_client", return_value=None):
        resp = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrongpassword"})
        assert resp.status_code == 503


def test_login_invalid_credentials():
    supabase_mock = MagicMock()
    supabase_mock.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
    with patch("app.api.v1.routes.auth_routes.create_supabase_client", return_value=supabase_mock):
        resp = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrongpassword"})
        assert resp.status_code == 401


def test_recursive_audit_sanitization():
    nested_payload = {
        "auth": {
            "password": "secret_password",
            "token": "secret_token",
            "nested": {
                "bearer": "secret_bearer",
                "safe_field": "visible_value",
            },
        }
    }
    event = record_audit_event("user_1", "ws_acme", "TEST_EVENT", details=nested_payload)
    _assert_no_sensitive_keys_recursive(event.details)
    assert event.details["auth"]["nested"]["safe_field"] == "visible_value"


def test_refresh_session_request_body():
    query_resp = client.post("/api/v1/auth/refresh?refresh_token=dummy_token")
    assert query_resp.status_code == 422

    supabase_mock = MagicMock()
    supabase_mock.auth.refresh_session.side_effect = Exception("invalid token")

    with patch(
        "app.api.v1.routes.auth_routes.create_supabase_client",
        return_value=supabase_mock,
    ):
        json_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "dummy_token"})

    assert json_resp.status_code == 401
    supabase_mock.auth.refresh_session.assert_called_once_with("dummy_token")
