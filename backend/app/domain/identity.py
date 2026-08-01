from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


@dataclass(frozen=True)
class User:
    id: str
    email: str
    full_name: str
    password: str


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    slug: str


@dataclass(frozen=True)
class WorkspaceMember:
    workspace_id: str
    user_id: str
    role: Role
    joined_at: str


@dataclass(frozen=True)
class AuditLogEvent:
    id: str
    actor_id: str
    workspace_id: str
    action: str
    target_id: str | None
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)
