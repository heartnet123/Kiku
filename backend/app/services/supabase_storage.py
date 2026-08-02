from datetime import datetime, timezone
import os
import re
from typing import Any

from app.domain.knowledge import (
    ChunkLineage,
    DocumentVersion,
    FileType,
    KnowledgeSourceDocument,
    SourceStatus,
)
from app.services.embedding_service import embedding_service



class SupabaseStorageService:
    """Persistence boundary for original files, metadata, versions, chunks, and telemetry metrics."""

    def __init__(self) -> None:
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        
        # In-memory storage for test/demo mode or when Supabase credentials are absent
        self._sources: dict[str, KnowledgeSourceDocument] = {}
        self._versions: dict[str, list[DocumentVersion]] = {}
        self._files: dict[str, bytes] = {}
        self._chunks: list[dict[str, Any]] = []
        self._metrics: dict[str, dict[str, int]] = {
            "markdown": {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "retrying": 0},
            "text": {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "retrying": 0},
            "pdf": {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "retrying": 0},
        }

    def save_file(self, file_path: str, content: bytes) -> str:
        """Store original file content."""
        self._files[file_path] = content
        return file_path

    def get_file(self, file_path: str) -> bytes | None:
        """Retrieve original file content."""
        return self._files.get(file_path)

    def create_or_update_source(
        self,
        workspace_id: str,
        title: str,
        file_type: FileType,
        file_content: bytes,
        filename: str,
        source_id: str | None = None,
    ) -> tuple[KnowledgeSourceDocument, DocumentVersion]:
        """Create a new source or add a new traceable version to an existing source."""
        now = datetime.now(timezone.utc).isoformat()
        
        if not source_id:
            # Generate deterministic or unique ID based on workspace and title/filename
            clean_filename = filename.replace(" ", "_").lower()
            source_id = f"{workspace_id}-{clean_filename}"

        existing = self._sources.get(source_id)
        if existing:
            # Ensure workspace isolation
            if existing.workspace_id != workspace_id:
                raise ValueError(f"Source '{source_id}' belongs to another workspace")
            
            version_number = existing.current_version + 1
            existing.current_version = version_number
            existing.title = title
            existing.file_type = file_type
            existing.status = SourceStatus.QUEUED
            existing.status_reason = None
            existing.updated_at = now
            source_doc = existing
        else:
            version_number = 1
            source_doc = KnowledgeSourceDocument(
                id=source_id,
                workspace_id=workspace_id,
                title=title,
                file_type=file_type,
                file_path=f"workspaces/{workspace_id}/{source_id}/v{version_number}/{filename}",
                current_version=version_number,
                status=SourceStatus.QUEUED,
                status_reason=None,
                created_at=now,
                updated_at=now,
            )
            self._sources[source_id] = source_doc

        file_path = f"workspaces/{workspace_id}/{source_id}/v{version_number}/{filename}"
        source_doc.file_path = file_path
        self.save_file(file_path, file_content)

        version = DocumentVersion(
            version_id=f"{source_id}-v{version_number}",
            source_id=source_id,
            version_number=version_number,
            file_path=file_path,
            file_size=len(file_content),
            created_at=now,
        )

        if source_id not in self._versions:
            self._versions[source_id] = []
        self._versions[source_id].append(version)

        # Track metric for queued attempt
        file_type_key = file_type.value if isinstance(file_type, FileType) else str(file_type)
        if file_type_key in self._metrics:
            self._metrics[file_type_key]["queued"] += 1

        return source_doc, version

    def update_source_status(
        self, source_id: str, status: SourceStatus, reason: str | None = None
    ) -> KnowledgeSourceDocument | None:
        doc = self._sources.get(source_id)
        if doc:
            old_status = doc.status
            doc.status = status
            doc.status_reason = reason
            doc.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Update metrics
            file_type_key = doc.file_type.value if isinstance(doc.file_type, FileType) else str(doc.file_type)
            if file_type_key in self._metrics and status.value in self._metrics[file_type_key]:
                self._metrics[file_type_key][status.value] += 1
        return doc

    def list_sources(self, workspace_id: str) -> list[KnowledgeSourceDocument]:
        return [doc for doc in self._sources.values() if doc.workspace_id == workspace_id]

    def get_source(self, workspace_id: str, source_id: str) -> KnowledgeSourceDocument | None:
        doc = self._sources.get(source_id)
        if doc and doc.workspace_id == workspace_id:
            return doc
        return None

    def list_versions(self, workspace_id: str, source_id: str) -> list[DocumentVersion]:
        doc = self.get_source(workspace_id, source_id)
        if not doc:
            return []
        return self._versions.get(source_id, [])

    def save_chunks(self, workspace_id: str, source_id: str, version_number: int, chunks: list[ChunkLineage]) -> None:
        """Store chunks and purge older chunks for this source to ensure idempotency."""
        # Purge existing chunks for source_id to prevent duplicates
        self._chunks = [c for c in self._chunks if not (c["workspace_id"] == workspace_id and c["source_id"] == source_id)]

        for chunk in chunks:
            self._chunks.append({
                "workspace_id": chunk.workspace_id,
                "source_id": chunk.source_id,
                "source_version": chunk.source_version,
                "location": chunk.location,
                "text": chunk.text,
                "metadata": chunk.metadata,
            })

    def search_chunks(
        self, workspace_id: str, query: str, category: str | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Retrieve matching chunks strictly scoped to workspace_id using Vector Cosine Similarity and Keyword scoring."""
        normalized = query.lower()
        matched = []

        # Generate query embedding if OpenAI embedding API is configured
        query_embedding = embedding_service.get_embedding(query)

        stop_words = {"what", "is", "the", "a", "an", "do", "i", "how", "to", "my", "in", "of", "for", "on", "with", "your", "can", "our", "are"}
        query_words = [w for w in normalized.split() if w not in stop_words] or normalized.split()

        target_cat = category.strip().lower() if category and category.strip().lower() != "all" else None
        query_regexes = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in query_words]

        for chunk in self._chunks:
            if chunk["workspace_id"] != workspace_id:
                continue

            metadata = chunk.get("metadata", {})
            chunk_cat = metadata.get("category", "").lower()
            source_title = metadata.get("source_title", "")
            chunk_embedding = metadata.get("embedding")

            # Require exact match between chunk_cat and target_cat
            if target_cat and chunk_cat != target_cat:
                continue

            score = 0.0

            # 1. Vector Cosine Similarity Score (Weight: 10.0)
            if query_embedding and chunk_embedding:
                vector_sim = embedding_service.cosine_similarity(query_embedding, chunk_embedding)
                score += vector_sim * 10.0

            # 2. Keyword & Title Matching Score (Weight: 1.0 - 3.0)
            text_content = chunk["text"]
            location_content = chunk["location"]

            for rx in query_regexes:
                if rx.search(text_content):
                    score += 2.0
                if rx.search(source_title):
                    score += 3.0
                if rx.search(location_content):
                    score += 1.0

            if score > 0.0:
                matched.append((score, chunk))

        # Sort by score descending
        matched.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched[:top_k]]


    def get_metrics(self, workspace_id: str) -> dict[str, Any]:
        """Aggregate ingestion telemetry metrics."""
        workspace_sources = self.list_sources(workspace_id)
        
        total_attempts = len(workspace_sources)
        ready_count = sum(1 for s in workspace_sources if s.status == SourceStatus.READY)
        failed_count = sum(1 for s in workspace_sources if s.status == SourceStatus.FAILED)
        retrying_count = sum(1 for s in workspace_sources if s.status in (SourceStatus.QUEUED, SourceStatus.PROCESSING) and s.current_version > 1)

        return {
            "total_attempts": total_attempts,
            "ready_count": ready_count,
            "failed_count": failed_count,
            "retrying_count": retrying_count,
            "by_type": self._metrics,
        }

    def clear_all(self) -> None:
        self._sources.clear()
        self._versions.clear()
        self._files.clear()
        self._chunks.clear()
        for k in self._metrics:
            for status_key in self._metrics[k]:
                self._metrics[k][status_key] = 0


# Global singleton instance for application lifetime / test fixtures
storage_service = SupabaseStorageService()
