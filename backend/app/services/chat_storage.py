from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

from supabase import Client

from app.core.config import settings
from app.domain.chat import ChatMessage, ChatSession
from app.services.supabase_client import create_supabase_client, response_data

T = TypeVar("T")
logger = logging.getLogger(__name__)


class ChatStorageError(RuntimeError):
    """Raised when durable chat storage cannot complete an operation."""


class ChatStorageService:
    """Workspace/user-scoped chat persistence with an explicit in-memory test mode."""

    def __init__(
        self,
        *,
        client: Client | Any | None = None,
        in_memory: bool | None = None,
    ) -> None:
        if client is not None and in_memory is True:
            raise ValueError("Chat storage cannot use both a Supabase client and in-memory mode")
        if client is not None:
            self.client = client
            self._in_memory = False
        else:
            if in_memory is None:
                in_memory = not bool(settings.supabase_service_role_key)
            self._in_memory = in_memory
            self.client = None if in_memory else create_supabase_client(service_role=True)
            if not self._in_memory and self.client is None:
                raise RuntimeError("Supabase service-role storage is not configured")

        self._sessions: dict[str, ChatSession] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    @staticmethod
    def _parse_datetime(value: datetime | str) -> datetime:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def _run_backend(operation: str, callback: Callable[[], T]) -> T:
        try:
            return callback()
        except ChatStorageError:
            raise
        except Exception as exc:
            raise ChatStorageError(f"{operation} failed: {exc}") from exc

    def _row_to_session(self, row: dict[str, Any]) -> ChatSession:
        return ChatSession(
            id=str(row["id"]),
            workspace_id=str(row["workspace_id"]),
            user_id=str(row["user_id"]),
            title=str(row["title"]),
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
        )

    def _row_to_message(self, row: dict[str, Any], user_id: str) -> ChatMessage:
        return ChatMessage(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            workspace_id=str(row["workspace_id"]),
            user_id=user_id,
            role=str(row["role"]),
            content=str(row["content"]),
            citations_json=row.get("citations_json") or [],
            created_at=self._parse_datetime(row["created_at"]),
        )

    def _memory_session(self, session_id: str, workspace_id: str, user_id: str) -> ChatSession | None:
        session = self._sessions.get(session_id)
        if session and session.workspace_id == workspace_id and session.user_id == user_id:
            return session
        return None

    def _require_session_scope(self, session_id: str, workspace_id: str, user_id: str) -> ChatSession:
        session = self.get_session(session_id, workspace_id, user_id)
        if not session:
            raise ValueError("Chat session scope does not match workspace/user scope")
        return session

    def create_session(self, workspace_id: str, user_id: str, title: str = "New Chat") -> ChatSession:
        clean_title = title.strip() or "New Chat"
        if self._in_memory:
            now = datetime.now(timezone.utc)
            session = ChatSession(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                user_id=user_id,
                title=clean_title,
                created_at=now,
                updated_at=now,
            )
            self._sessions[session.id] = session
            self._messages[session.id] = []
            return session

        result = self._run_backend(
            "create chat session",
            lambda: self.client.table("chat_sessions")
            .insert({"workspace_id": workspace_id, "user_id": user_id, "title": clean_title, "metadata": {}})
            .execute(),
        )
        rows = response_data(result)
        if not rows:
            raise ChatStorageError("create chat session returned no row")
        return self._row_to_session(rows[0])

    def list_sessions(self, workspace_id: str, user_id: str) -> list[ChatSession]:
        if self._in_memory:
            return sorted(
                [
                    session
                    for session in self._sessions.values()
                    if session.workspace_id == workspace_id and session.user_id == user_id
                ],
                key=lambda session: session.updated_at,
                reverse=True,
            )
        rows = response_data(
            self._run_backend(
                "list chat sessions",
                lambda: self.client.table("chat_sessions")
                .select("*")
                .eq("workspace_id", workspace_id)
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .execute(),
            )
        )
        return [self._row_to_session(row) for row in rows]

    def get_session(self, session_id: str, workspace_id: str, user_id: str) -> ChatSession | None:
        if self._in_memory:
            return self._memory_session(session_id, workspace_id, user_id)
        rows = response_data(
            self._run_backend(
                "get chat session",
                lambda: self.client.table("chat_sessions")
                .select("*")
                .eq("id", session_id)
                .eq("workspace_id", workspace_id)
                .eq("user_id", user_id)
                .execute(),
            )
        )
        return self._row_to_session(rows[0]) if rows else None

    def delete_session(self, session_id: str, workspace_id: str, user_id: str) -> bool:
        if not self.get_session(session_id, workspace_id, user_id):
            return False
        if self._in_memory:
            del self._sessions[session_id]
            self._messages.pop(session_id, None)
            return True
        self._run_backend(
            "delete chat session",
            lambda: self.client.table("chat_sessions")
            .delete()
            .eq("id", session_id)
            .eq("workspace_id", workspace_id)
            .eq("user_id", user_id)
            .execute(),
        )
        return True

    def add_message(
        self,
        session_id: str,
        workspace_id: str,
        user_id: str,
        role: str,
        content: str,
        citations_json: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        if role not in {"user", "assistant"}:
            raise ValueError("Chat message role must be user or assistant")
        self._require_session_scope(session_id, workspace_id, user_id)
        citations = citations_json or []

        if self._in_memory:
            message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                content=content,
                citations_json=citations,
            )
            self._messages.setdefault(session_id, []).append(message)
            session = self._sessions[session_id]
            session.updated_at = datetime.now(timezone.utc)
            if role == "user" and len(self._messages[session_id]) == 1:
                session.title = content[:30] + ("..." if len(content) > 30 else "")
            return message

        rows = response_data(
            self._run_backend(
                "add chat message",
                lambda: self.client.table("chat_messages")
                .insert(
                    {
                        "session_id": session_id,
                        "workspace_id": workspace_id,
                        "role": role,
                        "content": content,
                        "citations_json": citations,
                    }
                )
                .execute(),
            )
        )
        if not rows:
            raise ChatStorageError("add chat message returned no row")
        message = self._row_to_message(rows[0], user_id)

        update_payload: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if role == "user":
            count_result = self._run_backend(
                "count chat messages",
                lambda: self.client.table("chat_messages")
                .select("id", count="exact")
                .eq("session_id", session_id)
                .eq("workspace_id", workspace_id)
                .execute(),
            )
            if (count_result.count or 0) == 1:
                update_payload["title"] = content[:30] + ("..." if len(content) > 30 else "")
        self._run_backend(
            "update chat session",
            lambda: self.client.table("chat_sessions")
            .update(update_payload)
            .eq("id", session_id)
            .eq("workspace_id", workspace_id)
            .eq("user_id", user_id)
            .execute(),
        )
        return message

    def get_messages(self, session_id: str, workspace_id: str, user_id: str) -> list[ChatMessage]:
        if not self.get_session(session_id, workspace_id, user_id):
            return []
        if self._in_memory:
            return sorted(self._messages.get(session_id, []), key=lambda message: message.created_at)
        rows = response_data(
            self._run_backend(
                "get chat messages",
                lambda: self.client.table("chat_messages")
                .select("*")
                .eq("session_id", session_id)
                .eq("workspace_id", workspace_id)
                .order("created_at")
                .execute(),
            )
        )
        return [self._row_to_message(row, user_id) for row in rows]


chat_storage_service = ChatStorageService()
