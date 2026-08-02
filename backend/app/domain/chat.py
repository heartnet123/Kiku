from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class ChatMessage:
    id: str
    session_id: str
    workspace_id: str
    role: str  # "user" | "assistant"
    content: str
    citations_json: list[dict[str, Any]] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ChatSession:
    id: str
    workspace_id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
