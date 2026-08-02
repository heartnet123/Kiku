import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import (
    DEMO_MEMBERSHIPS,
    DEMO_USERS,
    DEMO_WORKSPACES,
    get_access_token,
    get_current_user,
)
from app.domain.identity import Role, User, Workspace, WorkspaceMember
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceJoinRequest, WorkspaceResponse
from app.services.supabase_client import create_supabase_client, response_data

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or f"workspace-{uuid.uuid4().hex[:8]}")[:64]


def _response(row: dict, role: str | Role) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=str(row["id"]),
        name=str(row["name"]),
        slug=str(row["slug"]),
        role=Role(role),
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> WorkspaceResponse:
    slug = _slugify(request.slug or request.name)
    if user.id in DEMO_USERS:
        workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
        workspace = Workspace(id=workspace_id, name=request.name.strip(), slug=slug)
        DEMO_WORKSPACES[workspace_id] = workspace
        DEMO_MEMBERSHIPS[(workspace_id, user.id)] = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=Role.ADMIN,
            joined_at="2026-01-01T00:00:00Z",
        )
        return _response({"id": workspace.id, "name": workspace.name, "slug": workspace.slug}, Role.ADMIN)

    client = create_supabase_client(token)
    if not client:
        raise HTTPException(status_code=503, detail="Supabase connection is not configured.")
    try:
        rows = response_data(
            client.table("workspaces")
            .insert({"name": request.name.strip(), "slug": slug, "owner_id": user.id})
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to create workspace.") from exc
    if not rows:
        raise HTTPException(status_code=400, detail="Workspace creation returned no row.")
    return _response(rows[0], Role.OWNER)


@router.post("/join", response_model=WorkspaceResponse)
async def join_workspace(
    request: WorkspaceJoinRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> WorkspaceResponse:
    if not request.workspace_id and not request.slug:
        raise HTTPException(status_code=422, detail="workspace_id or slug is required.")

    if user.id in DEMO_USERS:
        workspace = DEMO_WORKSPACES.get(request.workspace_id or "")
        if not workspace and request.slug:
            workspace = next((item for item in DEMO_WORKSPACES.values() if item.slug == request.slug), None)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found.")
        DEMO_MEMBERSHIPS.setdefault(
            (workspace.id, user.id),
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=Role.MEMBER,
                joined_at="2026-01-01T00:00:00Z",
            ),
        )
        return _response({"id": workspace.id, "name": workspace.name, "slug": workspace.slug}, Role.MEMBER)

    client = create_supabase_client(token)
    if not client:
        raise HTTPException(status_code=503, detail="Supabase connection is not configured.")
    function = "join_workspace_by_id" if request.workspace_id else "join_workspace_by_slug"
    argument = {"target_workspace_id": request.workspace_id} if request.workspace_id else {"target_slug": request.slug}
    try:
        rows = response_data(client.rpc(function, argument).execute())
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to join workspace. Check the workspace identifier or apply the join migration.",
        ) from exc
    if not rows:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return _response(rows[0], rows[0].get("role", Role.VIEWER))
