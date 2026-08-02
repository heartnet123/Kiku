from datetime import datetime, timezone
import secrets
import uuid
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.core.audit import get_workspace_audit_logs, record_audit_event
from app.core.auth import DEMO_MEMBERSHIPS, DEMO_USERS
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
    """Workspace membership operations for demo fixtures and Supabase RLS clients."""

    def __init__(self, *, client: Client | None = None, user_id: str | None = None) -> None:
        self.client = client
        self.user_id = user_id

    def _get_admin_count(self, workspace_id: str) -> int:
        return sum(
            1
            for (ws_id, _), membership in DEMO_MEMBERSHIPS.items()
            if ws_id == workspace_id and membership.role == Role.ADMIN
        )

    def get_members(self, workspace_id: str) -> list[WorkspaceMemberResponse]:
        if not self.client:
            members: list[WorkspaceMemberResponse] = []
            for (ws_id, user_id), membership in list(DEMO_MEMBERSHIPS.items()):
                if ws_id == workspace_id and user_id in DEMO_USERS:
                    user = DEMO_USERS[user_id]
                    members.append(
                        WorkspaceMemberResponse(
                            user_id=user.id,
                            email=user.email,
                            full_name=user.full_name,
                            role=membership.role,
                            joined_at=membership.joined_at,
                        )
                    )
            return members

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
        if self.client:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Use the workspace join flow or configure a Supabase service-role key for email invitations.",
            )

        user = next((item for item in DEMO_USERS.values() if item.email.lower() == email.lower()), None)
        if not user:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            user = User(
                id=user_id,
                email=email,
                full_name=email.split("@")[0].capitalize(),
                password_hash=hash_password(secrets.token_urlsafe(16)),
            )
            DEMO_USERS[user_id] = user

        if (workspace_id, user.id) in DEMO_MEMBERSHIPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{email}' is already a member of this workspace.",
            )

        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role,
            joined_at=datetime.now(timezone.utc).isoformat(),
        )
        DEMO_MEMBERSHIPS[(workspace_id, user.id)] = membership
        record_audit_event(
            actor_id=actor_id,
            workspace_id=workspace_id,
            action="MEMBER_INVITED",
            target_id=user.id,
            details={"email": email, "role": role.value},
        )
        return WorkspaceMemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            joined_at=membership.joined_at,
        )

    def update_member_role(
        self, actor_id: str, workspace_id: str, target_user_id: str, new_role: Role
    ) -> WorkspaceMemberResponse:
        if self.client:
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

        key = (workspace_id, target_user_id)
        existing = DEMO_MEMBERSHIPS.get(key)
        if not existing or target_user_id not in DEMO_USERS:
            raise HTTPException(status_code=404, detail="Member not found.")
        if existing.role == Role.ADMIN and new_role != Role.ADMIN and self._get_admin_count(workspace_id) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the sole remaining workspace administrator.",
            )
        updated = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user_id,
            role=new_role,
            joined_at=existing.joined_at,
        )
        DEMO_MEMBERSHIPS[key] = updated
        user = DEMO_USERS[target_user_id]
        record_audit_event(
            actor_id=actor_id,
            workspace_id=workspace_id,
            action="ROLE_UPDATED",
            target_id=target_user_id,
            details={"old_role": existing.role.value, "new_role": new_role.value},
        )
        return WorkspaceMemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=updated.role,
            joined_at=updated.joined_at,
        )

    def remove_member(self, actor_id: str, workspace_id: str, target_user_id: str) -> None:
        if self.client:
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
            return

        key = (workspace_id, target_user_id)
        existing = DEMO_MEMBERSHIPS.get(key)
        if not existing:
            raise HTTPException(status_code=404, detail="Member not found.")
        if existing.role == Role.ADMIN and self._get_admin_count(workspace_id) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the sole remaining workspace administrator.",
            )
        del DEMO_MEMBERSHIPS[key]
        record_audit_event(
            actor_id=actor_id,
            workspace_id=workspace_id,
            action="MEMBER_REMOVED",
            target_id=target_user_id,
        )

    def get_audit_logs(self, workspace_id: str) -> list[AuditLogEvent]:
        return get_workspace_audit_logs(workspace_id)
