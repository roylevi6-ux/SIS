"""Pydantic schemas for dashboard endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Pipeline Overview ────────────────────────────────────────────────


class PipelineDeal(BaseModel):
    """Single deal in the pipeline view."""

    account_id: str
    account_name: str
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    ic_forecast_category: Optional[str] = None
    last_call_date: Optional[str] = None
    health_score: Optional[int] = None
    momentum_direction: Optional[str] = None
    ai_forecast_category: Optional[str] = None
    inferred_stage: Optional[int] = None
    stage_name: Optional[str] = None
    overall_confidence: Optional[float] = None
    divergence_flag: bool = False
    deal_memo_preview: Optional[str] = None


class PipelineSummary(BaseModel):
    """Aggregate counts and MRR totals for pipeline buckets."""

    healthy_count: int
    neutral_count: int
    needs_attention_count: int
    unscored_count: int
    total_mrr_healthy: float
    total_mrr_neutral: float
    total_mrr_needs_attention: float


class PipelineOverviewResponse(BaseModel):
    """Full pipeline overview with categorised deals."""

    total_deals: int
    healthy: List[PipelineDeal] = []
    neutral: List[PipelineDeal] = []
    needs_attention: List[PipelineDeal] = []
    unscored: List[PipelineDeal] = []
    summary: PipelineSummary


# ── Divergence ───────────────────────────────────────────────────────


class DivergenceItem(BaseModel):
    """Deal where AI and IC forecast categories diverge."""

    account_id: str
    account_name: str
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ai_forecast_category: str
    ic_forecast_category: Optional[str] = None
    health_score: int
    divergence_explanation: Optional[str] = None
    forecast_rationale: Optional[str] = None


# ── Team Rollup ──────────────────────────────────────────────────────


class TeamRollupItem(BaseModel):
    """Aggregated health metrics for a single team."""

    team_name: str
    total_deals: int
    scored_deals: int
    avg_health_score: Optional[float] = None
    healthy_count: int
    neutral_count: int
    needs_attention_count: int
    total_mrr: float
    divergent_count: int


# ── Trends ───────────────────────────────────────────────────────────


class DealTrendDataPoint(BaseModel):
    """Single point in a deal's health trend."""

    date: str
    health_score: int
    momentum: str
    forecast: str


class DealTrendItem(BaseModel):
    """Health trend for a single deal across assessments."""

    account_id: str
    account_name: str
    team_name: Optional[str] = None
    ae_owner: Optional[str] = None
    data_points: List[DealTrendDataPoint] = []
    first_score: int
    last_score: int
    delta: int
    trend_direction: str


class TeamTrendItem(BaseModel):
    """Aggregated trend data for a team."""

    team_name: str
    deal_count: int
    avg_health: float
    avg_delta: float
    improving_count: int
    declining_count: int
    stable_count: int
    team_direction: str


class PortfolioSummary(BaseModel):
    """Portfolio-level trend summary."""

    total_deals: int
    improving: int
    stable: int
    declining: int
    avg_delta: float
    portfolio_direction: str
    biggest_improver: Optional[Dict[str, Any]] = None
    biggest_decliner: Optional[Dict[str, Any]] = None


# ── Pipeline Insights ────────────────────────────────────────────────


class PipelineInsight(BaseModel):
    """Auto-generated insight about a deal."""

    account_id: str
    account_name: str
    health_score: Optional[int] = None
    description: str
    # Additional optional fields vary by insight type
    cp_estimate: Optional[float] = None
    team_name: Optional[str] = None
    ae_owner: Optional[str] = None
    momentum_direction: Optional[str] = None
    ai_forecast_category: Optional[str] = None
    inferred_stage: Optional[int] = None
    stage_name: Optional[str] = None
    previous_health_score: Optional[int] = None
    delta: Optional[int] = None
    previous_forecast: Optional[str] = None
    current_forecast: Optional[str] = None
    last_call_date: Optional[str] = None
    days_since_call: Optional[int] = None
    top_risks: Optional[List[Any]] = None
    new_risks: Optional[List[Any]] = None


class PipelineInsightsResponse(BaseModel):
    """All auto-generated pipeline insights grouped by type."""

    stuck: List[PipelineInsight] = []
    improving: List[PipelineInsight] = []
    declining: List[PipelineInsight] = []
    new_risks: List[PipelineInsight] = []
    stale: List[PipelineInsight] = []
    forecast_flips: List[PipelineInsight] = []
