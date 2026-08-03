from dataclasses import dataclass
import secrets
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.audit import record_audit_event
from app.domain.identity import Role, User, Workspace, WorkspaceMember, hash_password, verify_password
from app.services.supabase_client import create_supabase_client, response_data

security = HTTPBearer(auto_error=False)



def get_access_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    # Prefer Authorization: Bearer (keeps curl / Postman compatibility)
    if credentials and credentials.credentials:
        return credentials.credentials
    # Fall back to HttpOnly cookie (browser sessions)
    cookie_token = request.cookies.get("kiku_access_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Missing Bearer token or session cookie.",
        headers={"WWW-Authenticate": "Bearer"},
    )


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


def _build_user_workspaces(user_id: str, client: Client | None = None) -> list[dict[str, Any]]:
    if client is None:
        return []

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
    """Verify a Supabase JWT."""
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
    """Validate membership and role against Supabase."""


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

    try:
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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to verify workspace membership.",
        ) from exc
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
