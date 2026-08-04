import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_api_hardening_headers(client):
    """API responses include security headers and no-store cache on non-SSE endpoints."""
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    assert r.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"


def test_api_no_store_cache(client):
    """API endpoints under /api/v1 have Cache-Control: no-store."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers.get("Cache-Control") == "no-store"
    assert "Origin" in r.headers.get("Vary", "")

def test_invalid_environment_rejected():
    """Unknown KIKU_ENV values fail startup validation instead of acting like non-production."""
    from app.core.config import validate_runtime_settings
    class MockSettings:
        environment = "prod"
        frontend_origin = "http://localhost:5173"
    import app.core.config as config_module
    original_settings = config_module.settings
    config_module.settings = MockSettings()
    try:
        with pytest.raises(RuntimeError, match="KIKU_ENV"):
            validate_runtime_settings()
    finally:
        config_module.settings = original_settings


def test_production_config_validation():
    """validate_runtime_settings raises when production env has localhost origin."""
    from app.core.config import Settings, validate_runtime_settings
    class MockSettings:
        environment = "production"
        frontend_origin = "http://localhost:5173"
    import app.core.config as config_module
    original_settings = config_module.settings
    config_module.settings = MockSettings()
    try:
        with pytest.raises(RuntimeError, match="KIKU_FRONTEND_ORIGIN must be set to a production origin"):
            validate_runtime_settings()
    finally:
        config_module.settings = original_settings


def test_openapi_disabled_in_production():
    """enable_openapi is false when KIKU_ENV=production and KIKU_ENABLE_OPENAPI not set."""
    import os
    import importlib
    original_env = os.environ.get("KIKU_ENV")
    original_openapi = os.environ.get("KIKU_ENABLE_OPENAPI")
    os.environ["KIKU_ENV"] = "production"
    os.environ.pop("KIKU_ENABLE_OPENAPI", None)
    try:
        import app.core.config
        importlib.reload(app.core.config)
        from app.core.config import Settings
        settings = Settings()
        assert settings.enable_openapi is False
    finally:
        if original_env is not None:
            os.environ["KIKU_ENV"] = original_env
        else:
            os.environ.pop("KIKU_ENV", None)
        if original_openapi is not None:
            os.environ["KIKU_ENABLE_OPENAPI"] = original_openapi
        import app.core.config
        importlib.reload(app.core.config)
