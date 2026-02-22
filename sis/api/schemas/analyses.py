"""Pydantic schemas for analysis endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Requests ─────────────────────────────────────────────────────────


class AnalysisRequest(BaseModel):
    account_id: str


# ── Responses ────────────────────────────────────────────────────────


class AnalysisRunResponse(BaseModel):
    """Returned after running a full analysis pipeline."""

    run_id: str
    status: str
    wall_clock_seconds: float
    total_cost_usd: float
    agents_completed: int
    agents_total: int
    errors: List[Any] = []
    validation_warnings: List[str] = []


class AnalysisHistoryItem(BaseModel):
    """Single entry in analysis run history."""

    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    total_cost_usd: Optional[float] = None
    total_input_tokens: Optional[int] = None
    total_output_tokens: Optional[int] = None


class AgentAnalysisResponse(BaseModel):
    """Individual agent analysis result."""

    agent_id: str
    agent_name: str
    narrative: Optional[str] = None
    findings: Any = None
    evidence: List[Any] = []
    confidence_overall: Optional[float] = None
    confidence_rationale: Optional[str] = None
    data_gaps: List[Any] = []
    sparse_data_flag: bool = False
    model_used: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    status: str


class RerunResponse(BaseModel):
    """Returned after rerunning a single agent."""

    agent_id: str
    status: str
    warnings: List[str] = []
    input_tokens: int
    output_tokens: int


class ResynthesizeResponse(BaseModel):
    """Returned after resynthesizing deal assessment."""

    status: str
    health_score: int
    forecast_category: str
    input_tokens: int
    output_tokens: int


class AnalysisStatusResponse(BaseModel):
    """Current status of an analysis run."""

    run_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
