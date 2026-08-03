from pydantic import BaseModel, EmailStr, Field
from app.domain.identity import Role


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Supabase refresh token for session renewal")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=120)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    role: Role
    owner_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class LoginResponse(BaseModel):
    token: str | None = None
    refresh_token: str | None = None
    user: UserResponse
    workspaces: list[WorkspaceResponse]
    requires_email_confirmation: bool = False


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=64)


class WorkspaceJoinRequest(BaseModel):
    workspace_id: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=64)


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
