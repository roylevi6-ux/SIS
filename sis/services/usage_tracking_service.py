"""Usage tracking service — event logging and CRO metrics per PRD Sec 12 Condition 1.

Tracks page views, chat queries, brief views, and other user interactions.
Computes the 6 CRO success criteria for the Week 8 checkpoint.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sis.db.session import get_session
from sis.db.models import UsageEvent, DealAssessment, Account

logger = logging.getLogger(__name__)


def track_event(
    event_type: str,
    user_name: Optional[str] = None,
    account_id: Optional[str] = None,
    page_name: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Log a usage event. Fire-and-forget — exceptions are swallowed to avoid disrupting UI."""
    try:
        with get_session() as session:
            event = UsageEvent(
                event_type=event_type,
                user_name=user_name,
                account_id=account_id,
                page_name=page_name,
                event_metadata=json.dumps(metadata) if metadata else None,
            )
            session.add(event)
    except Exception:
        logger.exception("Failed to track event: %s", event_type)


def get_usage_summary(days: int = 30) -> dict:
    """Aggregate event counts by type, by day, and by user for the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with get_session() as session:
        events = (
            session.query(UsageEvent)
            .filter(UsageEvent.created_at >= cutoff)
            .order_by(UsageEvent.created_at.desc())
            .all()
        )

    by_type: dict[str, int] = defaultdict(int)
    by_day: dict[str, int] = defaultdict(int)
    by_user: dict[str, int] = defaultdict(int)
    by_page: dict[str, int] = defaultdict(int)

    for e in events:
        by_type[e.event_type] += 1
        day = e.created_at[:10] if e.created_at else "unknown"
        by_day[day] += 1
        if e.user_name:
            by_user[e.user_name] += 1
        if e.page_name:
            by_page[e.page_name] += 1

    return {
        "total_events": len(events),
        "days": days,
        "by_type": dict(by_type),
        "by_day": dict(sorted(by_day.items())),
        "by_user": dict(by_user),
        "by_page": dict(by_page),
    }


def get_cro_metrics() -> list[dict]:
    """Compute the 6 CRO success criteria for Week 8 checkpoint.

    Returns list of dicts with: metric, target, actual, passed.
    """
    now = datetime.now(timezone.utc)

    with get_session() as session:
        # --- 1. Deal coverage: % of accounts with assessment < 14 days old ---
        total_accounts = session.query(Account).count()
        cutoff_14d = (now - timedelta(days=14)).isoformat()
        accounts_with_recent = (
            session.query(DealAssessment.account_id)
            .filter(DealAssessment.created_at >= cutoff_14d)
            .distinct()
            .count()
        )
        coverage_pct = (accounts_with_recent / total_accounts * 100) if total_accounts > 0 else 0

        # --- 2. TL engagement: users with 3+ chat queries/week for 4 consecutive weeks ---
        cutoff_28d = (now - timedelta(days=28)).isoformat()
        chat_events = (
            session.query(UsageEvent)
            .filter(
                UsageEvent.event_type == "chat_query",
                UsageEvent.created_at >= cutoff_28d,
            )
            .all()
        )
        engaged_users = _count_engaged_users(chat_events, now)

        # --- 3. Pipeline review adoption: brief_view events in 4+ distinct weeks ---
        brief_events = (
            session.query(UsageEvent)
            .filter(UsageEvent.event_type == "brief_view")
            .all()
        )
        brief_weeks = set()
        for e in brief_events:
            if e.created_at:
                try:
                    dt = datetime.fromisoformat(e.created_at)
                    brief_weeks.add(dt.isocalendar()[:2])  # (year, week)
                except ValueError:
                    pass
        adoption_weeks = len(brief_weeks)

        # --- 5. VP forecast usage: forecast page views ---
        forecast_views = (
            session.query(UsageEvent)
            .filter(
                UsageEvent.event_type == "page_view",
                UsageEvent.page_name == "Forecast Comparison",
            )
            .count()
        )

    # --- 6. Forecast accuracy: placeholder ---
    forecast_accuracy = None  # Needs runtime outcome data

    return [
        {
            "metric": "Deal Coverage",
            "description": "Accounts with assessment < 14 days old",
            "target": "80%",
            "actual": f"{coverage_pct:.0f}%",
            "value": coverage_pct,
            "passed": coverage_pct >= 80,
        },
        {
            "metric": "TL Engagement",
            "description": "Users with 3+ chat queries/week for 4 weeks",
            "target": "2+ users",
            "actual": str(engaged_users),
            "value": engaged_users,
            "passed": engaged_users >= 2,
        },
        {
            "metric": "Pipeline Review Adoption",
            "description": "Deal briefs viewed in 4+ distinct weeks",
            "target": "4 weeks",
            "actual": f"{adoption_weeks} weeks",
            "value": adoption_weeks,
            "passed": adoption_weeks >= 4,
        },
        {
            "metric": "Score Feedback",
            "description": "Total feedback submissions from TLs",
            "target": "10+",
            "actual": "0",
            "value": 0,
            "passed": False,
        },
        {
            "metric": "VP Forecast Usage",
            "description": "Forecast comparison page views",
            "target": "5+",
            "actual": str(forecast_views),
            "value": forecast_views,
            "passed": forecast_views >= 5,
        },
        {
            "metric": "Forecast Accuracy",
            "description": "AI vs actual outcomes (needs closed-deal data)",
            "target": "TBD",
            "actual": "N/A" if forecast_accuracy is None else f"{forecast_accuracy:.0f}%",
            "value": forecast_accuracy,
            "passed": None,  # Cannot evaluate yet
        },
    ]


def _count_engaged_users(chat_events: list, now: datetime) -> int:
    """Count users with 3+ chat queries per week for 4 consecutive weeks."""
    user_weeks: dict[str, set] = defaultdict(set)
    for e in chat_events:
        user = e.user_name or "anonymous"
        if e.created_at:
            try:
                dt = datetime.fromisoformat(e.created_at)
                week_key = dt.isocalendar()[:2]
                user_weeks[user].add(week_key)
            except ValueError:
                pass

    # For each user, count weeks with 3+ queries
    user_week_counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for e in chat_events:
        user = e.user_name or "anonymous"
        if e.created_at:
            try:
                dt = datetime.fromisoformat(e.created_at)
                week_key = dt.isocalendar()[:2]
                user_week_counts[user][week_key] += 1
            except ValueError:
                pass

    engaged = 0
    for user, weeks in user_week_counts.items():
        qualifying_weeks = sum(1 for count in weeks.values() if count >= 3)
        if qualifying_weeks >= 4:
            engaged += 1
    return engaged
