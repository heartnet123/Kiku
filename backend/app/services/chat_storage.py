import uuid
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.core.config import settings
from app.domain.chat import ChatMessage, ChatSession


class ChatStorageService:
    """Dual-mode chat persistence.

    - Supabase Postgres when SUPABASE_URL + SUPABASE_KEY are set (production).
    - In-memory Python dicts when credentials are absent (unit tests / demo).

    Public interface is identical in both modes; callers never branch on storage type.
    """

    def __init__(self) -> None:
        key = settings.supabase_service_role_key or settings.supabase_key
        self.client: Client | None = (
            create_client(settings.supabase_url, key)
            if settings.supabase_url and key
            else None
        )
        # In-memory fallback — used when self.client is None
        self._sessions: dict[str, ChatSession] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _row_to_session(self, row: dict[str, Any]) -> ChatSession:
        created = row["created_at"]
        updated = row["updated_at"]
        return ChatSession(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
            updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else updated,
        )

    def _row_to_message(self, row: dict[str, Any]) -> ChatMessage:
        created = row["created_at"]
        return ChatMessage(
            id=row["id"],
            session_id=row["session_id"],
            workspace_id=row["workspace_id"],
            role=row["role"],
            content=row["content"],
            # citations_json is jsonb — supabase-py returns Python list directly
            citations_json=row.get("citations_json") or [],
            created_at=datetime.fromisoformat(created) if isinstance(created, str) else created,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(self, workspace_id: str, user_id: str, title: str = "New Chat") -> ChatSession:
        if self.client:
            try:
                # Let PostgreSQL gen_random_uuid() create the id — do not send id
                result = (
                    self.client.table("chat_sessions")
                    .insert({"workspace_id": workspace_id, "user_id": user_id, "title": title})
                    .execute()
                )
                return self._row_to_session(result.data[0])
            except Exception:
                pass

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session = ChatSession(
            id=session_id,
            workspace_id=workspace_id,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        self._sessions[session_id] = session
        self._messages[session_id] = []
        return session

    def list_sessions(self, workspace_id: str, user_id: str | None = None) -> list[ChatSession]:
        if self.client:
            try:
                q = (
                    self.client.table("chat_sessions")
                    .select("*")
                    .eq("workspace_id", workspace_id)
                )
                if user_id:
                    q = q.eq("user_id", user_id)
                result = q.order("updated_at", desc=True).execute()
                return [self._row_to_session(row) for row in result.data]
            except Exception:
                pass

        sessions = [s for s in self._sessions.values() if s.workspace_id == workspace_id]
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sessions

    def get_session(
        self, session_id: str, workspace_id: str | None = None, user_id: str | None = None
    ) -> ChatSession | None:
        if self.client:
            try:
                q = self.client.table("chat_sessions").select("*").eq("id", session_id)
                if workspace_id:
                    q = q.eq("workspace_id", workspace_id)
                if user_id:
                    q = q.eq("user_id", user_id)
                result = q.execute()
                return self._row_to_session(result.data[0]) if result.data else None
            except Exception:
                pass

        session = self._sessions.get(session_id)
        if session and workspace_id and session.workspace_id != workspace_id:
            return None
        if session and user_id and session.user_id != user_id:
            return None
        return session

    def delete_session(
        self, session_id: str, workspace_id: str | None = None, user_id: str | None = None
    ) -> bool:
        if self.client:
            try:
                # ON DELETE CASCADE removes chat_messages → citations automatically
                q = self.client.table("chat_sessions").delete().eq("id", session_id)
                if workspace_id:
                    q = q.eq("workspace_id", workspace_id)
                if user_id:
                    q = q.eq("user_id", user_id)
                result = q.execute()
                return len(result.data) > 0
            except Exception:
                pass

        if session_id in self._sessions:
            del self._sessions[session_id]
            self._messages.pop(session_id, None)
            return True
        return False

    def add_message(
        self,
        session_id: str,
        workspace_id: str,
        role: str,
        content: str,
        citations_json: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        if self.client:
            try:
                # citations_json is jsonb — pass Python list directly, never json.dumps()
                result = (
                    self.client.table("chat_messages")
                    .insert({
                        "session_id": session_id,
                        "workspace_id": workspace_id,
                        "role": role,
                        "content": content,
                        "citations_json": citations_json if citations_json is not None else [],
                    })
                    .execute()
                )
                msg = self._row_to_message(result.data[0])

                # Update session updated_at; auto-title on first user message
                update_payload: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
                if role == "user":
                    count_result = (
                        self.client.table("chat_messages")
                        .select("id", count="exact")
                        .eq("session_id", session_id)
                        .execute()
                    )
                    if (count_result.count or 0) == 1:
                        update_payload["title"] = content[:30] + ("..." if len(content) > 30 else "")

                self.client.table("chat_sessions").update(update_payload).eq("id", session_id).execute()
                return msg
            except Exception:
                pass

        # In-memory fallback
        msg_id = str(uuid.uuid4())
        msg = ChatMessage(
            id=msg_id,
            session_id=session_id,
            workspace_id=workspace_id,
            role=role,
            content=content,
            citations_json=citations_json,
        )
        if session_id not in self._messages:
            self._messages[session_id] = []
        self._messages[session_id].append(msg)
        if session_id in self._sessions:
            self._sessions[session_id].updated_at = datetime.now(timezone.utc)
            if len(self._messages[session_id]) == 1 and role == "user":
                self._sessions[session_id].title = content[:30] + ("..." if len(content) > 30 else "")
        return msg

    def get_messages(
        self,
        session_id: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ChatMessage]:
        if self.client:
            try:
                result = (
                    self.client.table("chat_messages")
                    .select("*")
                    .eq("session_id", session_id)
                    .order("created_at")
                    .execute()
                )
                return [self._row_to_message(row) for row in result.data]
            except Exception:
                pass

        return self._messages.get(session_id, [])


chat_storage_service = ChatStorageService()