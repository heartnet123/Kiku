import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import (
    AuthenticatedMemberContext,
    _build_user_workspaces,
    get_access_token,
    get_current_user,
    require_member,
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
        role=Role(role) if not isinstance(role, Role) else role,
        owner_id=str(row["owner_id"]) if row.get("owner_id") else None,
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> list[WorkspaceResponse]:
    """Retrieve all workspaces accessible by the current authenticated user."""
    client = create_supabase_client(token)
    if not client:
        raise HTTPException(status_code=503, detail="Supabase connection is not configured.")
    workspaces = _build_user_workspaces(user.id, client)
    return [
        WorkspaceResponse(
            id=w["id"],
            name=w["name"],
            slug=w["slug"],
            role=Role(w["role"]) if not isinstance(w["role"], Role) else w["role"],
        )
        for w in workspaces
    ]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> WorkspaceResponse:
    """Retrieve details for a specific workspace if the user is a member."""
    return WorkspaceResponse(
        id=ctx.workspace.id,
        name=ctx.workspace.name,
        slug=ctx.workspace.slug,
        role=ctx.membership.role,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> WorkspaceResponse:
    """Create a new workspace, assigning the creator as owner."""
    raw_name = request.name.strip()
    if not raw_name:
        raise HTTPException(status_code=422, detail="Workspace name cannot be empty.")

    slug = _slugify(request.slug or raw_name)
    client = create_supabase_client(token)
    if not client:
        raise HTTPException(status_code=503, detail="Supabase connection is not configured.")

    # Check if slug already exists. The DB owns the real guarantee (unique index on
    # workspaces.slug), so this only turns the common case into a clearer error.
    try:
        existing = response_data(
            client.table("workspaces").select("id").eq("slug", slug).execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Unable to verify workspace slug availability."
        ) from exc

    if existing:
        # If slug was custom, return 409 conflict; if auto-generated, make it unique
        if request.slug:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workspace with slug '{slug}' already exists.",
            )
        slug = f"{slug[:55]}-{uuid.uuid4().hex[:6]}"

    try:
        rows = response_data(
            client.table("workspaces")
            .insert({"name": raw_name, "slug": slug, "owner_id": user.id})
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to create workspace. Slug may be duplicated.") from exc

    if not rows:
        raise HTTPException(status_code=400, detail="Workspace creation returned no row.")

    ws = rows[0]
    try:
        client.table("workspace_members").insert(
            {"workspace_id": str(ws["id"]), "user_id": user.id, "role": "owner"}
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unable to create workspace membership.") from exc

    return _response(ws, Role.OWNER)


@router.post("/join", response_model=WorkspaceResponse)
async def join_workspace(
    request: WorkspaceJoinRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
) -> WorkspaceResponse:
    if not request.workspace_id and not request.slug:
        raise HTTPException(status_code=422, detail="workspace_id or slug is required.")

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
