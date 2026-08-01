from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    title: str
    page: int
    updated_at: str


@dataclass(frozen=True)
class KnowledgeResult:
    query: str
    answer: str
    details: str
    source_id: str
    source_page: int
    sources: tuple[KnowledgeSource, ...]
    related_faqs: tuple[str, ...]
