from dataclasses import dataclass, field
from enum import Enum
import hashlib
import secrets
from typing import Any


class Role(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA-256 and a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain password against PBKDF2 hash."""
    try:
        salt, stored_key = hashed_password.split("$", 1)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(key.hex(), stored_key)
    except Exception:
        return False


@dataclass(frozen=True)
class User:
    id: str
    email: str
    full_name: str
    password_hash: str


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
