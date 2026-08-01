from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FileType(str, Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"


@dataclass
class DocumentVersion:
    version_id: str
    source_id: str
    version_number: int
    file_path: str
    file_size: int
    created_at: str


@dataclass
class KnowledgeSourceDocument:
    id: str
    workspace_id: str
    title: str
    file_type: FileType
    file_path: str
    current_version: int
    status: SourceStatus
    status_reason: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ChunkLineage:
    workspace_id: str
    source_id: str
    source_version: int
    location: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    title: str
    page: int
    updated_at: str
    status: str = "ready"
    version: int = 1


@dataclass(frozen=True)
class CitationDetail:
    source_id: str
    title: str
    version: int
    location: str
    snippet: str


@dataclass(frozen=True)
class KnowledgeResult:
    query: str
    answer: str
    details: str
    source_id: str
    source_page: int
    sources: tuple[KnowledgeSource, ...]
    related_faqs: tuple[str, ...]
    citation: CitationDetail | None = None

