"""Feedback service — score feedback CRUD per Technical Architecture Section 6.4."""

from __future__ import annotations

from typing import Optional

from sis.db.session import get_session
from sis.db.models import ScoreFeedback, DealAssessment


VALID_DIRECTIONS = {"too_high", "too_low"}
VALID_CATEGORIES = {
    "off_channel", "stakeholder_context", "stage_mismatch",
    "score_too_high", "recent_change", "other",
}


def submit_feedback(
    account_id: str,
    assessment_id: str,
    author: str,
    direction: str,
    reason: str,
    free_text: Optional[str] = None,
    off_channel: bool = False,
) -> dict:
    """Submit score feedback for a deal assessment."""
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {VALID_DIRECTIONS}")
    if reason not in VALID_CATEGORIES:
        raise ValueError(f"reason must be one of {VALID_CATEGORIES}")

    with get_session() as session:
        # Get the health score at time of feedback
        assessment = session.query(DealAssessment).filter_by(id=assessment_id).one()

        feedback = ScoreFeedback(
            account_id=account_id,
            deal_assessment_id=assessment_id,
            author=author,
            health_score_at_time=assessment.health_score,
            disagreement_direction=direction,
            reason_category=reason,
            free_text=free_text,
            off_channel_activity=1 if off_channel else 0,
        )
        session.add(feedback)
        session.flush()
        return {
            "id": feedback.id,
            "account_id": feedback.account_id,
            "author": feedback.author,
            "direction": feedback.disagreement_direction,
            "reason": feedback.reason_category,
            "health_score_at_time": feedback.health_score_at_time,
        }


def list_feedback(
    account_id: Optional[str] = None,
    author: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """List feedback with optional filters."""
    with get_session() as session:
        query = session.query(ScoreFeedback)
        if account_id:
            query = query.filter_by(account_id=account_id)
        if author:
            query = query.filter_by(author=author)
        if status:
            query = query.filter_by(resolution=status)
        feedback_list = query.order_by(ScoreFeedback.created_at.desc()).all()
        return [
            {
                "id": f.id,
                "account_id": f.account_id,
                "author": f.author,
                "direction": f.disagreement_direction,
                "reason": f.reason_category,
                "free_text": f.free_text,
                "health_score_at_time": f.health_score_at_time,
                "off_channel": bool(f.off_channel_activity),
                "resolution": f.resolution,
                "created_at": f.created_at,
            }
            for f in feedback_list
        ]


def resolve_feedback(
    feedback_id: str,
    resolution: str,
    notes: str,
    resolved_by: str,
) -> dict:
    """Resolve a feedback item."""
    from datetime import datetime, timezone

    if resolution not in {"accepted", "rejected"}:
        raise ValueError("resolution must be 'accepted' or 'rejected'")

    with get_session() as session:
        feedback = session.query(ScoreFeedback).filter_by(id=feedback_id).one()
        feedback.resolution = resolution
        feedback.resolution_notes = notes
        feedback.resolved_by = resolved_by
        feedback.resolved_at = datetime.now(timezone.utc).isoformat()
        session.flush()
        return {"id": feedback.id, "resolution": feedback.resolution}
