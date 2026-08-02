from datetime import datetime, timezone
import io
import re
import uuid
from typing import Any, Callable, TypeVar

from supabase import Client

from app.core.config import settings
from app.domain.knowledge import (
    ChunkLineage,
    DocumentVersion,
    FileType,
    KnowledgeSourceDocument,
    SourceStatus,
)
from app.services.embedding_service import embedding_service
from app.services.supabase_client import create_supabase_client, response_data

T = TypeVar("T")


class SupabaseStorageError(RuntimeError):
    pass


class SupabaseStorageService:
    """Persist source files, immutable versions, chunks, and retrieval data in Supabase."""

    def __init__(
        self,
        *,
        client: Client | Any | None = None,
        user_id: str | None = None,
        in_memory: bool | None = None,
    ) -> None:
        if client is not None and in_memory is True:
            raise ValueError("Storage cannot use both a Supabase client and in-memory mode")

        if client is not None:
            self.client = client
            self._in_memory = False
        else:
            if in_memory is None:
                in_memory = not bool(settings.supabase_service_role_key)
            self._in_memory = in_memory
            self.client = None if in_memory else create_supabase_client(service_role=True)

        self.user_id = user_id
        self._sources: dict[str, KnowledgeSourceDocument] = {}
        self._versions: dict[str, list[DocumentVersion]] = {}
        self._files: dict[str, bytes] = {}
        self._chunks: list[dict[str, Any]] = []
        self._metrics: dict[str, dict[str, int]] = {
            "markdown": {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "retrying": 0},
            "text": {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "retrying": 0},
            "pdf": {"queued": 0, "processing": 0, "ready": 0, "failed": 0, "retrying": 0},
        }

    @staticmethod
    def _run(operation: str, callback: Callable[[], T]) -> T:
        try:
            return callback()
        except SupabaseStorageError:
            raise
        except Exception as exc:
            raise SupabaseStorageError(f"{operation} failed: {exc}") from exc

    @staticmethod
    def _status_value(status: SourceStatus) -> str:
        return "pending" if status == SourceStatus.QUEUED else status.value

    @staticmethod
    def _source_status(value: str) -> SourceStatus:
        if value == "pending":
            return SourceStatus.QUEUED
        try:
            return SourceStatus(value)
        except ValueError:
            return SourceStatus.FAILED

    @staticmethod
    def _parse_datetime(value: datetime | str | None) -> str:
        if value is None:
            return datetime.now(timezone.utc).isoformat()
        return value.isoformat() if isinstance(value, datetime) else str(value)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = filename.replace("\\", "/").split("/")[-1].strip()
        return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:180] or "uploaded_file.txt"

    @staticmethod
    def _mime_type(file_type: FileType) -> str:
        return {
            FileType.PDF: "application/pdf",
            FileType.MARKDOWN: "text/markdown",
            FileType.TEXT: "text/plain",
        }[file_type]

    @staticmethod
    def _page_number(location: str) -> int | None:
        match = re.search(r"Page\s+(\d+)", location, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _row_to_version(row: dict[str, Any]) -> DocumentVersion:
        return DocumentVersion(
            version_id=str(row["id"]),
            source_id=str(row["document_id"]),
            version_number=int(row["version_number"]),
            file_path=str(row["storage_path"]),
            file_size=int(row["file_size_bytes"]),
            created_at=SupabaseStorageService._parse_datetime(row.get("created_at")),
        )

    @classmethod
    def _row_to_source(
        cls,
        row: dict[str, Any],
        version_number: int = 1,
    ) -> KnowledgeSourceDocument:
        filename = str(row.get("original_filename") or row.get("storage_path") or "source.txt")
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        file_type = FileType.PDF if suffix == "pdf" else FileType.MARKDOWN if suffix in {"md", "markdown"} else FileType.TEXT
        return KnowledgeSourceDocument(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            title=str(row["title"]),
            file_type=file_type,
            file_path=str(row["storage_path"]),
            current_version=version_number,
            status=cls._source_status(str(row["status"])),
            status_reason=row.get("error_message"),
            created_at=cls._parse_datetime(row.get("created_at")),
            updated_at=cls._parse_datetime(row.get("updated_at")),
        )

    def _db_document(self, workspace_id: str, source_id: str) -> dict[str, Any] | None:
        rows = response_data(
            self.client.table("documents")
            .select("*")
            .eq("id", source_id)
            .eq("workspace_id", workspace_id)
            .execute()
        )
        return rows[0] if rows else None

    def _db_current_version_number(self, document: dict[str, Any]) -> int:
        rows = response_data(
            self.client.table("document_versions")
            .select("version_number")
            .eq("document_id", str(document["id"]))
            .order("version_number", desc=True)
            .limit(1)
            .execute()
        )
        return int(rows[0]["version_number"]) if rows else 1

    def save_file(self, file_path: str, content: bytes) -> str:
        if self._in_memory:
            self._files[file_path] = content
            return file_path
        self._run(
            "upload source file",
            lambda: self.client.storage.from_("documents").upload(
                file_path,
                content,
                {"content-type": "application/octet-stream", "upsert": "true"},
            ),
        )
        return file_path

    def get_file(self, file_path: str) -> bytes | None:
        if self._in_memory:
            return self._files.get(file_path)
        return self._run(
            "download source file",
            lambda: self.client.storage.from_("documents").download(file_path),
        )

    def create_or_update_source(
        self,
        workspace_id: str,
        title: str,
        file_type: FileType,
        file_content: bytes,
        filename: str,
        source_id: str | None = None,
    ) -> tuple[KnowledgeSourceDocument, DocumentVersion]:
        if self._in_memory:
            return self._create_memory_source(
                workspace_id, title, file_type, file_content, filename, source_id
            )

        safe_filename = self._safe_filename(filename)
        document = self._db_document(workspace_id, source_id) if source_id else None
        source_id = str(document["id"]) if document else str(uuid.uuid4())
        version_number = self._db_current_version_number(document) + 1 if document else 1
        file_path = f"{workspace_id}/{source_id}/v{version_number}/{safe_filename}"
        version_id = str(uuid.uuid4())

        self.save_file(file_path, file_content)
        if not document:
            self._run(
                "create source document",
                lambda: self.client.table("documents")
                .insert(
                    {
                        "id": source_id,
                        "workspace_id": workspace_id,
                        "owner_id": self.user_id,
                        "title": title,
                        "original_filename": safe_filename,
                        "storage_bucket": "documents",
                        "storage_path": file_path,
                        "mime_type": self._mime_type(file_type),
                        "file_size_bytes": len(file_content),
                        "status": "pending",
                        "chunk_count": 0,
                        "metadata": {},
                    }
                )
                .execute(),
            )
        else:
            self._run(
                "queue source version",
                lambda: self.client.table("documents")
                .update(
                    {
                        "title": title,
                        "original_filename": safe_filename,
                        "storage_path": file_path,
                        "mime_type": self._mime_type(file_type),
                        "file_size_bytes": len(file_content),
                        "status": "pending",
                        "error_message": None,
                    }
                )
                .eq("id", source_id)
                .eq("workspace_id", workspace_id)
                .execute(),
            )

        version_rows = response_data(
            self._run(
                "create source version",
                lambda: self.client.table("document_versions")
                .insert(
                    {
                        "id": version_id,
                        "workspace_id": workspace_id,
                        "document_id": source_id,
                        "version_number": version_number,
                        "storage_bucket": "documents",
                        "storage_path": file_path,
                        "original_filename": safe_filename,
                        "mime_type": self._mime_type(file_type),
                        "file_size_bytes": len(file_content),
                        "status": "pending",
                        "chunk_count": 0,
                        "metadata": {},
                        "created_by": self.user_id,
                    }
                )
                .execute()
            )
        )
        self._run(
            "activate source version",
            lambda: self.client.table("documents")
            .update(
                {
                    "current_version_id": version_id,
                    "status": "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", source_id)
            .eq("workspace_id", workspace_id)
            .execute(),
        )
        version_row = version_rows[0] if version_rows else {
            "id": version_id,
            "document_id": source_id,
            "version_number": version_number,
            "storage_path": file_path,
            "file_size_bytes": len(file_content),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        document_row = self._db_document(workspace_id, source_id) or {
            "id": source_id,
            "workspace_id": workspace_id,
            "title": title,
            "original_filename": safe_filename,
            "storage_path": file_path,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return self._row_to_source(document_row, version_number), self._row_to_version(version_row)

    def _create_memory_source(
        self,
        workspace_id: str,
        title: str,
        file_type: FileType,
        file_content: bytes,
        filename: str,
        source_id: str | None,
    ) -> tuple[KnowledgeSourceDocument, DocumentVersion]:
        now = datetime.now(timezone.utc).isoformat()
        source_id = source_id or f"{workspace_id}-{self._safe_filename(filename).lower()}"
        existing = self._sources.get(source_id)
        if existing and existing.workspace_id != workspace_id:
            raise ValueError(f"Source '{source_id}' belongs to another workspace")

        version_number = existing.current_version + 1 if existing else 1
        file_path = f"workspaces/{workspace_id}/{source_id}/v{version_number}/{filename}"
        source_doc = existing or KnowledgeSourceDocument(
            id=source_id,
            workspace_id=workspace_id,
            title=title,
            file_type=file_type,
            file_path=file_path,
            current_version=version_number,
            status=SourceStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        source_doc.title = title
        source_doc.file_type = file_type
        source_doc.file_path = file_path
        source_doc.current_version = version_number
        source_doc.status = SourceStatus.QUEUED
        source_doc.status_reason = None
        source_doc.updated_at = now
        self._sources[source_id] = source_doc
        self._files[file_path] = file_content
        version = DocumentVersion(
            version_id=f"{source_id}-v{version_number}",
            source_id=source_id,
            version_number=version_number,
            file_path=file_path,
            file_size=len(file_content),
            created_at=now,
        )
        self._versions.setdefault(source_id, []).append(version)
        file_type_key = file_type.value
        self._metrics[file_type_key]["queued"] += 1
        return source_doc, version

    def update_source_status(
        self,
        source_id: str,
        status: SourceStatus,
        reason: str | None = None,
        workspace_id: str | None = None,
    ) -> KnowledgeSourceDocument | None:
        if self._in_memory:
            doc = self._sources.get(source_id)
            if doc:
                doc.status = status
                doc.status_reason = reason
                doc.updated_at = datetime.now(timezone.utc).isoformat()
                file_type_key = doc.file_type.value
                if file_type_key in self._metrics and status.value in self._metrics[file_type_key]:
                    self._metrics[file_type_key][status.value] += 1
            return doc

        query = self.client.table("documents").update(
            {
                "status": self._status_value(status),
                "error_message": reason,
                "processed_at": datetime.now(timezone.utc).isoformat() if status == SourceStatus.READY else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", source_id)
        if workspace_id:
            query = query.eq("workspace_id", workspace_id)
        self._run("update source status", lambda: query.execute())
        document = self._db_document(workspace_id or "", source_id) if workspace_id else None
        if not document:
            return None
        version_id = document.get("current_version_id")
        if version_id:
            self._run(
                "update source version status",
                lambda: self.client.table("document_versions")
                .update(
                    {
                        "status": self._status_value(status),
                        "error_message": reason,
                        "processed_at": datetime.now(timezone.utc).isoformat() if status == SourceStatus.READY else None,
                    }
                )
                .eq("id", version_id)
                .execute(),
            )
        return self._row_to_source(document, self._db_current_version_number(document))

    def list_sources(self, workspace_id: str) -> list[KnowledgeSourceDocument]:
        if self._in_memory:
            return [doc for doc in self._sources.values() if doc.workspace_id == workspace_id]

        documents = response_data(
            self.client.table("documents").select("*").eq("workspace_id", workspace_id).order("updated_at", desc=True).execute()
        )
        ids = [str(document["id"]) for document in documents]
        versions = response_data(
            self.client.table("document_versions")
            .select("id,document_id,version_number")
            .in_("document_id", ids)
            .order("version_number", desc=True)
            .execute()
        ) if ids else []
        latest = {}
        for version in versions:
            latest.setdefault(str(version["document_id"]), int(version["version_number"]))
        return [self._row_to_source(document, latest.get(str(document["id"]), 1)) for document in documents]

    def get_source(self, workspace_id: str, source_id: str) -> KnowledgeSourceDocument | None:
        if self._in_memory:
            document = self._sources.get(source_id)
            return document if document and document.workspace_id == workspace_id else None
        document = self._db_document(workspace_id, source_id)
        return self._row_to_source(document, self._db_current_version_number(document)) if document else None

    def list_versions(self, workspace_id: str, source_id: str) -> list[DocumentVersion]:
        if self._in_memory:
            return list(self._versions.get(source_id, [])) if self.get_source(workspace_id, source_id) else []
        if not self._db_document(workspace_id, source_id):
            return []
        rows = response_data(
            self.client.table("document_versions")
            .select("*")
            .eq("document_id", source_id)
            .order("version_number")
            .execute()
        )
        return [self._row_to_version(row) for row in rows]

    def save_chunks(
        self,
        workspace_id: str,
        source_id: str,
        version_number: int,
        chunks: list[ChunkLineage],
    ) -> None:
        if self._in_memory:
            self._chunks = [
                chunk
                for chunk in self._chunks
                if not (chunk["workspace_id"] == workspace_id and chunk["source_id"] == source_id)
            ]
            self._chunks.extend(
                {
                    "workspace_id": chunk.workspace_id,
                    "source_id": chunk.source_id,
                    "source_version": chunk.source_version,
                    "location": chunk.location,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            )
            return

        document = self._db_document(workspace_id, source_id)
        if not document:
            raise SupabaseStorageError("source document not found")
        versions = response_data(
            self.client.table("document_versions")
            .select("id")
            .eq("document_id", source_id)
            .eq("version_number", version_number)
            .execute()
        )
        if not versions:
            raise SupabaseStorageError("source version not found")
        version_id = str(versions[0]["id"])
        self._run(
            "replace source chunks",
            lambda: self.client.table("document_chunks").delete().eq("document_version_id", version_id).execute(),
        )
        rows = []
        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata)
            embedding = metadata.pop("embedding", None)
            rows.append(
                {
                    "document_id": source_id,
                    "document_version_id": version_id,
                    "chunk_index": index,
                    "content": chunk.text,
                    "page_number": self._page_number(chunk.location),
                    "heading": chunk.location,
                    "metadata": metadata,
                    "embedding": embedding,
                }
            )
        if rows:
            self._run("save source chunks", lambda: self.client.table("document_chunks").insert(rows).execute())
        self._run(
            "update source chunk count",
            lambda: self.client.table("document_versions")
            .update({"chunk_count": len(rows)})
            .eq("id", version_id)
            .execute(),
        )
        self._run(
            "update document chunk count",
            lambda: self.client.table("documents")
            .update({"chunk_count": len(rows)})
            .eq("id", source_id)
            .eq("workspace_id", workspace_id)
            .execute(),
        )

    def _keyword_search(
        self,
        workspace_id: str,
        query: str,
        category: str | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        documents = response_data(
            self.client.table("documents")
            .select("id,title,current_version_id")
            .eq("workspace_id", workspace_id)
            .eq("status", "ready")
            .execute()
        )
        if not documents:
            return []
        document_ids = [str(document["id"]) for document in documents]
        by_id = {str(document["id"]): document for document in documents}
        rows = response_data(
            self.client.table("document_chunks")
            .select("document_id,document_version_id,content,page_number,heading,metadata")
            .in_("document_id", document_ids)
            .execute()
        )
        normalized = query.lower()
        words = [word for word in normalized.split() if word not in {"what", "is", "the", "a", "an", "do", "i", "how", "to", "my", "in", "of", "for", "on", "with", "your", "can", "our", "are"}] or normalized.split()
        target_category = category.strip().lower() if category and category.strip().lower() != "all" else None
        matches = []
        for row in rows:
            metadata = row.get("metadata") or {}
            if target_category and str(metadata.get("category", "")).lower() != target_category:
                continue
            text = str(row.get("content") or "")
            score = sum(2.0 for word in words if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE))
            if score:
                document = by_id[str(row["document_id"])]
                matches.append(
                    (
                        score,
                        {
                            "workspace_id": workspace_id,
                            "source_id": str(row["document_id"]),
                            "source_version": 1,
                            "location": str(row.get("heading") or f"Page {row.get('page_number') or 1}"),
                            "text": text,
                            "metadata": {**metadata, "source_title": document["title"]},
                        },
                    )
                )
        matches.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in matches[:top_k]]

    def search_chunks(
        self,
        workspace_id: str,
        query: str,
        category: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if self._in_memory:
            normalized = query.lower()
            query_embedding = embedding_service.get_embedding(query)
            words = [word for word in normalized.split() if word not in {"what", "is", "the", "a", "an", "do", "i", "how", "to", "my", "in", "of", "for", "on", "with", "your", "can", "our", "are"}] or normalized.split()
            target_category = category.strip().lower() if category and category.strip().lower() != "all" else None
            matches = []
            for chunk in self._chunks:
                if chunk["workspace_id"] != workspace_id:
                    continue
                metadata = chunk.get("metadata", {})
                if target_category and metadata.get("category", "").lower() != target_category:
                    continue
                score = 0.0
                embedding = metadata.get("embedding")
                if query_embedding and embedding:
                    score += embedding_service.cosine_similarity(query_embedding, embedding) * 10.0
                for word in words:
                    if re.search(rf"\b{re.escape(word)}\b", chunk["text"], re.IGNORECASE):
                        score += 2.0
                if score > 0:
                    matches.append((score, chunk))
            matches.sort(key=lambda item: item[0], reverse=True)
            return [item[1] for item in matches[:top_k]]

        query_embedding = embedding_service.get_embedding(query)
        if query_embedding:
            rows = response_data(
                self.client.rpc(
                    "match_workspace_document_chunks",
                    {
                        "query_workspace_id": workspace_id,
                        "query_embedding": query_embedding,
                        "match_threshold": 0.0,
                        "match_count": max(top_k * 5, 20),
                        "filter_document_ids": None,
                    },
                ).execute()
            )
            results = []
            for row in rows:
                metadata = row.get("metadata") or {}
                if category and category.strip().lower() not in {"", "all"} and str(metadata.get("category", "")).lower() != category.strip().lower():
                    continue
                results.append(
                    {
                        "workspace_id": workspace_id,
                        "source_id": str(row["document_id"]),
                        "source_version": 1,
                        "location": str(row.get("heading") or f"Page {row.get('page_number') or 1}"),
                        "text": str(row.get("content") or ""),
                        "metadata": {**metadata, "source_title": row.get("document_title")},
                    }
                )
            if results:
                return results[:top_k]
        return self._keyword_search(workspace_id, query, category, top_k)

    def get_metrics(self, workspace_id: str) -> dict[str, Any]:
        if self._in_memory:
            workspace_sources = self.list_sources(workspace_id)
            return {
                "total_attempts": len(workspace_sources),
                "ready_count": sum(source.status == SourceStatus.READY for source in workspace_sources),
                "failed_count": sum(source.status == SourceStatus.FAILED for source in workspace_sources),
                "retrying_count": sum(
                    source.status in {SourceStatus.QUEUED, SourceStatus.PROCESSING} and source.current_version > 1
                    for source in workspace_sources
                ),
                "by_type": self._metrics,
            }

        sources = self.list_sources(workspace_id)
        return {
            "total_attempts": len(sources),
            "ready_count": sum(source.status == SourceStatus.READY for source in sources),
            "failed_count": sum(source.status == SourceStatus.FAILED for source in sources),
            "retrying_count": sum(
                source.status in {SourceStatus.QUEUED, SourceStatus.PROCESSING} and source.current_version > 1
                for source in sources
            ),
            "by_type": {
                "markdown": {"queued": 0, "processing": 0, "ready": sum(source.file_type == FileType.MARKDOWN and source.status == SourceStatus.READY for source in sources), "failed": 0, "retrying": 0},
                "text": {"queued": 0, "processing": 0, "ready": sum(source.file_type == FileType.TEXT and source.status == SourceStatus.READY for source in sources), "failed": 0, "retrying": 0},
                "pdf": {"queued": 0, "processing": 0, "ready": sum(source.file_type == FileType.PDF and source.status == SourceStatus.READY for source in sources), "failed": 0, "retrying": 0},
            },
        }

    def clear_all(self) -> None:
        self._sources.clear()
        self._versions.clear()
        self._files.clear()
        self._chunks.clear()
        for values in self._metrics.values():
            for key in values:
                values[key] = 0


storage_service = SupabaseStorageService()
