from fastapi import HTTPException
import pytest

from app.core.auth import AuthenticatedMemberContext
from app.domain.identity import Role, User, Workspace, WorkspaceMember


def _mock_verify_supabase_token(token: str) -> User:
    if "admin" in token:
        user_id = "user_globex_admin" if "globex" in token else "user_acme_admin"
        email = "admin@globex.com" if "globex" in token else "admin@acme.com"
        return User(id=user_id, email=email, full_name="Admin", password_hash="")
    return User(id="user_acme_member", email="member@acme.com", full_name="Member", password_hash="")


def _mock_get_authenticated_member(
    workspace_id: str,
    user: User,
    access_token: str | None = None,
    required_role: Role | None = None,
) -> AuthenticatedMemberContext:
    is_globex_token = "globex" in (access_token or "")
    if workspace_id == "ws_acme" and is_globex_token:
        raise HTTPException(status_code=403, detail="Access denied")
    if workspace_id == "ws_globex" and not is_globex_token:
        raise HTTPException(status_code=403, detail="Access denied")

    role = Role.MEMBER if ("member" in (access_token or "") and not is_globex_token) else Role.ADMIN
    if required_role == Role.ADMIN and role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Operation requires ADMIN role")

    return AuthenticatedMemberContext(
        user=user,
        membership=WorkspaceMember(
            workspace_id=workspace_id, user_id=user.id, role=role, joined_at="2026-01-01T00:00:00Z"
        ),
        workspace=Workspace(id=workspace_id, name="Workspace", slug=workspace_id),
    )
