"""Pydantic schemas for transcript endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# ── Requests ─────────────────────────────────────────────────────────


class TranscriptUpload(BaseModel):
    account_id: str
    raw_text: str
    call_date: str
    participants: Optional[List[Dict[str, Any]]] = None
    duration_minutes: Optional[int] = None


# ── Responses ────────────────────────────────────────────────────────


class TranscriptItem(BaseModel):
    """Transcript summary used in account detail view."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    call_date: str
    duration_minutes: Optional[int] = None
    token_count: int
    is_active: bool
    created_at: str
    preprocessed_text: Optional[str] = None


class TranscriptResponse(BaseModel):
    """Returned after transcript upload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    call_date: str
    duration_minutes: Optional[int] = None
    token_count: int
    is_active: bool
    created_at: str
