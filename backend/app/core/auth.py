from dataclasses import dataclass
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.audit import record_audit_event
from app.domain.identity import Role, User, Workspace, WorkspaceMember, hash_password, verify_password

# Pre-seeded Demo Data
DEMO_USERS = {
    "user_acme_admin": User(
        id="user_acme_admin",
        email="admin@acme.com",
        full_name="Acme Admin User",
        password_hash=hash_password("admin123"),
    ),
    "user_acme_member": User(
        id="user_acme_member",
        email="member@acme.com",
        full_name="Acme Team Member",
        password_hash=hash_password("member123"),
    ),
    "user_globex_admin": User(
        id="user_globex_admin",
        email="admin@globex.com",
        full_name="Globex Admin User",
        password_hash=hash_password("admin123"),
    ),
}

DEMO_WORKSPACES = {
    "ws_acme": Workspace(id="ws_acme", name="Acme Team Workspace", slug="acme"),
    "ws_globex": Workspace(id="ws_globex", name="Globex Corp Workspace", slug="globex"),
}

# Mapping: (workspace_id, user_id) -> WorkspaceMember
DEMO_MEMBERSHIPS: dict[tuple[str, str], WorkspaceMember] = {
    ("ws_acme", "user_acme_admin"): WorkspaceMember(
        workspace_id="ws_acme",
        user_id="user_acme_admin",
        role=Role.ADMIN,
        joined_at="2026-01-01T00:00:00Z",
    ),
    ("ws_acme", "user_acme_member"): WorkspaceMember(
        workspace_id="ws_acme",
        user_id="user_acme_member",
        role=Role.MEMBER,
        joined_at="2026-01-15T00:00:00Z",
    ),
    ("ws_globex", "user_globex_admin"): WorkspaceMember(
        workspace_id="ws_globex",
        user_id="user_globex_admin",
        role=Role.ADMIN,
        joined_at="2026-02-01T00:00:00Z",
    ),
}

# Token Store: token -> user_id (dynamically populated upon login)
_TOKENS: dict[str, str] = {}

security = HTTPBearer(auto_error=False)


def authenticate_user(email: str, password: str) -> tuple[User, str] | None:
    """Authenticate user with email and password, returning (user, token) or None."""
    for user in DEMO_USERS.values():
        if user.email.lower() == email.lower() and verify_password(password, user.password_hash):
            token = f"token_{user.id}_{secrets.token_urlsafe(32)}"
            _TOKENS[token] = user.id
            record_audit_event(
                actor_id=user.id,
                workspace_id="global",
                action="AUTH_SUCCESS",
                target_id=user.id,
            )
            return user, token

    record_audit_event(
        actor_id="anonymous",
        workspace_id="global",
        action="AUTH_FAILURE",
        details={"attempted_email": email},
    )
    return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """Dependency to extract authenticated user from Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = _TOKENS.get(token)
    if not user_id or user_id not in DEMO_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return DEMO_USERS[user_id]


@dataclass
class AuthenticatedMemberContext:
    user: User
    membership: WorkspaceMember
    workspace: Workspace


def get_authenticated_member(
    workspace_id: str,
    user: User = Depends(get_current_user),
    required_role: Role | None = None,
) -> AuthenticatedMemberContext:
    """Validate that the authenticated user belongs to workspace_id and has required_role."""
    workspace = DEMO_WORKSPACES.get(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' does not exist.",
        )

    membership = DEMO_MEMBERSHIPS.get((workspace_id, user.id))
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. User '{user.email}' is not a member of workspace '{workspace_id}'.",
        )

    if required_role == Role.ADMIN and membership.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Operation requires ADMIN role in workspace '{workspace_id}'.",
        )

    return AuthenticatedMemberContext(user=user, membership=membership, workspace=workspace)


def require_member(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> AuthenticatedMemberContext:
    return get_authenticated_member(workspace_id=workspace_id, user=user, required_role=None)


def require_admin(
    workspace_id: str,
    user: User = Depends(get_current_user),
) -> AuthenticatedMemberContext:
    return get_authenticated_member(workspace_id=workspace_id, user=user, required_role=Role.ADMIN)
