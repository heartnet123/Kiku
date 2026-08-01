from datetime import datetime, timezone
import uuid

from fastapi import HTTPException, status

from app.core.audit import get_workspace_audit_logs, record_audit_event
from app.core.auth import DEMO_MEMBERSHIPS, DEMO_USERS
from app.domain.identity import AuditLogEvent, Role, User, WorkspaceMember, hash_password
from app.schemas.workspace import WorkspaceMemberResponse


class WorkspaceMembershipService:
    """Service to handle workspace member operations and audit logging."""

    def _get_admin_count(self, workspace_id: str) -> int:
        return sum(
            1 for (ws_id, _), m in DEMO_MEMBERSHIPS.items()
            if ws_id == workspace_id and m.role == Role.ADMIN
        )

    def get_members(self, workspace_id: str) -> list[WorkspaceMemberResponse]:
        members: list[WorkspaceMemberResponse] = []
        for (ws_id, u_id), membership in list(DEMO_MEMBERSHIPS.items()):
            if ws_id == workspace_id and u_id in DEMO_USERS:
                user = DEMO_USERS[u_id]
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

    def invite_member(
        self, actor_id: str, workspace_id: str, email: str, role: Role
    ) -> WorkspaceMemberResponse:
        user = None
        for u in DEMO_USERS.values():
            if u.email.lower() == email.lower():
                user = u
                break

        if not user:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            user = User(
                id=user_id,
                email=email,
                full_name=email.split("@")[0].capitalize(),
                password_hash=hash_password("user123"),
            )
            DEMO_USERS[user_id] = user

        if (workspace_id, user.id) in DEMO_MEMBERSHIPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{email}' is already a member of this workspace.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role,
            joined_at=now_iso,
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
        key = (workspace_id, target_user_id)
        existing = DEMO_MEMBERSHIPS.get(key)
        if not existing or target_user_id not in DEMO_USERS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member '{target_user_id}' not found in workspace '{workspace_id}'.",
            )

        if existing.role == Role.ADMIN and new_role != Role.ADMIN:
            if self._get_admin_count(workspace_id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the sole remaining workspace administrator.",
                )

        old_role = existing.role
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
            details={"old_role": old_role.value, "new_role": new_role.value},
        )

        return WorkspaceMemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=updated.role,
            joined_at=updated.joined_at,
        )

    def remove_member(self, actor_id: str, workspace_id: str, target_user_id: str) -> None:
        key = (workspace_id, target_user_id)
        existing = DEMO_MEMBERSHIPS.get(key)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member '{target_user_id}' not found in workspace '{workspace_id}'.",
            )

        if existing.role == Role.ADMIN:
            if self._get_admin_count(workspace_id) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
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
