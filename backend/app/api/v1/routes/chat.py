from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import AuthenticatedMemberContext, require_member
from app.services.chat_storage import ChatStorageService, chat_storage_service
from app.services.knowledge_search import KnowledgeSearchService

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=80)


class StreamMessageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    category: str | None = Field(default=None, max_length=80)


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    workspace_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime


def _session_or_404(
    storage: ChatStorageService,
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext,
):
    session = storage.get_session(session_id, workspace_id, ctx.user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def _message_response(message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        workspace_id=message.workspace_id,
        role=message.role,
        content=message.content,
        citations=message.citations_json,
        created_at=message.created_at,
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    workspace_id: str,
    req: CreateSessionRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return chat_storage_service.create_session(workspace_id, ctx.user.id, req.title.strip())


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return chat_storage_service.list_sessions(workspace_id, ctx.user.id)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    return _session_or_404(chat_storage_service, workspace_id, session_id, ctx)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    _session_or_404(chat_storage_service, workspace_id, session_id, ctx)
    messages = chat_storage_service.get_messages(session_id, workspace_id, ctx.user.id)
    return [_message_response(message) for message in messages]


@router.delete("/sessions/{session_id}")
async def delete_session(
    workspace_id: str,
    session_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    _session_or_404(chat_storage_service, workspace_id, session_id, ctx)
    chat_storage_service.delete_session(session_id, workspace_id, ctx.user.id)
    return {"status": "deleted"}


@router.post("/sessions/{session_id}/stream")
async def stream_message(
    workspace_id: str,
    session_id: str,
    req: StreamMessageRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
):
    _session_or_404(chat_storage_service, workspace_id, session_id, ctx)
    service = KnowledgeSearchService(chat_storage=chat_storage_service)
    generator = service.stream_search(
        workspace_id=workspace_id,
        query=req.query,
        session_id=session_id,
        user_id=ctx.user.id,
        category=req.category,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
