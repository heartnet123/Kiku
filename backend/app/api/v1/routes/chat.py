from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import AuthenticatedMemberContext, require_member
from app.services.chat_storage import chat_storage_service
from app.services.knowledge_search import KnowledgeSearchService

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    title: str = "New Chat"


class StreamMessageRequest(BaseModel):
    query: str
    category: str | None = None


@router.post("/sessions")
async def create_session(
    workspace_id: str,
    req: CreateSessionRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    session = chat_storage_service.create_session(workspace_id, ctx.membership.user_id, req.title)
    return session


@router.get("/sessions")
async def list_sessions(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return chat_storage_service.list_sessions(workspace_id)


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return chat_storage_service.get_messages(session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    success = chat_storage_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


@router.post("/sessions/{session_id}/stream")
async def stream_message(
    workspace_id: str,
    session_id: str,
    req: StreamMessageRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    search_service = KnowledgeSearchService()
    generator = search_service.stream_search(
        workspace_id=workspace_id, query=req.query, session_id=session_id, category=req.category
    )
    return StreamingResponse(generator, media_type="text/event-stream")
