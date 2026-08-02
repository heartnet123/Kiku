import uuid
from datetime import datetime, timezone
from app.domain.chat import ChatMessage, ChatSession

class ChatStorageService:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    def create_session(self, workspace_id: str, user_id: str, title: str = "New Chat") -> ChatSession:
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

    def list_sessions(self, workspace_id: str) -> list[ChatSession]:
        return [s for s in self._sessions.values() if s.workspace_id == workspace_id]

    def get_session(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
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
        citations_json: list[dict] | None = None,
    ) -> ChatMessage:
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

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        return self._messages.get(session_id, [])

chat_storage_service = ChatStorageService()
