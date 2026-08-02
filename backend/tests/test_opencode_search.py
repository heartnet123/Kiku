from unittest.mock import MagicMock, patch
import pytest

from app.domain.knowledge import FileType
from app.services.ingestion_pipeline import IngestionPipelineService
from app.services.knowledge_search import KnowledgeSearchService
from app.services.supabase_storage import SupabaseStorageService


@pytest.fixture
def mock_storage():
    storage = SupabaseStorageService()
    storage.clear_all()
    pipeline = IngestionPipelineService(storage=storage)
    
    # Ingest a security doc in workspace ws_acme
    source, _ = storage.create_or_update_source(
        workspace_id="ws_acme",
        title="Security Guide",
        file_type=FileType.MARKDOWN,
        file_content=b"# Security Policy\n\nAll members must enforce 2FA and strong passwords.",
        filename="security.md",
    )
    pipeline.process_source_ingestion("ws_acme", source.id)

    return storage


def test_opencode_llm_synthesis_success(mock_storage):
    """Verify KnowledgeSearchService calls Opencode API and returns synthesized LLM answer."""
    service = KnowledgeSearchService(
        storage=mock_storage,
        api_base_url="https://opencode.ai/zen/v1",
        api_key="mock_key",
        model="deepseek-v4-flash-free",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "According to the Security Guide, team members are required to enforce 2FA multi-factor authentication.",
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        res = service.search("ws_acme", "What are the 2FA rules?")

        assert res is not None
        assert "2FA multi-factor authentication" in res.answer
        assert "deepseek-v4-flash-free" in res.details
        assert res.citation is not None
        assert res.citation.title == "Security Guide"

        # Verify API request details
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://opencode.ai/zen/v1/chat/completions"
        assert kwargs["json"]["model"] == "deepseek-v4-flash-free"
        assert kwargs["headers"]["Authorization"] == "Bearer mock_key"


def test_opencode_llm_synthesis_api_failure_fallback(mock_storage):
    """Verify KnowledgeSearchService gracefully falls back to template answer on API HTTP errors."""
    service = KnowledgeSearchService(
        storage=mock_storage,
        api_base_url="https://opencode.ai/zen/v1",
        api_key="mock_key",
        model="deepseek-v4-flash-free",
    )

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.Client.post", return_value=mock_response):
        res = service.search("ws_acme", "2FA rules")

        assert res is not None
        assert "Based on Security Guide" in res.answer or "2FA" in res.answer
        assert res.citation is not None
        assert res.citation.title == "Security Guide"


def test_opencode_no_evidence_does_not_call_llm(mock_storage):
    """Verify queries with no matching evidence return explicit no-evidence response without calling Opencode LLM."""
    service = KnowledgeSearchService(storage=mock_storage)

    with patch("httpx.Client.post") as mock_post:
        res = service.search("ws_acme", "quantum physics teleportation")

        assert res is not None
        assert "couldn't find any relevant information" in res.answer.lower()
        assert res.citation is None
        mock_post.assert_not_called()
