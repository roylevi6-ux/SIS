"""Pydantic schemas for account endpoints."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from .transcripts import TranscriptItem

# ── Allowed IC forecast categories (matches account_service validation) ──

IC_FORECAST_CATEGORIES = {
    "Commit",
    "Realistic",
    "Upside",
    "At Risk",
}


# ── Requests ─────────────────────────────────────────────────────────


class AccountCreate(BaseModel):
    name: str
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    deal_type: str = "new_logo"
    prior_contract_value: Optional[float] = None
    owner_id: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    deal_type: Optional[str] = None
    prior_contract_value: Optional[float] = None
    owner_id: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None


class ICForecastUpdate(BaseModel):
    category: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in IC_FORECAST_CATEGORIES:
            raise ValueError(
                f"Invalid category: {v}. Must be one of {IC_FORECAST_CATEGORIES}"
            )
        return v


# ── Responses ────────────────────────────────────────────────────────


class AssessmentDetail(BaseModel):
    """Full assessment data returned inside AccountDetail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    deal_type: Optional[str] = None
    stage_model: Optional[str] = None
    deal_memo: Optional[str] = None
    health_score: Optional[int] = None
    health_breakdown: Any = None
    momentum_direction: Optional[str] = None
    momentum_trend: Optional[str] = None
    ai_forecast_category: Optional[str] = None
    forecast_rationale: Optional[str] = None
    inferred_stage: Optional[int] = None
    stage_name: Optional[str] = None
    stage_confidence: Optional[float] = None
    overall_confidence: Optional[float] = None
    key_unknowns: List[Any] = []
    top_positive_signals: List[Any] = []
    top_risks: List[Any] = []
    recommended_actions: List[Any] = []
    contradiction_map: List[Any] = []
    divergence_flag: bool = False
    divergence_explanation: Optional[str] = None
    sf_stage_at_run: Optional[int] = None
    sf_forecast_at_run: Optional[str] = None
    sf_close_quarter_at_run: Optional[str] = None
    cp_estimate_at_run: Optional[float] = None
    stage_gap_direction: Optional[str] = None
    stage_gap_magnitude: Optional[int] = None
    forecast_gap_direction: Optional[str] = None
    sf_gap_interpretation: Optional[str] = None
    created_at: str


class AccountSummary(BaseModel):
    """Account row in the pipeline list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_name: str
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    deal_type: str = "new_logo"
    ic_forecast_category: Optional[str] = None
    health_score: Optional[int] = None
    momentum_direction: Optional[str] = None
    ai_forecast_category: Optional[str] = None
    inferred_stage: Optional[int] = None
    stage_name: Optional[str] = None
    overall_confidence: Optional[float] = None
    divergence_flag: bool = False
    last_assessed: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
    stage_gap_direction: Optional[str] = None
    stage_gap_magnitude: Optional[int] = None
    forecast_gap_direction: Optional[str] = None


class AccountDetail(BaseModel):
    """Full account detail with assessment and transcripts."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_name: str
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    deal_type: str = "new_logo"
    prior_contract_value: Optional[float] = None
    ic_forecast_category: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
    transcripts: List[TranscriptItem] = []
    assessment: Optional[AssessmentDetail] = None


class ICForecastResponse(BaseModel):
    """Returned after setting IC forecast category."""

    divergence_flag: bool
    explanation: Optional[str] = None
