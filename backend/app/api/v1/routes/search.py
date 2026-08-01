from fastapi import APIRouter, Depends

from app.core.auth import DEMO_MEMBERSHIPS, AuthenticatedMemberContext, get_current_user, require_member
from app.domain.identity import User
from app.schemas.knowledge import SearchRequest, SearchResponse, SourceReferenceResponse, SourceResponse
from app.services.knowledge_search import KnowledgeSearchService

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["knowledge"])


def get_knowledge_search_service() -> KnowledgeSearchService:
    return KnowledgeSearchService()


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    workspace_id: str,
    request: SearchRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
    service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> SearchResponse:
    result = service.search(workspace_id=workspace_id, query=request.query, category=request.category)
    
    citation_ref = SourceReferenceResponse(
        id=result.source_id,
        page=result.source_page,
        title=result.citation.title if result.citation else None,
        version=result.citation.version if result.citation else None,
        location=result.citation.location if result.citation else None,
        snippet=result.citation.snippet if result.citation else None,
    )

    sources_response = []
    for s in result.sources:
        sources_response.append(
            SourceResponse(
                id=s.id,
                workspace_id=workspace_id,
                title=s.title,
                file_type="markdown",
                current_version=getattr(s, "version", 1),
                status=getattr(s, "status", "ready"),
                status_reason=None,
                page=s.page,
                updated_at=s.updated_at,
            )
        )

    return SearchResponse(
        query=result.query,
        answer=result.answer,
        details=result.details,
        source=citation_ref,
        sources=sources_response,
        related_faqs=list(result.related_faqs),
    )


def get_user_workspace_id(user: User = Depends(get_current_user)) -> str:
    for (ws_id, u_id) in DEMO_MEMBERSHIPS:
        if u_id == user.id:
            return ws_id
    return "ws_acme"


def require_alias_member_context(
    user: User = Depends(get_current_user),
) -> AuthenticatedMemberContext:
    workspace_id = get_user_workspace_id(user)
    return require_member(workspace_id=workspace_id, user=user)


top_level_router = APIRouter(tags=["knowledge"])


@top_level_router.post("/search", response_model=SearchResponse)
async def search_knowledge_alias(
    request: SearchRequest,
    ctx: AuthenticatedMemberContext = Depends(require_alias_member_context),
    service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> SearchResponse:
    workspace_id = ctx.membership.workspace_id
    return await search_knowledge(workspace_id=workspace_id, request=request, ctx=ctx, service=service)


