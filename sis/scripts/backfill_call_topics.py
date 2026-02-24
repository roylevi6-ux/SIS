"""Backfill call_topics for existing transcripts.

Parses the "TOPICS:" line from preprocessed_text (written by gong_parser),
extracts topic names and durations, normalizes for display, and stores as JSON.

Usage:
    python3 -m sis.scripts.backfill_call_topics
"""

from __future__ import annotations

import json
import re
import logging

from sqlalchemy import text as sa_text

from sis.db.engine import init_db, get_engine
from sis.db.session import get_session
from sis.db.models import Transcript
from sis.services.transcript_service import normalize_topic_name

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Matches: "Pricing (120s), Integration (90s)"
_TOPIC_ENTRY_RE = re.compile(r"([^,(]+?)\s*\((\d+)s\)")

# Matches the full TOPICS line in preprocessed_text
_TOPICS_LINE_RE = re.compile(r"TOPICS:\s*(.+)")


def _ensure_column_exists() -> None:
    """Add call_topics column if it doesn't exist (SQLite ALTER TABLE)."""
    engine = get_engine()
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(sa_text("PRAGMA table_info(transcripts)"))
        columns = {row[1] for row in result}
        if "call_topics" not in columns:
            conn.execute(sa_text("ALTER TABLE transcripts ADD COLUMN call_topics TEXT"))
            conn.commit()
            logger.info("Added call_topics column to transcripts table")


def _parse_topics_line(line: str) -> list[dict]:
    """Parse 'Pricing (120s), Integration (90s)' into [{"name": ..., "duration": ...}]."""
    entries = _TOPIC_ENTRY_RE.findall(line)
    return [{"name": name.strip(), "duration": int(dur)} for name, dur in entries]


def backfill() -> int:
    """Backfill call_topics from preprocessed_text TOPICS lines.

    Returns the number of transcripts updated.
    """
    _ensure_column_exists()
    init_db()

    updated = 0
    with get_session() as session:
        # Find transcripts with no call_topics but with preprocessed_text
        transcripts = (
            session.query(Transcript)
            .filter(
                Transcript.call_topics.is_(None),
                Transcript.preprocessed_text.isnot(None),
            )
            .all()
        )

        logger.info("Found %d transcripts to check for TOPICS lines", len(transcripts))

        for t in transcripts:
            match = _TOPICS_LINE_RE.search(t.preprocessed_text)
            if not match:
                continue

            raw_topics = _parse_topics_line(match.group(1))
            if not raw_topics:
                continue

            # Take top 2 by duration, normalize names
            top_topics = sorted(raw_topics, key=lambda x: -x["duration"])[:2]
            normalized = [
                {"name": normalize_topic_name(entry["name"]), "duration": entry["duration"]}
                for entry in top_topics
            ]

            t.call_topics = json.dumps(normalized)
            updated += 1

        session.flush()

    logger.info("Backfilled call_topics for %d transcripts", updated)
    return updated


if __name__ == "__main__":
    backfill()
