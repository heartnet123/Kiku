from unittest.mock import patch
import pytest

from app.domain.knowledge import FileType
from app.services.embedding_service import EmbeddingService, embedding_service
from app.services.ingestion_pipeline import IngestionPipelineService
from app.services.supabase_storage import SupabaseStorageService


def test_cosine_similarity_calculation():
    """Verify vector cosine similarity math calculations."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert pytest.approx(EmbeddingService.cosine_similarity(v1, v2), 0.001) == 1.0
    assert pytest.approx(EmbeddingService.cosine_similarity(v1, v3), 0.001) == 0.0


def test_vector_similarity_search_ranking():
    """Verify search_chunks uses vector cosine similarity to rank chunks when embeddings exist."""
    storage = SupabaseStorageService()
    storage.clear_all()

    # Manual chunks with embeddings
    chunk_a = {
        "workspace_id": "ws_acme",
        "source_id": "src_1",
        "source_version": 1,
        "location": "Page 1",
        "text": "Alpha document details",
        "metadata": {
            "source_title": "Alpha Doc",
            "embedding": [0.9, 0.1, 0.0],
        },
    }
    chunk_b = {
        "workspace_id": "ws_acme",
        "source_id": "src_2",
        "source_version": 1,
        "location": "Page 1",
        "text": "Beta document details",
        "metadata": {
            "source_title": "Beta Doc",
            "embedding": [0.1, 0.9, 0.0],
        },
    }
    storage._chunks.extend([chunk_a, chunk_b])

    # Mock query embedding close to chunk_b ([0.0, 1.0, 0.0])
    with patch("app.services.embedding_service.embedding_service.get_embedding", return_value=[0.0, 1.0, 0.0]):
        matched = storage.search_chunks(workspace_id="ws_acme", query="query text", top_k=2)

        assert len(matched) == 2
        # Beta Doc (chunk_b) must be ranked first due to higher vector similarity
        assert matched[0]["source_id"] == "src_2"
        assert matched[1]["source_id"] == "src_1"
