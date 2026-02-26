"""Alert detection engine — identifies significant deal changes per PRD P0-23.

Detects:
  - score_drop: health_score dropped > SCORE_DROP_ALERT_THRESHOLD
  - forecast_flip: ai_forecast_category changed between runs
  - stale_call: no transcript in > STALE_CALL_DAYS_THRESHOLD days
  - new_needs_attention: health_score went below 40
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sis.db.session import get_session
from sis.db.models import Account, DealAssessment, Transcript
from sis.config import SCORE_DROP_ALERT_THRESHOLD, STALE_CALL_DAYS_THRESHOLD


def check_alerts() -> list[dict]:
    """Scan all accounts for alert conditions.

    Returns list of Alert dicts with: type, account_id, account_name, details, severity.
    """
    alerts = []
    now = datetime.now(timezone.utc)
    stale_cutoff = (now - timedelta(days=STALE_CALL_DAYS_THRESHOLD)).strftime("%Y-%m-%d")

    with get_session() as session:
        accounts = session.query(Account).all()

        for acct in accounts:
            # Get latest two assessments
            assessments = (
                session.query(DealAssessment)
                .filter_by(account_id=acct.id)
                .order_by(DealAssessment.created_at.desc())
                .limit(2)
                .all()
            )

            # Stale call check (works even without assessments)
            latest_transcript = (
                session.query(Transcript)
                .filter_by(account_id=acct.id, is_active=1)
                .order_by(Transcript.call_date.desc())
                .first()
            )
            if latest_transcript and latest_transcript.call_date[:10] < stale_cutoff:
                alerts.append({
                    "type": "stale_call",
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "severity": "warning",
                    "details": (
                        f"No transcript in {STALE_CALL_DAYS_THRESHOLD}+ days. "
                        f"Last call: {latest_transcript.call_date}"
                    ),
                })

            if len(assessments) < 2:
                # Check needs_attention on single assessment
                if assessments and assessments[0].health_score < 40:
                    alerts.append({
                        "type": "new_needs_attention",
                        "account_id": acct.id,
                        "account_name": acct.account_name,
                        "severity": "critical",
                        "details": f"Health score is {assessments[0].health_score} (needs attention threshold: 40)",
                    })
                continue

            latest, previous = assessments[0], assessments[1]
            score_delta = latest.health_score - previous.health_score

            # Score drop
            if score_delta <= -SCORE_DROP_ALERT_THRESHOLD:
                alerts.append({
                    "type": "score_drop",
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "severity": "critical",
                    "details": (
                        f"Health dropped {previous.health_score} -> {latest.health_score} "
                        f"({score_delta} pts, threshold: {SCORE_DROP_ALERT_THRESHOLD})"
                    ),
                })

            # Forecast flip
            if latest.ai_forecast_category != previous.ai_forecast_category:
                alerts.append({
                    "type": "forecast_flip",
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "severity": "critical",
                    "details": (
                        f"Forecast changed: {previous.ai_forecast_category} -> "
                        f"{latest.ai_forecast_category}"
                    ),
                })

            # New needs_attention (crossed below 40)
            if latest.health_score < 40 and previous.health_score >= 40:
                alerts.append({
                    "type": "new_needs_attention",
                    "account_id": acct.id,
                    "account_name": acct.account_name,
                    "severity": "critical",
                    "details": (
                        f"Entered needs attention zone: {previous.health_score} -> {latest.health_score}"
                    ),
                })

    return alerts
