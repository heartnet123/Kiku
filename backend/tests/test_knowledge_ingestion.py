import io
from fastapi.testclient import TestClient
import pytest

from app.core.audit import clear_audit_logs
from app.core.auth import DEMO_MEMBERSHIPS, DEMO_USERS, _TOKENS
from app.domain.knowledge import FileType, SourceStatus
from app.main import app
from app.services.ingestion_pipeline import IngestionPipelineService, ingestion_service
from app.services.supabase_storage import storage_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_state():
    users_snapshot = DEMO_USERS.copy()
    memberships_snapshot = DEMO_MEMBERSHIPS.copy()
    tokens_snapshot = _TOKENS.copy()
    storage_service.clear_all()
    clear_audit_logs()

    yield

    DEMO_USERS.clear()
    DEMO_USERS.update(users_snapshot)
    DEMO_MEMBERSHIPS.clear()
    DEMO_MEMBERSHIPS.update(memberships_snapshot)
    _TOKENS.clear()
    _TOKENS.update(tokens_snapshot)
    storage_service.clear_all()
    clear_audit_logs()


def _get_admin_headers():
    resp = client.post("/api/v1/auth/login", json={"email": "admin@acme.com", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _get_member_headers():
    resp = client.post("/api/v1/auth/login", json={"email": "member@acme.com", "password": "member123"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_authorization_and_status():
    admin_headers = _get_admin_headers()
    member_headers = _get_member_headers()

    # Member role cannot upload sources (requires ADMIN / Knowledge Owner)
    files = {"file": ("policy.md", b"# Acme Policy\n\nSecurity rules.", "text/markdown")}
    fail_resp = client.post("/api/v1/workspaces/ws_acme/sources", files=files, headers=member_headers)
    assert fail_resp.status_code == 403

    # Admin role uploads markdown source successfully
    upload_resp = client.post("/api/v1/workspaces/ws_acme/sources", files=files, headers=admin_headers)
    assert upload_resp.status_code == 201
    data = upload_resp.json()
    assert data["title"] == "Policy"
    assert data["file_type"] == "markdown"
    assert data["status"] in ("ready", "processing", "queued")
    assert data["current_version"] == 1


def test_ingestion_pipeline_and_chunk_lineage():
    admin_headers = _get_admin_headers()

    md_content = b"# Security Guide\n\nAll staff must use 2FA.\n\n# Data Protection\n\nEncrypt sensitive files."
    files = {"file": ("security_guide.md", md_content, "text/markdown")}
    resp = client.post("/api/v1/workspaces/ws_acme/sources", files=files, headers=admin_headers)
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    # Verify searchable chunks retain exact workspace, source, version, and location lineage
    chunks = storage_service.search_chunks("ws_acme", "2FA")
    assert len(chunks) >= 1
    top_chunk = chunks[0]
    assert top_chunk["workspace_id"] == "ws_acme"
    assert top_chunk["source_id"] == source_id
    assert top_chunk["source_version"] == 1
    assert "location" in top_chunk
    assert "2FA" in top_chunk["text"]


def test_search_retrieval_and_citation_synthesis():
    admin_headers = _get_admin_headers()
    member_headers = _get_member_headers()

    # Upload document
    files = {"file": ("expense_policy.txt", b"Travel expense policy: Daily food limit is $50 USD per person.", "text/plain")}
    client.post("/api/v1/workspaces/ws_acme/sources", files=files, headers=admin_headers)

    # Search for expense policy
    search_resp = client.post(
        "/api/v1/workspaces/ws_acme/search",
        json={"query": "food limit"},
        headers=member_headers,
    )
    assert search_resp.status_code == 200
    res_data = search_resp.json()
    assert "food limit is $50 USD" in res_data["answer"] or "expense" in res_data["answer"].lower()
    assert res_data["source"]["title"] == "Expense Policy"
    assert res_data["source"]["version"] == 1
    assert res_data["source"]["location"] is not None
    assert "$50 USD" in res_data["source"]["snippet"]


def test_failed_ingestion_and_actionable_retry():
    admin_headers = _get_admin_headers()

    # Upload invalid empty file which triggers ingestion failure
    files = {"file": ("empty.md", b"", "text/markdown")}
    resp = client.post("/api/v1/workspaces/ws_acme/sources", files=files, headers=admin_headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

    # Create source manually with bad payload to simulate background processing failure
    source_doc, _ = storage_service.create_or_update_source(
        workspace_id="ws_acme",
        title="Corrupted Doc",
        file_type=FileType.PDF,
        file_content=b"not a real pdf file header",
        filename="corrupted.pdf",
    )
    ingestion_service.process_source_ingestion("ws_acme", source_doc.id)

    # Check status is failed with actionable reason
    sources_resp = client.get("/api/v1/workspaces/ws_acme/sources", headers=admin_headers)
    assert sources_resp.status_code == 200
    corrupted = [s for s in sources_resp.json() if s["id"] == source_doc.id][0]
    assert corrupted["status"] == "failed"
    assert corrupted["status_reason"] is not None

    # Repair raw file and retry idempotently
    storage_service.save_file(source_doc.file_path, b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>startxref\n0\n%%EOF")
    retry_resp = client.post(f"/api/v1/workspaces/ws_acme/sources/{source_doc.id}/retry", headers=admin_headers)
    assert retry_resp.status_code == 200

    # Verify no duplicate source records created
    sources_after = client.get("/api/v1/workspaces/ws_acme/sources", headers=admin_headers).json()
    matching_sources = [s for s in sources_after if s["id"] == source_doc.id]
    assert len(matching_sources) == 1


def test_versioning_and_workspace_isolation():
    admin_acme = _get_admin_headers()
    
    # Login as Globex admin
    login_globex = client.post("/api/v1/auth/login", json={"email": "admin@globex.com", "password": "admin123"})
    globex_token = login_globex.json()["token"]
    admin_globex = {"Authorization": f"Bearer {globex_token}"}

    # Upload v1 to Acme
    files_v1 = {"file": ("handbook.txt", b"Acme handbook version 1 content.", "text/plain")}
    resp_v1 = client.post("/api/v1/workspaces/ws_acme/sources", files=files_v1, headers=admin_acme)
    assert resp_v1.status_code == 201
    assert resp_v1.json()["current_version"] == 1
    source_id = resp_v1.json()["id"]

    # Upload v2 to Acme (updating existing source)
    files_v2 = {"file": ("handbook.txt", b"Acme handbook version 2 updated content.", "text/plain")}
    resp_v2 = client.post("/api/v1/workspaces/ws_acme/sources", files=files_v1, headers=admin_acme)
    assert resp_v2.status_code == 201
    assert resp_v2.json()["current_version"] == 2

    # Verify versions endpoint
    versions_resp = client.get(f"/api/v1/workspaces/ws_acme/sources/{source_id}/versions", headers=admin_acme)
    assert versions_resp.status_code == 200
    assert len(versions_resp.json()) == 2

    # Workspace Isolation: Globex user search cannot retrieve Acme sources
    globex_search = client.post(
        "/api/v1/workspaces/ws_globex/search",
        json={"query": "handbook"},
        headers=admin_globex,
    )
    assert globex_search.status_code == 200
    assert "Acme" not in globex_search.json()["answer"]


def test_telemetry_metrics_endpoint():
    admin_headers = _get_admin_headers()
    
    # Check initial metrics
    resp = client.get("/api/v1/workspaces/ws_acme/sources/metrics", headers=admin_headers)
    assert resp.status_code == 200
    metrics = resp.json()
    assert "total_attempts" in metrics
    assert "by_type" in metrics
