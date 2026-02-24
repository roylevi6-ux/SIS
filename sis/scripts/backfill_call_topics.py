"""Backfill call_topics for existing transcripts using AI extraction.

Uses the Haiku topic extractor to generate business-relevant topic labels
from the stored preprocessed_text. Replaces the old Gong-based topics.

Usage:
    python3 -m sis.scripts.backfill_call_topics           # Only fill NULLs
    python3 -m sis.scripts.backfill_call_topics --force    # Re-extract ALL
"""

from __future__ import annotations

import json
import sys
import logging

from sqlalchemy import text as sa_text

from sis.db.engine import init_db, get_engine
from sis.db.session import get_session
from sis.db.models import Transcript
from sis.preprocessor.topic_extractor import extract_business_topics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _ensure_column_exists() -> None:
    """Add call_topics column if it doesn't exist (SQLite ALTER TABLE)."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(sa_text("PRAGMA table_info(transcripts)"))
        columns = {row[1] for row in result}
        if "call_topics" not in columns:
            conn.execute(sa_text("ALTER TABLE transcripts ADD COLUMN call_topics TEXT"))
            conn.commit()
            logger.info("Added call_topics column to transcripts table")


def backfill(force: bool = False) -> int:
    """Backfill call_topics using AI topic extraction.

    Args:
        force: If True, re-extract topics for ALL transcripts (not just NULLs).

    Returns the number of transcripts updated.
    """
    _ensure_column_exists()
    init_db()

    updated = 0
    failed = 0

    with get_session() as session:
        query = session.query(Transcript).filter(
            Transcript.preprocessed_text.isnot(None),
        )
        if not force:
            query = query.filter(Transcript.call_topics.is_(None))

        transcripts = query.all()
        total = len(transcripts)
        logger.info("Found %d transcripts to process (force=%s)", total, force)

        for i, t in enumerate(transcripts):
            logger.info(
                "[%d/%d] Extracting topics for %s (%s)...",
                i + 1, total,
                (t.call_title or "untitled")[:40],
                t.call_date,
            )

            topics = extract_business_topics(
                t.preprocessed_text,
                call_title=t.call_title,
            )

            if topics:
                t.call_topics = json.dumps(topics)
                updated += 1
                names = [tp["name"] for tp in topics]
                logger.info("  → %s", names)
            else:
                failed += 1
                logger.warning("  → extraction failed, skipping")

        session.flush()

    logger.info(
        "Done: %d updated, %d failed, %d total",
        updated, failed, total,
    )
    return updated


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    backfill(force=force_flag)
