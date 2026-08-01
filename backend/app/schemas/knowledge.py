from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=50)


class SourceResponse(BaseModel):
    id: str
    title: str
    page: int
    updated_at: str


class SourceReferenceResponse(BaseModel):
    id: str
    page: int


class SearchResponse(BaseModel):
    query: str
    answer: str
    details: str
    source: SourceReferenceResponse
    sources: list[SourceResponse]
    related_faqs: list[str]
