"""Calibration API routes — current config, patterns, create log, history."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sis.api.deps import get_current_user
from sis.services import calibration_service
from sis.api.schemas.admin import CalibrationCreate

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


@router.get("/current")
def get_current(user: dict = Depends(get_current_user)):
    """Load the current calibration config from YAML."""
    return calibration_service.get_current_calibration()


@router.get("/patterns")
def get_patterns(user: dict = Depends(get_current_user)):
    """Analyze feedback patterns for calibration review."""
    return calibration_service.get_feedback_patterns()


@router.post("")
def create(body: CalibrationCreate, user: dict = Depends(get_current_user)):
    """Persist a calibration change log entry."""
    return calibration_service.create_calibration_log(
        config_version=body.config_version,
        previous_version=body.previous_version,
        changes=body.changes,
        feedback_items_reviewed=body.feedback_items_reviewed,
        approved_by=body.approved_by,
    )


@router.get("/history")
def history(user: dict = Depends(get_current_user)):
    """All calibration logs ordered by date descending."""
    return calibration_service.list_calibration_history()
