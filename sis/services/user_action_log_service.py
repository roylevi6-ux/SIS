"""User action log service — structured audit trail of all user actions.

Provides a richer, queryable action log beyond usage_tracking_service events.
Each action captures: who, what, which account, when, and contextual metadata.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sis.db.session import get_session
from sis.db.models import UserActionLog

logger = logging.getLogger(__name__)

# ── Action type constants ──────────────────────────────────────────────

ACTION_PAGE_VIEW = "page_view"
ACTION_FORECAST_SET = "forecast_set"
ACTION_ANALYSIS_RUN = "analysis_run"
ACTION_TRANSCRIPT_UPLOAD = "transcript_upload"
ACTION_FEEDBACK_SUBMIT = "feedback_submit"
ACTION_CHAT_QUERY = "chat_query"
ACTION_BRIEF_EXPORT = "brief_export"
ACTION_CALIBRATION = "calibration"
ACTION_RERUN_AGENT = "rerun_agent"
ACTION_RESYNTHESIZE = "resynthesize"
ACTION_SETTING_CHANGE = "setting_change"


def log_action(
    action_type: str,
    action_detail: Optional[str] = None,
    user_name: Optional[str] = None,
    account_id: Optional[str] = None,
    account_name: Optional[str] = None,
    page_name: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Log a user action. Fire-and-forget — never raises."""
    try:
        with get_session() as session:
            entry = UserActionLog(
                user_name=user_name,
                action_type=action_type,
                action_detail=action_detail,
                account_id=account_id,
                account_name=account_name,
                page_name=page_name,
                session_id=session_id,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            session.add(entry)
    except Exception:
        logger.exception("Failed to log action: %s", action_type)


def get_action_logs(
    days: int = 30,
    action_type: Optional[str] = None,
    user_name: Optional[str] = None,
    account_id: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Query action logs with filters.

    Returns list of dicts, most recent first.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with get_session() as session:
        query = (
            session.query(UserActionLog)
            .filter(UserActionLog.created_at >= cutoff)
        )
        if action_type:
            query = query.filter(UserActionLog.action_type == action_type)
        if user_name:
            query = query.filter(UserActionLog.user_name == user_name)
        if account_id:
            query = query.filter(UserActionLog.account_id == account_id)

        rows = (
            query
            .order_by(UserActionLog.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": r.id,
                "user_name": r.user_name or "anonymous",
                "action_type": r.action_type,
                "action_detail": r.action_detail or "",
                "account_name": r.account_name or "",
                "page_name": r.page_name or "",
                "created_at": r.created_at,
                "metadata": json.loads(r.metadata_json) if r.metadata_json else {},
            }
            for r in rows
        ]


def get_action_summary(days: int = 30) -> dict:
    """Aggregate action counts by type and user for the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with get_session() as session:
        rows = (
            session.query(UserActionLog)
            .filter(UserActionLog.created_at >= cutoff)
            .all()
        )

    by_type: dict[str, int] = defaultdict(int)
    by_user: dict[str, int] = defaultdict(int)
    by_day: dict[str, int] = defaultdict(int)

    for r in rows:
        by_type[r.action_type] += 1
        by_user[r.user_name or "anonymous"] += 1
        day = r.created_at[:10] if r.created_at else "unknown"
        by_day[day] += 1

    return {
        "total": len(rows),
        "days": days,
        "by_type": dict(by_type),
        "by_user": dict(by_user),
        "by_day": dict(sorted(by_day.items())),
    }
