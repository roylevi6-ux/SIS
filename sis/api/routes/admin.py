"""Admin API routes — usage tracking, action logs, coaching, prompt versions,
rep scorecard, and forecast data.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from sis.api.deps import get_current_user
from sis.services import (
    usage_tracking_service,
    user_action_log_service,
    coaching_service,
    prompt_version_service,
    rep_scorecard_service,
    forecast_data_service,
)
from sis.api.schemas.admin import (
    CoachingCreate,
    LogActionBody,
    PromptVersionCreate,
    RollbackVersionBody,
    TrackEventBody,
)

router = APIRouter(tags=["admin"])


# ── Usage Tracking ──────────────────────────────────────────────────────


@router.get("/api/tracking/summary")
def get_usage_summary(days: int = 30, user: dict = Depends(get_current_user)):
    """Aggregated usage event counts for the last N days."""
    return usage_tracking_service.get_usage_summary(days=days)


@router.get("/api/tracking/cro-metrics")
def get_cro_metrics(user: dict = Depends(get_current_user)):
    """Compute the 6 CRO success criteria for Week 8 checkpoint."""
    return usage_tracking_service.get_cro_metrics()


@router.post("/api/tracking/event")
def track_event(
    body: TrackEventBody,
    user: dict = Depends(get_current_user),
):
    """Log a usage event. Fire-and-forget."""
    usage_tracking_service.track_event(
        event_type=body.event_type,
        user_name=body.user_name,
        account_id=body.account_id,
        page_name=body.page_name,
        metadata=body.metadata,
    )
    return {"status": "ok"}


# ── Action Logs ─────────────────────────────────────────────────────────


@router.get("/api/logs/actions")
def get_action_logs(
    days: int = 30,
    action_type: Optional[str] = None,
    user_name: Optional[str] = None,
    account_id: Optional[str] = None,
    limit: int = 500,
    user: dict = Depends(get_current_user),
):
    """Query action logs with filters."""
    return user_action_log_service.get_action_logs(
        days=days,
        action_type=action_type,
        user_name=user_name,
        account_id=account_id,
        limit=limit,
    )


@router.get("/api/logs/actions/summary")
def get_action_summary(days: int = 30, user: dict = Depends(get_current_user)):
    """Aggregate action counts by type and user."""
    return user_action_log_service.get_action_summary(days=days)


@router.post("/api/logs/actions")
def log_action(body: LogActionBody, user: dict = Depends(get_current_user)):
    """Log a user action. Fire-and-forget."""
    user_action_log_service.log_action(
        action_type=body.action_type,
        action_detail=body.action_detail,
        user_name=body.user_name,
        account_id=body.account_id,
        account_name=body.account_name,
        page_name=body.page_name,
        session_id=body.session_id,
        metadata=body.metadata,
    )
    return {"status": "ok"}


# ── Coaching ────────────────────────────────────────────────────────────


@router.post("/api/coaching/")
def submit_coaching(body: CoachingCreate, user: dict = Depends(get_current_user)):
    """Submit a coaching entry for a rep on a specific dimension."""
    try:
        return coaching_service.submit_coaching(
            account_id=body.account_id,
            rep_name=body.rep_name,
            coach_name=body.coach_name,
            dimension=body.dimension,
            feedback_text=body.feedback_text,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 422,
            detail=str(e),
        )


@router.get("/api/coaching/")
def list_coaching(
    rep_name: Optional[str] = None,
    account_id: Optional[str] = None,
    dimension: Optional[str] = None,
    incorporated: Optional[bool] = None,
    user: dict = Depends(get_current_user),
):
    """List coaching entries with optional filters."""
    return coaching_service.list_coaching(
        rep_name=rep_name,
        account_id=account_id,
        dimension=dimension,
        incorporated=incorporated,
    )


@router.patch("/api/coaching/{entry_id}/incorporate")
def mark_incorporated(entry_id: str, notes: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Mark a coaching entry as incorporated."""
    try:
        return coaching_service.mark_incorporated(entry_id=entry_id, notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/coaching/summary")
def get_coaching_summary(rep_name: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Aggregate coaching stats: total, by dimension, incorporation rate."""
    return coaching_service.get_coaching_summary(rep_name=rep_name)


@router.get("/api/coaching/check")
def check_incorporation(rep_name: str, user: dict = Depends(get_current_user)):
    """Check pending coaching entries for score improvements."""
    return coaching_service.check_incorporation(rep_name=rep_name)


# ── Prompt Versions ─────────────────────────────────────────────────────


@router.get("/api/prompts/versions")
def list_versions(agent_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """List prompt versions, optionally filtered by agent_id."""
    return prompt_version_service.list_versions(agent_id=agent_id)


@router.get("/api/prompts/versions/active/{agent_id}")
def get_active_version(agent_id: str, user: dict = Depends(get_current_user)):
    """Get the currently active prompt version for an agent."""
    result = prompt_version_service.get_active_version(agent_id=agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No active version for agent {agent_id}")
    return result


@router.post("/api/prompts/versions")
def create_version(body: PromptVersionCreate, user: dict = Depends(get_current_user)):
    """Create a new prompt version, deactivating the previous active version."""
    return prompt_version_service.create_version(
        agent_id=body.agent_id,
        version=body.version,
        prompt_template=body.prompt_template,
        change_notes=body.change_notes,
        calibration_config_version=body.calibration_config_version,
    )


@router.post("/api/prompts/versions/rollback")
def rollback_version(body: RollbackVersionBody, user: dict = Depends(get_current_user)):
    """Reactivate a previous prompt version."""
    try:
        return prompt_version_service.rollback_version(
            agent_id=body.agent_id,
            version_id=body.version_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 422,
            detail=str(e),
        )


@router.get("/api/prompts/versions/diff")
def diff_versions(version_id_a: str, version_id_b: str, user: dict = Depends(get_current_user)):
    """Return a unified diff between two prompt versions."""
    try:
        diff_text = prompt_version_service.diff_versions(
            version_id_a=version_id_a,
            version_id_b=version_id_b,
        )
        return {"diff": diff_text}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Rep Scorecard ───────────────────────────────────────────────────────


@router.get("/api/scorecard/reps")
def get_rep_scorecard(ae_owner: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Compute behavioral scorecards for reps."""
    return rep_scorecard_service.get_rep_scorecard(ae_owner=ae_owner)


# ── Forecast Data ───────────────────────────────────────────────────────


@router.get("/api/forecast/data")
def load_forecast_data(team: Optional[str] = None, team_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Load deal-level forecast data for the comparison view."""
    return forecast_data_service.load_forecast_data(team=team, team_id=team_id)


@router.get("/api/forecast/teams")
def get_team_names(user: dict = Depends(get_current_user)):
    """Return distinct non-null team names."""
    return forecast_data_service.get_team_names()
