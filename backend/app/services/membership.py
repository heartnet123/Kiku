from datetime import datetime, timezone
import secrets
import uuid
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.core.audit import get_workspace_audit_logs, record_audit_event
from app.domain.identity import AuditLogEvent, Role, User, WorkspaceMember, hash_password
from app.schemas.workspace import WorkspaceMemberResponse
from app.services.supabase_client import create_supabase_client, response_data


def _db_role(role: Role) -> str:
    return "viewer" if role == Role.MEMBER else role.value


def _response(row: dict[str, Any], user: dict[str, Any]) -> WorkspaceMemberResponse:
    return WorkspaceMemberResponse(
        user_id=str(row["user_id"]),
        email=str(user.get("email") or ""),
        full_name=str(user.get("full_name") or user.get("email") or "Kiku User"),
        role=Role(str(row["role"])),
        joined_at=str(row.get("created_at") or row.get("joined_at") or ""),
    )


class WorkspaceMembershipService:
    """Workspace membership operations via Supabase RLS clients."""

    def __init__(self, *, client: Client | None = None, user_id: str | None = None) -> None:
        self.client = client
        self.user_id = user_id

    def get_members(self, workspace_id: str) -> list[WorkspaceMemberResponse]:
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase connection is not configured.",
            )

        rows = response_data(
            self.client.table("workspace_members")
            .select("workspace_id,user_id,role,created_at")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        user_ids = [str(row["user_id"]) for row in rows]
        users = response_data(
            self.client.table("users").select("id,email,full_name").in_("id", user_ids).execute()
        ) if user_ids else []
        users_by_id = {str(user["id"]): user for user in users}
        return [_response(row, users_by_id.get(str(row["user_id"]), {})) for row in rows]

    def invite_member(
        self, actor_id: str, workspace_id: str, email: str, role: Role
    ) -> WorkspaceMemberResponse:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Use the workspace join flow or configure a Supabase service-role key for email invitations.",
        )

    def update_member_role(
        self, actor_id: str, workspace_id: str, target_user_id: str, new_role: Role
    ) -> WorkspaceMemberResponse:
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase connection is not configured.",
            )

        rows = response_data(
            self.client.table("workspace_members")
            .select("workspace_id,user_id,role,created_at")
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id)
            .execute()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Member not found.")
        existing = rows[0]
        db_role = _db_role(new_role)
        if existing["role"] == "owner" and db_role != "owner":
            raise HTTPException(status_code=400, detail="The workspace owner cannot be demoted.")
        updated = response_data(
            self.client.table("workspace_members")
            .update({"role": db_role})
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id)
            .execute()
        )
        if not updated:
            raise HTTPException(status_code=400, detail="Unable to update member role.")
        users = response_data(
            self.client.table("users").select("id,email,full_name").eq("id", target_user_id).execute()
        )
        return _response(updated[0], users[0] if users else {})

    def remove_member(self, actor_id: str, workspace_id: str, target_user_id: str) -> None:
        if not self.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase connection is not configured.",
            )

        rows = response_data(
            self.client.table("workspace_members")
            .select("role")
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id)
            .execute()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Member not found.")
        if rows[0]["role"] == "owner":
            raise HTTPException(status_code=400, detail="The workspace owner cannot be removed.")
        self.client.table("workspace_members").delete().eq("workspace_id", workspace_id).eq(
            "user_id", target_user_id
        ).execute()

    def get_audit_logs(self, workspace_id: str) -> list[AuditLogEvent]:
        return get_workspace_audit_logs(workspace_id)

