"""Calibration API routes — current config, patterns, create log, history."""

from __future__ import annotations

from fastapi import APIRouter

from sis.services import calibration_service
from sis.api.schemas.admin import CalibrationCreate

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


@router.get("/current")
def get_current():
    """Load the current calibration config from YAML."""
    return calibration_service.get_current_calibration()


@router.get("/patterns")
def get_patterns():
    """Analyze feedback patterns for calibration review."""
    return calibration_service.get_feedback_patterns()


@router.post("/")
def create(body: CalibrationCreate):
    """Persist a calibration change log entry."""
    return calibration_service.create_calibration_log(
        config_version=body.config_version,
        previous_version=body.previous_version,
        changes=body.changes,
        feedback_items_reviewed=body.feedback_items_reviewed,
        approved_by=body.approved_by,
    )


@router.get("/history")
def history():
    """All calibration logs ordered by date descending."""
    return calibration_service.list_calibration_history()
