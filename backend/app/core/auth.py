from dataclasses import dataclass
import secrets
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.audit import record_audit_event
from app.domain.identity import Role, User, Workspace, WorkspaceMember, hash_password, verify_password
from app.services.supabase_client import create_supabase_client, response_data

# Local demo fixtures remain available for unit tests and the development persona picker.
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

DEMO_MEMBERSHIPS: dict[tuple[str, str], WorkspaceMember] = {
    (
        "ws_acme",
        "user_acme_admin",
    ): WorkspaceMember(
        workspace_id="ws_acme",
        user_id="user_acme_admin",
        role=Role.ADMIN,
        joined_at="2026-01-01T00:00:00Z",
    ),
    (
        "ws_acme",
        "user_acme_member",
    ): WorkspaceMember(
        workspace_id="ws_acme",
        user_id="user_acme_member",
        role=Role.MEMBER,
        joined_at="2026-01-15T00:00:00Z",
    ),
    (
        "ws_globex",
        "user_globex_admin",
    ): WorkspaceMember(
        workspace_id="ws_globex",
        user_id="user_globex_admin",
        role=Role.ADMIN,
        joined_at="2026-02-01T00:00:00Z",
    ),
}

_TOKENS: dict[str, str] = {}
security = HTTPBearer(auto_error=False)


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def _role(value: str | Role) -> Role:
    try:
        return Role(value)
    except ValueError:
        return Role.VIEWER


def _user_from_claims(claims: dict[str, Any]) -> User:
    metadata = claims.get("user_metadata") or claims.get("app_metadata") or {}
    email = str(claims.get("email") or "")
    return User(
        id=str(claims["sub"]),
        email=email,
        full_name=str(metadata.get("full_name") or email.split("@")[0] or "Kiku User"),
        password_hash="",
    )


def _user_from_auth_user(auth_user: Any, full_name: str | None = None) -> User:
    metadata = getattr(auth_user, "user_metadata", None) or {}
    email = str(getattr(auth_user, "email", "") or "")
    return User(
        id=str(getattr(auth_user, "id")),
        email=email,
        full_name=str(full_name or metadata.get("full_name") or email.split("@")[0] or "Kiku User"),
        password_hash="",
    )


def _build_demo_workspaces(user_id: str) -> list[dict[str, Any]]:
    workspaces: list[dict[str, Any]] = []
    for (workspace_id, member_id), membership in DEMO_MEMBERSHIPS.items():
        if member_id != user_id:
            continue
        workspace = DEMO_WORKSPACES.get(workspace_id)
        if workspace:
            workspaces.append(
                {
                    "id": workspace.id,
                    "name": workspace.name,
                    "slug": workspace.slug,
                    "role": membership.role,
                }
            )
    return workspaces


def _build_user_workspaces(user_id: str, client: Client | None = None) -> list[dict[str, Any]]:
    if client is None:
        return _build_demo_workspaces(user_id)

    membership_rows = response_data(
        client.table("workspace_members")
        .select("workspace_id,role")
        .eq("user_id", user_id)
        .execute()
    )
    workspace_ids = [str(row["workspace_id"]) for row in membership_rows]
    if not workspace_ids:
        return []

    workspace_rows = response_data(
        client.table("workspaces")
        .select("id,name,slug")
        .in_("id", workspace_ids)
        .execute()
    )
    roles = {str(row["workspace_id"]): _role(str(row["role"])) for row in membership_rows}
    return [
        {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "slug": str(row["slug"]),
            "role": roles.get(str(row["id"]), Role.VIEWER),
        }
        for row in workspace_rows
    ]


def _login_response(
    token: str | None,
    refresh_token: str | None,
    user: User,
    workspaces: list[dict[str, Any]],
    *,
    requires_email_confirmation: bool = False,
) -> dict[str, Any]:
    return {
        "token": token,
        "refresh_token": refresh_token,
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "workspaces": workspaces,
        "requires_email_confirmation": requires_email_confirmation,
    }


def authenticate_user(email: str, password: str) -> tuple[User, str] | None:
    """Authenticate only the local demo personas used by tests and development."""
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


def _verify_supabase_token(token: str) -> User:
    client = create_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured.",
        )

    try:
        claims_response = client.auth.get_claims(token)
        claims = getattr(claims_response, "claims", None) or {}
        if not claims.get("sub"):
            raise ValueError("JWT has no subject")
        return _user_from_claims(claims)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(token: str = Depends(get_access_token)) -> User:
    """Verify a Supabase JWT, with the local demo token as an explicit test fallback."""
    user_id = _TOKENS.get(token)
    if user_id and user_id in DEMO_USERS:
        return DEMO_USERS[user_id]
    return _verify_supabase_token(token)


@dataclass
class AuthenticatedMemberContext:
    user: User
    membership: WorkspaceMember
    workspace: Workspace
    supabase: Client | None = None
    access_token: str | None = None


def get_authenticated_member(
    workspace_id: str,
    user: User,
    access_token: str | None = None,
    required_role: Role | None = None,
) -> AuthenticatedMemberContext:
    """Validate membership and role against Supabase or the explicit demo fixtures."""
    demo_workspace = DEMO_WORKSPACES.get(workspace_id)
    demo_membership = DEMO_MEMBERSHIPS.get((workspace_id, user.id))
    if user.id in DEMO_USERS and not demo_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. User '{user.email}' is not a member of workspace '{workspace_id}'.",
        )
    if demo_workspace and demo_membership:
        if required_role == Role.ADMIN and demo_membership.role not in {Role.ADMIN, Role.OWNER}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Operation requires ADMIN role in workspace '{workspace_id}'.",
            )
        return AuthenticatedMemberContext(
            user=user,
            membership=demo_membership,
            workspace=demo_workspace,
        )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client = create_supabase_client(access_token)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase connection is not configured.",
        )

    workspace_rows = response_data(
        client.table("workspaces").select("id,name,slug").eq("id", workspace_id).execute()
    )
    if not workspace_rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' does not exist.",
        )

    membership_rows = response_data(
        client.table("workspace_members")
        .select("workspace_id,user_id,role,created_at")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not membership_rows:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. User '{user.email}' is not a member of workspace '{workspace_id}'.",
        )

    membership_row = membership_rows[0]
    membership_role = _role(str(membership_row["role"]))
    if required_role == Role.ADMIN and membership_role not in {Role.OWNER, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Operation requires ADMIN role in workspace '{workspace_id}'.",
        )

    workspace_row = workspace_rows[0]
    return AuthenticatedMemberContext(
        user=user,
        membership=WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=membership_role,
            joined_at=str(membership_row.get("created_at") or ""),
        ),
        workspace=Workspace(
            id=str(workspace_row["id"]),
            name=str(workspace_row["name"]),
            slug=str(workspace_row["slug"]),
        ),
        supabase=client,
        access_token=access_token,
    )


def require_member(
    workspace_id: str,
    user: User = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> AuthenticatedMemberContext:
    return get_authenticated_member(
        workspace_id=workspace_id,
        user=user,
        access_token=access_token,
        required_role=None,
    )


def require_admin(
    workspace_id: str,
    user: User = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> AuthenticatedMemberContext:
    return get_authenticated_member(
        workspace_id=workspace_id,
        user=user,
        access_token=access_token,
        required_role=Role.ADMIN,
    )
