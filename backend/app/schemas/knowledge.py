from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=50)


class SourceResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    file_type: str
    current_version: int
    status: str
    status_reason: str | None = None
    page: int = 1
    updated_at: str


class SourceVersionResponse(BaseModel):
    version_id: str
    source_id: str
    version_number: int
    file_path: str
    file_size: int
    created_at: str


class SourceMetricsResponse(BaseModel):
    total_attempts: int
    ready_count: int
    failed_count: int
    retrying_count: int
    by_type: dict[str, dict[str, int]]


class SourceReferenceResponse(BaseModel):
    id: str
    page: int = 1
    title: str | None = None
    version: int | None = None
    location: str | None = None
    snippet: str | None = None


class SearchResponse(BaseModel):
    query: str
    answer: str
    details: str
    source: SourceReferenceResponse
    sources: list[SourceResponse]
    related_faqs: list[str]


class RetryResponse(BaseModel):
    status: str
    message: str

