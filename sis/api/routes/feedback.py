"""Feedback API routes — submit, list, resolve, summary."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user
from sis.services import feedback_service
from sis.api.schemas.feedback import FeedbackCreate, FeedbackResolve

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/")
def submit_feedback(body: FeedbackCreate, user: dict = Depends(get_current_user)):
    """Submit score feedback for a deal assessment."""
    try:
        return feedback_service.submit_feedback(
            account_id=body.account_id,
            assessment_id=body.assessment_id,
            author=body.author,
            direction=body.direction,
            reason=body.reason,
            free_text=body.free_text,
            off_channel=body.off_channel,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 422,
            detail=str(e),
        )


@router.get("/")
def list_feedback(
    account_id: Optional[str] = None,
    author: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List feedback with optional filters."""
    return feedback_service.list_feedback(
        account_id=account_id,
        author=author,
        status=status,
    )


@router.patch("/{feedback_id}/resolve")
def resolve(feedback_id: str, body: FeedbackResolve, user: dict = Depends(get_current_user)):
    """Resolve a feedback item."""
    try:
        return feedback_service.resolve_feedback(
            feedback_id=feedback_id,
            resolution=body.resolution,
            notes=body.notes,
            resolved_by=body.resolved_by,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 422,
            detail=str(e),
        )


@router.get("/summary")
def summary(user: dict = Depends(get_current_user)):
    """Aggregated feedback statistics."""
    return feedback_service.get_feedback_summary()
