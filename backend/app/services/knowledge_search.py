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

    async def stream_search(
        self, workspace_id: str, query: str, session_id: str | None = None, category: str | None = None
    ):
        """Async generator streaming SSE events (metadata, delta, done, error)."""
        import json
        from app.services.chat_storage import chat_storage_service

        normalized_query = query.strip() or "General inquiry"
        matched_chunks = self.storage.search_chunks(
            workspace_id=workspace_id, query=normalized_query, category=category, top_k=5
        )

        citations_payload = []
        if matched_chunks:
            top_chunk = matched_chunks[0]
            source_doc = self.storage.get_source(workspace_id, top_chunk["source_id"])
            source_title = (
                source_doc.title
                if source_doc
                else top_chunk.get("metadata", {}).get("source_title", f"Source '{top_chunk['source_id']}'")
            )
            citations_payload.append({
                "source_id": top_chunk["source_id"],
                "title": source_title,
                "version": top_chunk["source_version"],
                "location": top_chunk["location"],
                "snippet": top_chunk["text"][:300],
            })

        # Yield event: metadata
        metadata_data = json.dumps({"citations": citations_payload, "query": normalized_query})
        yield f"event: metadata\ndata: {metadata_data}\n\n"

        # Record user message if session_id provided
        if session_id:
            chat_storage_service.add_message(session_id, workspace_id, "user", normalized_query)

        # Call Opencode LLM synthesis stream (or fallback)
        synthesized_text = ""
        try:
            endpoint = f"{self.api_base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            context_parts = [
                f"[{idx+1}] Source: {c.get('metadata', {}).get('source_title', c.get('source_id'))} ({c.get('location')})\n{c.get('text')}"
                for idx, c in enumerate(matched_chunks)
            ]
            context_str = "\n\n".join(context_parts) if context_parts else "No document chunks available."

            history_parts = []
            if session_id:
                past_msgs = chat_storage_service.get_messages(session_id)[-6:-1]
                for m in past_msgs:
                    history_parts.append(f"{m.role.capitalize()}: {m.content}")
            history_str = "\n".join(history_parts)

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise knowledge synthesis assistant. Answer strictly based on provided context.",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context_str}\n\nHistory:\n{history_str}\n\nQuestion: {query}",
                    },
                ],
                "temperature": 0.2,
                "stream": True,
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk_obj = json.loads(data_str)
                                    delta = chunk_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        synthesized_text += delta
                                        delta_data = json.dumps({"content": delta})
                                        yield f"event: delta\ndata: {delta_data}\n\n"
                                except Exception:
                                    pass
                    else:
                        fallback = (
                            f"Based on knowledge sources: {matched_chunks[0]['text'][:200]}"
                            if matched_chunks
                            else "No relevant information found."
                        )
                        synthesized_text = fallback
                        delta_data = json.dumps({"content": fallback})
                        yield f"event: delta\ndata: {delta_data}\n\n"
                        error_data = json.dumps({"message": f"LLM returned status {response.status_code}"})
                        yield f"event: error\ndata: {error_data}\n\n"
        except Exception as exc:
            fallback = (
                f"Based on knowledge sources: {matched_chunks[0]['text'][:200]}"
                if matched_chunks
                else "No relevant information found."
            )
            synthesized_text = fallback
            delta_data = json.dumps({"content": fallback})
            yield f"event: delta\ndata: {delta_data}\n\n"
            error_data = json.dumps({"message": str(exc) or "LLM synthesis failed"})
            yield f"event: error\ndata: {error_data}\n\n"

        # Record assistant message
        if session_id and synthesized_text:
            chat_storage_service.add_message(
                session_id, workspace_id, "assistant", synthesized_text, citations_json=citations_payload
            )

        done_data = json.dumps({"status": "completed"})
        yield f"event: done\ndata: {done_data}\n\n"

