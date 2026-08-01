from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.audit import record_audit_event
from app.core.auth import AuthenticatedMemberContext, require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["feedback"])


class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    workspace_id: str,
    request: FeedbackRequest,
    ctx: AuthenticatedMemberContext = Depends(require_member),
) -> FeedbackResponse:
    import uuid

    feedback_id = f"fb_{uuid.uuid4().hex[:10]}"
    record_audit_event(
        actor_id=ctx.user.id,
        workspace_id=workspace_id,
        action="FEEDBACK_SUBMITTED",
        target_id=feedback_id,
        details={"rating": request.rating},
    )
    return FeedbackResponse(status="accepted", feedback_id=feedback_id)
