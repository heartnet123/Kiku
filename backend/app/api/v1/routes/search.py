from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import (
    DEMO_MEMBERSHIPS,
    DEMO_USERS,
    AuthenticatedMemberContext,
    get_access_token,
    get_authenticated_member,
    get_current_user,
    require_member,
)
from app.domain.identity import User
from app.schemas.knowledge import SearchRequest, SearchResponse, SourceReferenceResponse, SourceResponse
from app.services.knowledge_search import KnowledgeSearchService
from app.services.supabase_storage import SupabaseStorageService
from app.services.supabase_client import create_supabase_client, response_data

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["knowledge"])


def get_knowledge_search_service() -> KnowledgeSearchService:
    return KnowledgeSearchService()


def _scoped_service(
    ctx: AuthenticatedMemberContext,
    service: KnowledgeSearchService,
) -> KnowledgeSearchService:
    if ctx.supabase is None:
        return service
    return KnowledgeSearchService(
        storage=SupabaseStorageService(client=ctx.supabase, user_id=ctx.user.id),
        chat_storage=service.chat_storage,
        api_base_url=service.api_base_url,
        api_key=service.api_key,
        model=service.model,
    )


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    workspace_id: str,
    request: SearchRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
    service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> SearchResponse:
    result = _scoped_service(ctx, service).search(
        workspace_id=workspace_id,
        query=request.query,
        category=request.category,
    )
    citation_ref = SourceReferenceResponse(
        id=result.source_id,
        page=result.source_page,
        title=result.citation.title if result.citation else None,
        version=result.citation.version if result.citation else None,
        location=result.citation.location if result.citation else None,
        snippet=result.citation.snippet if result.citation else None,
    )
    sources_response = [
        SourceResponse(
            id=source.id,
            workspace_id=workspace_id,
            title=source.title,
            file_type="markdown",
            current_version=getattr(source, "version", 1),
            status=getattr(source, "status", "ready"),
            status_reason=None,
            page=source.page,
            updated_at=source.updated_at,
        )
        for source in result.sources
    ]
    return SearchResponse(
        query=result.query,
        answer=result.answer,
        details=result.details,
        source=citation_ref,
        sources=sources_response,
        related_faqs=list(result.related_faqs),
    )


def get_user_workspace_id(user: User, token: str) -> str:
    if user.id in DEMO_USERS:
        workspace_ids = [workspace_id for (workspace_id, member_id) in DEMO_MEMBERSHIPS if member_id == user.id]
        if len(workspace_ids) > 1:
            raise HTTPException(status_code=409, detail="Multiple workspaces found. Use a workspace-scoped search endpoint.")
        if not workspace_ids:
            raise HTTPException(status_code=403, detail="No workspace membership found.")
        return workspace_ids[0]

    client = create_supabase_client(token)
    if not client:
        raise HTTPException(status_code=503, detail="Supabase connection is not configured.")
    rows = response_data(
        client.table("workspace_members").select("workspace_id").eq("user_id", user.id).execute()
    )
    workspace_ids = [str(row["workspace_id"]) for row in rows]
    if len(workspace_ids) > 1:
        raise HTTPException(status_code=409, detail="Multiple workspaces found. Use a workspace-scoped search endpoint.")
    if not workspace_ids:
        raise HTTPException(status_code=404, detail="No workspace membership found.")
    return workspace_ids[0]


def require_alias_member_context(
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> AuthenticatedMemberContext:
    workspace_id = get_user_workspace_id(user, token)
    return get_authenticated_member(workspace_id, user, token)


top_level_router = APIRouter(tags=["knowledge"])


@top_level_router.post("/search", response_model=SearchResponse)
async def search_knowledge_alias(
    request: SearchRequest,
    ctx: AuthenticatedMemberContext = Depends(require_alias_member_context),
    service: KnowledgeSearchService = Depends(get_knowledge_search_service),
) -> SearchResponse:
    return await search_knowledge(
        workspace_id=ctx.membership.workspace_id,
        request=request,
        ctx=ctx,
        service=service,
    )
