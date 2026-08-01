from pydantic import BaseModel, EmailStr, Field
from app.domain.identity import Role


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    role: Role


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
    workspaces: list[WorkspaceResponse]


class WorkspaceMemberResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: Role
    joined_at: str


class MemberInviteRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of user to invite")
    role: Role = Field(default=Role.MEMBER, description="Role to assign")


class RoleUpdateRequest(BaseModel):
    role: Role = Field(..., description="New role for member")


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    workspace_id: str
    action: str
    target_id: str | None
    timestamp: str
    details: dict
