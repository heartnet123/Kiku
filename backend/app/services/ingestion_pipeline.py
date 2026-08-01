import io
import logging
import re
from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from pypdf import PdfReader

from app.domain.knowledge import (
    ChunkLineage,
    FileType,
    KnowledgeSourceDocument,
    SourceStatus,
)
from app.services.supabase_storage import SupabaseStorageService, storage_service

logger = logging.getLogger(__name__)


class IngestionPipelineService:
    """LlamaIndex document ingestion pipeline for Markdown, text, and PDF files."""

    def __init__(self, storage: SupabaseStorageService = storage_service) -> None:
        self.storage = storage
        self.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    def load_document_nodes(
        self, file_content: bytes, filename: str, file_type: FileType
    ) -> list[Document]:
        """Use LlamaIndex / PyPDF readers to parse content into LlamaIndex Documents."""
        docs: list[Document] = []
        ext = file_type.value if isinstance(file_type, FileType) else str(file_type)

        if ext in ("pdf", FileType.PDF.value):
            try:
                reader = PdfReader(io.BytesIO(file_content))
                if len(reader.pages) == 0:
                    raise ValueError("PDF file contains no readable pages.")
                
                for page_idx, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        docs.append(
                            Document(
                                text=page_text,
                                metadata={
                                    "file_name": filename,
                                    "page_label": str(page_idx),
                                    "location": f"Page {page_idx}",
                                },
                            )
                        )
                if not docs:
                    raise ValueError("Could not extract non-empty text content from PDF pages.")
            except Exception as e:
                raise ValueError(f"PDF parsing error: {str(e)}") from e

        elif ext in ("markdown", FileType.MARKDOWN.value):
            content_str = file_content.decode("utf-8", errors="replace")
            if not content_str.strip():
                raise ValueError("Markdown file is empty.")
            
            # Separate sections by markdown headers if present for lineage location
            sections = content_str.split("\n#")
            if len(sections) > 1:
                for idx, section in enumerate(sections):
                    prefix = "#" if idx > 0 else ""
                    section_text = (prefix + section).strip()
                    if section_text:
                        first_line = section_text.split("\n")[0].replace("#", "").strip()
                        location_label = f"Header '{first_line[:40]}'" if first_line else f"Section {idx+1}"
                        docs.append(
                            Document(
                                text=section_text,
                                metadata={"file_name": filename, "location": location_label},
                            )
                        )
            else:
                docs.append(
                    Document(
                        text=content_str,
                        metadata={"file_name": filename, "location": "Document Root"},
                    )
                )

        elif ext in ("text", FileType.TEXT.value):
            content_str = file_content.decode("utf-8", errors="replace")
            if not content_str.strip():
                raise ValueError("Text file is empty.")
            
            lines = content_str.splitlines()
            docs.append(
                Document(
                    text=content_str,
                    metadata={"file_name": filename, "location": f"Lines 1-{len(lines)}"},
                )
            )
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        return docs

    def process_source_ingestion(self, workspace_id: str, source_id: str) -> KnowledgeSourceDocument:
        """Run the ingestion job synchronously or background task for the active version."""
        source_doc = self.storage.get_source(workspace_id, source_id)
        if not source_doc:
            raise ValueError(f"Source document '{source_id}' not found in workspace '{workspace_id}'")

        # Set status to PROCESSING
        self.storage.update_source_status(source_id, SourceStatus.PROCESSING)

        try:
            file_content = self.storage.get_file(source_doc.file_path)
            if not file_content:
                raise ValueError(f"Source raw file missing at path '{source_doc.file_path}'")

            # 1. Parse using LlamaIndex document readers
            filename = source_doc.file_path.split("/")[-1]
            documents = self.load_document_nodes(file_content, filename, source_doc.file_type)

            # 2. Chunking with SentenceSplitter
            nodes = self.node_parser.get_nodes_from_documents(documents)

            # 3. Create ChunkLineage objects retaining exact workspace, source, version, and location lineage
            def infer_category(title: str, path: str, text: str) -> str:
                combined = f"{title} {path} {text}"
                def match_words(words: tuple[str, ...]) -> bool:
                    pattern = rf"\b({'|'.join(re.escape(w) for w in words)})\b"
                    return bool(re.search(pattern, combined, re.IGNORECASE))

                if match_words(("security", "2fa", "auth", "authentication", "encrypt", "encryption", "permission", "permissions", "password", "passwords")):
                    return "Security"
                if match_words(("billing", "expense", "expenses", "payment", "payments", "plan", "plans", "pricing", "invoice", "invoices", "cost", "costs")):
                    return "Billing"
                if match_words(("account", "accounts", "user", "users", "profile", "profiles", "login", "membership", "memberships")):
                    return "Account"
                return "Workspace"

            category = infer_category(source_doc.title, source_doc.file_path, "")

            chunk_lineages: list[ChunkLineage] = []
            for idx, node in enumerate(nodes):
                loc = node.metadata.get("location") or f"Chunk {idx+1}"
                chunk_cat = infer_category(source_doc.title, source_doc.file_path, node.get_content())
                chunk_lineages.append(
                    ChunkLineage(
                        workspace_id=workspace_id,
                        source_id=source_id,
                        source_version=source_doc.current_version,
                        location=loc,
                        text=node.get_content(),
                        metadata={
                            "source_title": source_doc.title,
                            "file_type": source_doc.file_type.value if isinstance(source_doc.file_type, FileType) else str(source_doc.file_type),
                            "chunk_index": idx,
                            "category": chunk_cat,
                        },
                    )
                )

            # 4. Save searchable chunks to vector store
            self.storage.save_chunks(
                workspace_id=workspace_id,
                source_id=source_id,
                version_number=source_doc.current_version,
                chunks=chunk_lineages,
            )

            # 5. Transition status to READY
            updated_doc = self.storage.update_source_status(source_id, SourceStatus.READY, reason=None)
            logger.info(f"Ingestion successful for source '{source_id}' (v{source_doc.current_version})")
            return updated_doc or source_doc

        except Exception as err:
            error_reason = str(err) or "Ingestion processing failed unexpectedly."
            logger.error(f"Ingestion failed for source '{source_id}': {error_reason}")
            updated_doc = self.storage.update_source_status(
                source_id, SourceStatus.FAILED, reason=error_reason
            )
            return updated_doc or source_doc


# Global instance
ingestion_service = IngestionPipelineService()
