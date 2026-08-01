from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import DEMO_MEMBERSHIPS, DEMO_WORKSPACES, authenticate_user, get_current_user
from app.domain.identity import User
from app.schemas.workspace import LoginRequest, LoginResponse, UserResponse, WorkspaceResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    result = authenticate_user(request.email, request.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user, token = result

    # Find workspaces where user is a member
    user_workspaces: list[WorkspaceResponse] = []
    for (ws_id, u_id), membership in DEMO_MEMBERSHIPS.items():
        if u_id == user.id and ws_id in DEMO_WORKSPACES:
            ws = DEMO_WORKSPACES[ws_id]
            user_workspaces.append(
                WorkspaceResponse(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    role=membership.role,
                )
            )

    return LoginResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspaces=user_workspaces,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name)
