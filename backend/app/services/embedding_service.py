import logging
import math
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """OpenAI-compatible text embedding service for text-embedding-3-small."""

    def __init__(
        self,
        api_base_url: str = settings.openai_api_base_url,
        api_key: str = settings.openai_api_key,
        model: str = settings.openai_embedding_model,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/") if api_base_url else "https://api.openai.com/v1"
        self.api_key = api_key
        self.model = model or "text-embedding-3-small"

    def get_embedding(self, text: str) -> list[float] | None:
        """Fetch vector embedding for text using OpenAI Embeddings API."""
        if not self.api_key:
            return None

        endpoint = f"{self.api_base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "input": text.replace("\n", " "),
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    embeddings_data = data.get("data", [])
                    if embeddings_data and "embedding" in embeddings_data[0]:
                        return embeddings_data[0]["embedding"]
                else:
                    logger.warning(f"Embedding API non-200 status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {str(e)}")

        return None

    @staticmethod
    def cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(a * a for a in v1))
        norm_v2 = math.sqrt(sum(b * b for b in v2))
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot / (norm_v1 * norm_v2)


embedding_service = EmbeddingService()
