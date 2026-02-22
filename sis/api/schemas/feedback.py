"""Pydantic schemas for feedback endpoints."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


# ── Requests ─────────────────────────────────────────────────────────


class FeedbackCreate(BaseModel):
    account_id: str
    assessment_id: str
    author: str
    direction: str
    reason: str
    free_text: Optional[str] = None
    off_channel: bool = False


class FeedbackResolve(BaseModel):
    resolution: str
    notes: str
    resolved_by: str


# ── Responses ────────────────────────────────────────────────────────


class FeedbackItem(BaseModel):
    """Single feedback entry with joined account name."""

    id: str
    account_id: str
    account_name: str
    deal_assessment_id: str
    author: str
    direction: str
    reason: str
    free_text: Optional[str] = None
    health_score_at_time: int
    off_channel: bool = False
    resolution: Optional[str] = None
    created_at: str


class FeedbackSummary(BaseModel):
    """Aggregated feedback statistics."""

    total: int
    by_direction: Dict[str, int]
    by_reason: Dict[str, int]
    by_author: Dict[str, int]
    by_resolution: Dict[str, int]
    authors: List[str]
