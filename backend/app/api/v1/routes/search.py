from fastapi import APIRouter, Depends

from app.schemas.knowledge import SearchRequest, SearchResponse, SourceReferenceResponse, SourceResponse
from app.services.knowledge_search import KnowledgeSearchService

router = APIRouter(tags=["knowledge"])


def get_knowledge_search_service() -> KnowledgeSearchService:
    return KnowledgeSearchService()


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> SearchResponse:
    result = service.search(request.query, request.category)
    return SearchResponse(
        query=result.query,
        answer=result.answer,
        details=result.details,
        source=SourceReferenceResponse(id=result.source_id, page=result.source_page),
        sources=[
            SourceResponse(id=source.id, title=source.title, page=source.page, updated_at=source.updated_at)
            for source in result.sources
        ],
        related_faqs=list(result.related_faqs),
    )
