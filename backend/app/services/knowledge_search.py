import logging
import httpx

from app.core.config import settings
from app.domain.knowledge import CitationDetail, KnowledgeResult, KnowledgeSource, SourceStatus
from app.services.supabase_storage import SupabaseStorageService, storage_service

logger = logging.getLogger(__name__)


class KnowledgeSearchService:
    """Workspace-scoped knowledge retrieval via LlamaIndex & Supabase vector store adapter,
    synthesized via Opencode LLM (deepseek-v4-flash-free)."""

    def __init__(
        self,
        storage: SupabaseStorageService = storage_service,
        api_base_url: str = settings.opencode_api_base_url,
        api_key: str = settings.opencode_api_key,
        model: str = settings.opencode_llm_model,
    ) -> None:
        self.storage = storage
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _synthesize_with_opencode(self, query: str, context_chunks: list[dict]) -> str | None:
        """Call Opencode OpenAI-compatible endpoint to synthesize an answer grounded in context."""
        context_parts = []
        for idx, chunk in enumerate(context_chunks, start=1):
            source_title = chunk.get("metadata", {}).get("source_title", f"Source '{chunk.get('source_id')}'")
            location = chunk.get("location", f"Chunk {idx}")
            text = chunk.get("text", "")
            context_parts.append(f"[{idx}] Source: {source_title} ({location})\n{text}")

        context_str = "\n\n".join(context_parts)
        endpoint = f"{self.api_base_url}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise knowledge synthesis assistant. "
                        "Answer the user question based strictly on the provided context passages. "
                        "If the context does not contain enough information, state clearly that you could not "
                        "find sufficient evidence in the workspace documents. Keep your answer factual, direct, and helpful."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context_str}\n\nQuestion: {query}",
                },
            ],
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        answer_text = choices[0]["message"].get("content", "").strip()
                        if answer_text:
                            return answer_text
                else:
                    logger.warning(
                        f"Opencode API returned non-200 status code {response.status_code}: {response.text[:200]}"
                    )
        except Exception as e:
            logger.warning(f"Failed to call Opencode LLM synthesis endpoint: {str(e)}")

        return None

    def search(self, workspace_id: str, query: str, category: str | None = None) -> KnowledgeResult:
        normalized_query = query.strip() or "General inquiry"

        # Query vector store for chunks matching workspace_id and optional category filter
        matched_chunks = self.storage.search_chunks(
            workspace_id=workspace_id,
            query=normalized_query,
            category=category,
            top_k=5,
        )
        ready_sources_docs = [
            doc for doc in self.storage.list_sources(workspace_id)
            if doc.status == SourceStatus.READY
        ]

        sources_list: list[KnowledgeSource] = []
        for doc in ready_sources_docs:
            sources_list.append(
                KnowledgeSource(
                    id=doc.id,
                    title=doc.title,
                    page=1,
                    updated_at=doc.updated_at,
                    status=doc.status.value if isinstance(doc.status, SourceStatus) else str(doc.status),
                    version=doc.current_version,
                )
            )

        if matched_chunks:
            top_chunk = matched_chunks[0]
            source_id = top_chunk["source_id"]
            version = top_chunk["source_version"]
            location = top_chunk["location"]
            snippet = top_chunk["text"][:300]

            source_doc = self.storage.get_source(workspace_id, source_id)
            source_title = source_doc.title if source_doc else top_chunk.get("metadata", {}).get("source_title", f"Source '{source_id}'")

            citation = CitationDetail(
                source_id=source_id,
                title=source_title,
                version=version,
                location=location,
                snippet=snippet,
            )

            # Synthesize answer via Opencode LLM if available, fallback to grounded template
            synthesized_answer = self._synthesize_with_opencode(normalized_query, matched_chunks)
            if synthesized_answer:
                answer = synthesized_answer
                details = f"Synthesized answer via Opencode LLM ({self.model}) using knowledge from {source_title} ({location}) in workspace {workspace_id}."
            else:
                answer = f"Based on {source_title} ({location}): {top_chunk['text']}"
                details = f"Retrieved relevant knowledge from {source_title} ({location}) in workspace {workspace_id}."

            main_source_id = source_id
            main_source_page = 1
        else:
            # Insufficient evidence behavior: return explicit no-evidence status without hard-coded fallbacks
            citation = None
            main_source_id = ""
            main_source_page = 0
            cat_suffix = f" in category '{category}'" if (category and category.strip().lower() != "all") else ""
            answer = f"I couldn't find any relevant information in your workspace knowledge sources for '{normalized_query}'{cat_suffix}."
            details = f"No matching document chunks were found in workspace '{workspace_id}'{cat_suffix}. Try rephrasing your query or adding relevant documents under Sources."

        return KnowledgeResult(
            query=normalized_query,
            answer=answer,
            details=details,
            source_id=main_source_id,
            source_page=main_source_page,
            sources=tuple(sources_list),
            related_faqs=(
                "How do I upload new documents?",
                "How do category filters work?",
                "What file formats are supported?",
            ),
            citation=citation,
        )
