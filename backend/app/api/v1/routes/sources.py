from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedMemberContext, require_member
from app.schemas.knowledge import SourceResponse

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["sources"])


@router.get("/sources", response_model=list[SourceResponse])
async def list_workspace_sources(
    workspace_id: str,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> list[SourceResponse]:
    # Return workspace-scoped sources (demo data)
    return [
        SourceResponse(
            id=f"{workspace_id}-source-1",
            title=f"{ctx.workspace.name} Knowledge Base Vol. 1",
            page=1,
            updated_at="Updated 2026-01-10",
        ),
        SourceResponse(
            id=f"{workspace_id}-source-2",
            title=f"{ctx.workspace.name} Standard Operating Procedures",
            page=4,
            updated_at="Updated 2026-02-01",
        ),
    ]
