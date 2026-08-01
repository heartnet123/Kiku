from fastapi import APIRouter, Depends, status

from app.core.auth import AuthenticatedMemberContext, require_admin, require_member
from app.schemas.workspace import (
    AuditLogResponse,
    MemberInviteRequest,
    RoleUpdateRequest,
    WorkspaceMemberResponse,
)
from app.services.membership import WorkspaceMembershipService

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["members"])


def get_membership_service() -> WorkspaceMembershipService:
    return WorkspaceMembershipService()


@router.get("/members", response_model=list[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
    service: WorkspaceMembershipService = Depends(get_membership_service),
) -> list[WorkspaceMemberResponse]:
    return service.get_members(workspace_id)


@router.post("/members/invite", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_workspace_member(
    workspace_id: str,
    request: MemberInviteRequest,
    ctx: AuthenticatedMemberContext = Depends(require_admin),
    service: WorkspaceMembershipService = Depends(get_membership_service),
) -> WorkspaceMemberResponse:
    return service.invite_member(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        email=request.email,
        role=request.role,
    )


@router.patch("/members/{user_id}/role", response_model=WorkspaceMemberResponse)
async def update_member_role(
    workspace_id: str,
    user_id: str,
    request: RoleUpdateRequest,
    ctx: AuthenticatedMemberContext = Depends(require_admin),
    service: WorkspaceMembershipService = Depends(get_membership_service),
) -> WorkspaceMemberResponse:
    return service.update_member_role(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        target_user_id=user_id,
        new_role=request.role,
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_admin),
    service: WorkspaceMembershipService = Depends(get_membership_service),
) -> None:
    service.remove_member(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        target_user_id=user_id,
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_admin),
    service: WorkspaceMembershipService = Depends(get_membership_service),
) -> list[AuditLogResponse]:
    logs = service.get_audit_logs(workspace_id)
    return [
        AuditLogResponse(
            id=log.id,
            actor_id=log.actor_id,
            workspace_id=log.workspace_id,
            action=log.action,
            target_id=log.target_id,
            timestamp=log.timestamp,
            details=log.details,
        )
        for log in logs
    ]
