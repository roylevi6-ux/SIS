"""Transcript service — upload, preprocess, manage per Technical Architecture Section 6.3.

Preprocessing per spec:
1. Speaker label normalization → ROLE_NAME (Company) format
2. Filler word removal
3. Token counting via tiktoken
4. Truncation to 8K tokens if needed
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import tiktoken

from sis.db.session import get_session
from sis.db.models import Transcript
from sis.config import MAX_TRANSCRIPTS_PER_ACCOUNT

logger = logging.getLogger(__name__)

# tiktoken encoder for cl100k_base (used by Claude/GPT-4)
_encoder: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


# Filler words/phrases to remove
FILLER_PATTERNS = [
    r'\b(um|uh|erm|er|ah|like,?\s+you know|you know,?\s+like)\b',
    r'\b(basically|essentially|literally|actually)\b(?=,?\s)',
    r'\b(sort of|kind of)\b(?=\s+(?:like|you know))',
]
FILLER_RE = re.compile('|'.join(FILLER_PATTERNS), re.IGNORECASE)

MAX_TOKEN_BUDGET = 8000


def upload_transcript(
    account_id: str,
    raw_text: str,
    call_date: str,
    participants: Optional[list[dict]] = None,
    duration_minutes: Optional[int] = None,
    gong_call_id: Optional[str] = None,
    call_title: Optional[str] = None,
) -> Transcript:
    """Upload and preprocess a transcript. Enforces 5-transcript limit."""
    with get_session() as session:
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
            call_title=call_title,
            gong_call_id=gong_call_id,
            is_active=1,
        )
        session.add(transcript)
        session.flush()

        # Ensure only the N most recent by call_date stay active.
        # This is safe regardless of import order.
        _enforce_active_limit(session, account_id)

        session.refresh(transcript)
        session.expunge(transcript)
        return transcript


def transcript_exists(account_id: str, gong_call_id: str) -> bool:
    """Check if a transcript with this gong_call_id already exists for the account."""
    if not gong_call_id:
        return False
    with get_session() as session:
        return (
            session.query(Transcript.id)
            .filter_by(account_id=account_id, gong_call_id=gong_call_id)
            .first()
        ) is not None


def _enforce_active_limit(session, account_id: str) -> None:
    """Keep only the N most recent transcripts active (by call_date).

    Called after each insert so that regardless of import order,
    the newest calls are always the active ones.
    """
    all_active = (
        session.query(Transcript)
        .filter_by(account_id=account_id, is_active=1)
        .order_by(Transcript.call_date.desc())
        .all()
    )
    for t in all_active[MAX_TRANSCRIPTS_PER_ACCOUNT:]:
        t.is_active = 0


def normalize_active_transcripts(account_id: str) -> int:
    """Fix active flags so the N most recent by call_date are active.

    Returns the number of transcripts whose active state changed.
    """
    with get_session() as session:
        all_transcripts = (
            session.query(Transcript)
            .filter_by(account_id=account_id)
            .order_by(Transcript.call_date.desc())
            .all()
        )
        changed = 0
        for i, t in enumerate(all_transcripts):
            should_be_active = i < MAX_TRANSCRIPTS_PER_ACCOUNT
            if bool(t.is_active) != should_be_active:
                t.is_active = 1 if should_be_active else 0
                changed += 1
        session.flush()
        return changed


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


def get_active_transcript_ids(account_id: str) -> list[str]:
    """Get IDs of all active transcripts for an account (for audit trail)."""
    with get_session() as session:
        transcripts = (
            session.query(Transcript.id)
            .filter_by(account_id=account_id, is_active=1)
            .order_by(Transcript.call_date.asc())
            .all()
        )
        return [t.id for t in transcripts]


def _preprocess(raw_text: str) -> dict:
    """Full preprocessing per spec Section 6.3.

    1. Speaker label normalization
    2. Filler word removal
    3. Token counting via tiktoken
    4. Truncation to 8K tokens if needed
    """
    text = raw_text

    # Step 1: Remove filler words
    text = _remove_fillers(text)

    # Step 2: Normalize speaker labels
    text = _normalize_speakers(text)

    # Step 3: Count tokens accurately via tiktoken
    encoder = _get_encoder()
    tokens = encoder.encode(text)
    token_count = len(tokens)

    # Step 4: Truncate to token budget if needed
    if token_count > MAX_TOKEN_BUDGET:
        tokens = tokens[:MAX_TOKEN_BUDGET]
        text = encoder.decode(tokens) + "\n\n[TRUNCATED AT 8K TOKENS]"
        token_count = MAX_TOKEN_BUDGET

    return {"text": text, "token_count": token_count}


def _remove_fillers(text: str) -> str:
    """Remove filler words and clean up resulting whitespace."""
    cleaned = FILLER_RE.sub('', text)
    # Clean up double spaces and empty lines left by removals
    cleaned = re.sub(r'  +', ' ', cleaned)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    return cleaned.strip()


def _normalize_speakers(text: str) -> str:
    """Normalize speaker labels to SPEAKER_NAME (COMPANY): format.

    Detects patterns like:
    - "John Smith:" → "JOHN SMITH:"
    - "John Smith (Riskified):" → "JOHN SMITH (Riskified):"
    - Already formatted labels are preserved
    """
    lines = text.split('\n')
    result = []
    for line in lines:
        # Check for speaker labels at start of line
        match = re.match(r'^([A-Za-z][A-Za-z\s.]+?)(\s*\([^)]+\))?\s*:\s*(.*)$', line)
        if match:
            speaker = match.group(1).strip().upper()
            company = match.group(2) or ""
            content = match.group(3)
            result.append(f"{speaker}{company}: {content}")
        else:
            result.append(line)
    return '\n'.join(result)
