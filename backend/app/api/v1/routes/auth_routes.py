from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import DEMO_MEMBERSHIPS, DEMO_WORKSPACES, authenticate_user, get_current_user, security
from app.domain.identity import User
from app.schemas.workspace import LoginRequest, LoginResponse, UserResponse, WorkspaceResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_user_workspaces(user_id: str) -> list[WorkspaceResponse]:
    user_workspaces: list[WorkspaceResponse] = []
    for (ws_id, u_id), membership in DEMO_MEMBERSHIPS.items():
        if u_id == user_id and ws_id in DEMO_WORKSPACES:
            ws = DEMO_WORKSPACES[ws_id]
            user_workspaces.append(
                WorkspaceResponse(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    role=membership.role,
                )
            )
    return user_workspaces


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    result = authenticate_user(request.email, request.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user, token = result
    user_workspaces = _build_user_workspaces(user.id)

    return LoginResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspaces=user_workspaces,
    )


@router.get("/me", response_model=LoginResponse)
async def get_me(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> LoginResponse:
    token = credentials.credentials if credentials else ""
    user_workspaces = _build_user_workspaces(user.id)
    return LoginResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspaces=user_workspaces,
    )
