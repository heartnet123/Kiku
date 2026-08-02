import asyncio
from datetime import datetime, timezone

import pytest

from app.services.chat_storage import ChatStorageError, ChatStorageService


class FailingClient:
    def table(self, _name: str):
        raise RuntimeError("supabase unavailable")


def test_storage_is_scope_safe_and_orders_messages():
    storage = ChatStorageService(in_memory=True)
    session = storage.create_session("ws_acme", "user_1", "Thread")
    other_session = storage.create_session("ws_acme", "user_2", "Other")

    first = storage.add_message(
        session_id=session.id,
        workspace_id="ws_acme",
        user_id="user_1",
        role="user",
        content="First",
    )
    second = storage.add_message(
        session_id=session.id,
        workspace_id="ws_acme",
        user_id="user_1",
        role="assistant",
        content="Second",
    )
    first.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

    assert [message.content for message in storage.get_messages(session.id, "ws_acme", "user_1")] == [
        "Second",
        "First",
    ]
    assert storage.list_sessions("ws_acme", "user_1")[0].id == session.id
    assert storage.get_session(session.id, "ws_other", "user_1") is None
    assert storage.get_session(session.id, "ws_acme", "user_2") is None
    assert storage.get_messages(session.id, "ws_other", "user_1") == []
    assert storage.delete_session(other_session.id, "ws_acme", "user_1") is False

    with pytest.raises(ValueError, match="scope"):
        storage.add_message(
            session_id=session.id,
            workspace_id="ws_acme",
            user_id="user_2",
            role="assistant",
            content="Must not leak",
        )


def test_storage_does_not_fallback_to_memory_when_supabase_fails():
    storage = ChatStorageService(client=FailingClient(), in_memory=False)

    with pytest.raises(ChatStorageError, match="supabase unavailable"):
        storage.create_session("ws_acme", "user_1")

    assert storage._sessions == {}
    assert storage._messages == {}


@pytest.mark.anyio
async def test_stream_search_uses_scoped_history_and_emits_safe_events():
    from unittest.mock import patch

    from app.services.knowledge_search import KnowledgeSearchService
    from app.services.supabase_storage import SupabaseStorageService

    class ErrorResponse:
        status_code = 503

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    class ErrorClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def stream(self, *_args, **_kwargs):
            return ErrorResponse()

    storage = ChatStorageService(in_memory=True)
    session = storage.create_session("ws_acme", "user_1", "Thread")
    service = KnowledgeSearchService(
        storage=SupabaseStorageService(),
        chat_storage=storage,
        api_base_url="https://example.test/v1",
    )

    with patch("httpx.AsyncClient", return_value=ErrorClient()):
        chunks = [
            chunk
            async for chunk in service.stream_search(
                workspace_id="ws_acme",
                query="What is Kiku?",
                session_id=session.id,
                user_id="user_1",
            )
        ]

    events = []
    for chunk in chunks:
        lines = chunk.splitlines()
        name = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        events.append(name)

    assert events == [
        "status",
        "metadata",
        "status",
        "status",
        "error",
        "delta",
        "status",
        "done",
    ]
    assert "chain" not in "".join(chunks).lower()
    assert len(storage.get_messages(session.id, "ws_acme", "user_1")) == 2
    assert storage.get_messages(session.id, "ws_acme", "user_2") == []
