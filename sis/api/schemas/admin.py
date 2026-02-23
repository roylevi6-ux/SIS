"""Pydantic schemas for admin endpoints (usage, coaching, calibration, prompts, etc.)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Usage Tracking ───────────────────────────────────────────────────


class UsageSummary(BaseModel):
    """Aggregated usage tracking statistics."""

    total_events: int
    days: int
    by_type: Dict[str, int]
    by_day: Dict[str, int]
    by_user: Dict[str, int]
    by_page: Dict[str, int]


class CROMetric(BaseModel):
    """Single CRO adoption metric."""

    metric: str
    description: str
    target: str
    actual: str
    value: Any = None
    passed: Optional[bool] = None


# ── Action Logs ──────────────────────────────────────────────────────


class ActionLogItem(BaseModel):
    """Single user action log entry."""

    id: str
    user_name: str
    action_type: str
    action_detail: Optional[str] = None
    account_name: Optional[str] = None
    page_name: Optional[str] = None
    created_at: str
    metadata: Dict[str, Any] = {}


class ActionSummary(BaseModel):
    """Aggregated action log statistics."""

    total: int
    days: int
    by_type: Dict[str, int]
    by_user: Dict[str, int]
    by_day: Dict[str, int]


# ── Usage Tracking (request bodies) ──────────────────────────────────


class TrackEventBody(BaseModel):
    event_type: str
    user_name: Optional[str] = None
    account_id: Optional[str] = None
    page_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LogActionBody(BaseModel):
    action_type: str
    action_detail: Optional[str] = None
    user_name: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    page_name: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ── Prompt Rollback (request body) ──────────────────────────────────


class RollbackVersionBody(BaseModel):
    agent_id: str
    version_id: str


# ── Coaching ─────────────────────────────────────────────────────────


class CoachingCreate(BaseModel):
    account_id: str
    rep_name: str
    coach_name: str
    dimension: str
    feedback_text: str


class CoachingItem(BaseModel):
    """Single coaching log entry."""

    id: str
    account_id: str
    account_name: str
    rep_name: str
    coach_name: str
    dimension: str
    coaching_date: str
    feedback_text: str
    dimension_score_at_time: Optional[int] = None
    health_score_at_time: Optional[int] = None
    incorporated: bool = False
    incorporated_at: Optional[str] = None
    incorporated_notes: Optional[str] = None
    created_at: str


class CoachingSummary(BaseModel):
    """Aggregated coaching statistics."""

    total: int
    incorporated: int
    incorporation_rate: float
    by_dimension: Dict[str, int]
    coaches: List[str]


class IncorporationCheck(BaseModel):
    """Result of checking whether coaching was incorporated."""

    entry_id: str
    account_name: str
    dimension: str
    score_at_time: int
    current_score: int
    delta: int
    feedback_text: str


# ── Calibration ──────────────────────────────────────────────────────


class CalibrationCreate(BaseModel):
    config_version: str
    previous_version: Optional[str] = None
    changes: Optional[str] = None
    feedback_items_reviewed: int
    approved_by: Optional[str] = None


class CalibrationHistoryItem(BaseModel):
    """Single calibration history entry."""

    id: str
    calibration_date: str
    config_version: str
    config_previous_version: Optional[str] = None
    feedback_items_reviewed: int
    config_changes: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: str


class FeedbackPattern(BaseModel):
    """Aggregated feedback patterns for calibration analysis."""

    total_feedback: int
    by_reason: Dict[str, int]
    by_direction: Dict[str, int]
    by_agent: Dict[str, int]
    direction_per_agent: Dict[str, Any]
    top_flagged_reasons: List[Any]


# ── Prompts ──────────────────────────────────────────────────────────


class PromptVersionCreate(BaseModel):
    agent_id: str
    version: str
    prompt_template: str
    change_notes: Optional[str] = None
    calibration_config_version: Optional[str] = None


class PromptVersionItem(BaseModel):
    """Single prompt version entry."""

    id: str
    agent_id: str
    version: str
    prompt_template: str
    calibration_config_version: Optional[str] = None
    change_notes: Optional[str] = None
    is_active: bool
    created_at: str


# ── Rep Scorecard ────────────────────────────────────────────────────


class RepScorecard(BaseModel):
    """Aggregated rep performance scorecard."""

    rep_name: str
    total_accounts: int
    scored_accounts: int
    dimensions: Dict[str, Any]
    overall_score: Optional[float] = None
    accounts: List[Any] = []


# ── Forecast Data ────────────────────────────────────────────────────


class ForecastDataItem(BaseModel):
    """Single account's forecast data for export/analysis."""

    account_id: str
    account_name: str
    mrr: float
    team_name: Optional[str] = None
    ae_owner: Optional[str] = None
    ai_forecast: Optional[str] = None
    ic_forecast: Optional[str] = None
    health_score: int
    momentum: str
    divergence: bool
