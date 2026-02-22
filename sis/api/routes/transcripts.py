"""Transcript API routes — list and upload."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sis.services import transcript_service
from sis.api.schemas.transcripts import TranscriptUpload

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


@router.get("/{account_id}")
def list_transcripts(account_id: str, active_only: bool = True):
    """List transcripts for an account."""
    return transcript_service.list_transcripts(account_id, active_only=active_only)


@router.post("/")
def upload_transcript(body: TranscriptUpload):
    """Upload and preprocess a new transcript."""
    transcript = transcript_service.upload_transcript(
        account_id=body.account_id,
        raw_text=body.raw_text,
        call_date=body.call_date,
        participants=body.participants,
        duration_minutes=body.duration_minutes,
    )
    return {
        "id": transcript.id,
        "account_id": transcript.account_id,
        "call_date": transcript.call_date,
        "token_count": transcript.token_count,
        "is_active": bool(transcript.is_active),
        "created_at": transcript.created_at,
    }
