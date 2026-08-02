from app.domain.knowledge import CitationDetail, KnowledgeResult, KnowledgeSource, SourceStatus
from app.services.supabase_storage import SupabaseStorageService, storage_service


class KnowledgeSearchService:
    """Workspace-scoped knowledge retrieval via LlamaIndex & Supabase vector store adapter."""

    def __init__(self, storage: SupabaseStorageService = storage_service) -> None:
        self.storage = storage

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
