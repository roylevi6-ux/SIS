"""Calibration cycle tooling service — per PRD P0-18, Sec 7.9.

Analyzes feedback patterns, reads calibration config, and logs calibration changes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import yaml

from collections import defaultdict

from sis.db.session import get_session
from sis.db.models import CalibrationLog, DealContextEntry

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config" / "calibration"


def get_feedback_patterns() -> dict:
    """Analyze deal context entries for calibration insights."""
    with get_session() as session:
        entries = (
            session.query(DealContextEntry)
            .filter(DealContextEntry.is_active == 1, DealContextEntry.superseded_by.is_(None))
            .all()
        )

        by_question: dict[int, int] = defaultdict(int)
        by_account: dict[str, int] = defaultdict(int)

        for e in entries:
            by_question[e.question_id] += 1
            by_account[e.account_id] += 1

        return {
            "total_entries": len(entries),
            "by_question": dict(by_question),
            "accounts_with_context": len(by_account),
            "by_account": dict(by_account),
        }


def get_current_calibration() -> dict:
    """Load the current calibration config from YAML."""
    current_path = CONFIG_DIR / "current.yml"
    if not current_path.exists():
        return {}
    with open(current_path) as f:
        return yaml.safe_load(f) or {}


def create_calibration_log(
    config_version: str,
    previous_version: Optional[str] = None,
    changes: Optional[str] = None,
    feedback_items_reviewed: int = 0,
    approved_by: Optional[str] = None,
) -> dict:
    """Persist a calibration change log entry."""
    with get_session() as session:
        log = CalibrationLog(
            config_version=config_version,
            config_previous_version=previous_version,
            config_changes=changes,
            feedback_items_reviewed=feedback_items_reviewed,
            approved_by=approved_by,
        )
        session.add(log)
        session.flush()
        return {
            "id": log.id,
            "config_version": log.config_version,
            "calibration_date": log.calibration_date,
            "approved_by": log.approved_by,
        }


def list_calibration_history() -> list[dict]:
    """All calibration logs ordered by date descending."""
    with get_session() as session:
        logs = (
            session.query(CalibrationLog)
            .order_by(CalibrationLog.calibration_date.desc())
            .all()
        )
        return [
            {
                "id": log.id,
                "calibration_date": log.calibration_date,
                "config_version": log.config_version,
                "config_previous_version": log.config_previous_version,
                "feedback_items_reviewed": log.feedback_items_reviewed,
                "config_changes": log.config_changes,
                "approved_by": log.approved_by,
                "created_at": log.created_at,
            }
            for log in logs
        ]
