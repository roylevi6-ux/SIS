"""Transcript service — upload, preprocess, manage per Technical Architecture Section 6.3."""

from __future__ import annotations

import json
from typing import Optional

from sis.db.session import get_session
from sis.db.models import Transcript
from config import MAX_TRANSCRIPTS_PER_ACCOUNT


def upload_transcript(
    account_id: str,
    raw_text: str,
    call_date: str,
    participants: Optional[list[dict]] = None,
    duration_minutes: Optional[int] = None,
) -> Transcript:
    """Upload and preprocess a transcript. Enforces 5-transcript limit."""
    with get_session() as session:
        # Check active transcript count
        active_count = (
            session.query(Transcript)
            .filter_by(account_id=account_id, is_active=1)
            .count()
        )

        # Archive oldest if at limit
        if active_count >= MAX_TRANSCRIPTS_PER_ACCOUNT:
            oldest = (
                session.query(Transcript)
                .filter_by(account_id=account_id, is_active=1)
                .order_by(Transcript.call_date.asc())
                .first()
            )
            if oldest:
                oldest.is_active = 0

        # Basic preprocessing (token counting)
        preprocessed = _preprocess(raw_text)

        transcript = Transcript(
            account_id=account_id,
            call_date=call_date,
            participants=json.dumps(participants) if participants else None,
            duration_minutes=duration_minutes,
            raw_text=raw_text,
            preprocessed_text=preprocessed["text"],
            token_count=preprocessed["token_count"],
            is_active=1,
        )
        session.add(transcript)
        session.flush()
        session.expunge(transcript)
        return transcript


def list_transcripts(account_id: str, active_only: bool = True) -> list[dict]:
    """Transcripts for account, ordered by call_date DESC."""
    with get_session() as session:
        query = session.query(Transcript).filter_by(account_id=account_id)
        if active_only:
            query = query.filter_by(is_active=1)
        transcripts = query.order_by(Transcript.call_date.desc()).all()
        return [
            {
                "id": t.id,
                "call_date": t.call_date,
                "duration_minutes": t.duration_minutes,
                "token_count": t.token_count,
                "is_active": bool(t.is_active),
                "created_at": t.created_at,
                "preprocessed_text": t.preprocessed_text,
            }
            for t in transcripts
        ]


def get_active_transcript_texts(account_id: str) -> list[str]:
    """Get preprocessed text for all active transcripts (for pipeline input)."""
    with get_session() as session:
        transcripts = (
            session.query(Transcript)
            .filter_by(account_id=account_id, is_active=1)
            .order_by(Transcript.call_date.asc())
            .all()
        )
        return [t.preprocessed_text or t.raw_text for t in transcripts]


def _preprocess(raw_text: str) -> dict:
    """Basic preprocessing: estimate token count, truncate if needed."""
    # Simple token estimation: ~4 chars per token for English
    estimated_tokens = len(raw_text) // 4
    text = raw_text

    # Truncate to 8K token budget if needed
    max_chars = 8000 * 4  # ~8K tokens
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[TRUNCATED AT 8K TOKENS]"
        estimated_tokens = 8000

    return {"text": text, "token_count": estimated_tokens}
