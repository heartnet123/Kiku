from app.domain.knowledge import CitationDetail, KnowledgeResult, KnowledgeSource, SourceStatus
from app.services.supabase_storage import SupabaseStorageService, storage_service


class KnowledgeSearchService:
    """Workspace-scoped knowledge retrieval via LlamaIndex & Supabase vector store adapter."""

    def __init__(self, storage: SupabaseStorageService = storage_service) -> None:
        self.storage = storage

    def search(self, workspace_id: str, query: str, category: str | None = None) -> KnowledgeResult:
        normalized_query = query.strip() or "General inquiry"

        # Query vector store for chunks matching workspace_id
        matched_chunks = self.storage.search_chunks(workspace_id=workspace_id, query=normalized_query, top_k=5)
        ready_sources_docs = [
            doc for doc in self.storage.list_sources(workspace_id)
            if doc.status == SourceStatus.READY
        ]

        if matched_chunks:
            top_chunk = matched_chunks[0]
            source_id = top_chunk["source_id"]
            version = top_chunk["source_version"]
            location = top_chunk["location"]
            snippet = top_chunk["text"][:300]
            
            source_doc = self.storage.get_source(workspace_id, source_id)
            source_title = source_doc.title if source_doc else f"Source '{source_id}'"

            citation = CitationDetail(
                source_id=source_id,
                title=source_title,
                version=version,
                location=location,
                snippet=snippet,
            )

            answer = f"Based on {source_title} (v{version}, {location}): {top_chunk['text'][:150]}..."
            details = f"Retrieved relevant knowledge from {source_title} ({location}): {top_chunk['text']}"
            main_source_id = source_id
        else:
            # Fallback when no ingested chunks match
            citation = CitationDetail(
                source_id=f"{workspace_id}-default-source",
                title="Workspace Overview",
                version=1,
                location="Section 1",
                snippet="No custom knowledge source chunks indexed yet. Please add a Markdown, text, or PDF file under Sources.",
            )
            answer = f"No specific document matched your query '{normalized_query}' in workspace {workspace_id}."
            details = "Add workspace knowledge sources via the Sources route to index custom policies and documentation."
            main_source_id = f"{workspace_id}-default-source"

        sources_list: list[KnowledgeSource] = []
        for doc in ready_sources_docs:
            sources_list.append(
                KnowledgeSource(
                    id=doc.id,
                    title=doc.title,
                    page=1,
                    updated_at=doc.updated_at,
                    status=doc.status.value,
                    version=doc.current_version,
                )
            )

        if not sources_list:
            sources_list.append(
                KnowledgeSource(
                    id=f"{workspace_id}-default-guide",
                    title="Seeded Workspace Guide",
                    page=1,
                    updated_at="2026-01-01",
                    status="ready",
                    version=1,
                )
            )

        return KnowledgeResult(
            query=normalized_query,
            answer=answer,
            details=details,
            source_id=main_source_id,
            source_page=1,
            sources=tuple(sources_list),
            related_faqs=(
                "How do I upload new documents?",
                "What file formats are supported?",
                "How is content isolated across workspaces?",
            ),
            citation=citation,
        )
