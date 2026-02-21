"""Test alert engine, digest, slack notifier."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from sis.db.models import Account, AnalysisRun, DealAssessment, Transcript


def _now(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


class TestAlertEngine:
    def test_check_alerts_score_drop(self, seeded_db, mock_get_session):
        """Add a second assessment with higher health (older) to trigger score_drop on latest."""
        session = mock_get_session
        acct_id = seeded_db["healthy_id"]

        # Need a separate run for the unique constraint on analysis_run_id
        import uuid
        older_run_id = str(uuid.uuid4())
        from sis.db.models import AnalysisRun, DealAssessment
        session.add(AnalysisRun(
            id=older_run_id, account_id=acct_id, started_at=_now(10),
            completed_at=_now(10), status="completed", trigger="test",
        ))
        session.flush()

        older = DealAssessment(
            analysis_run_id=older_run_id, account_id=acct_id,
            deal_memo="Older memo", inferred_stage=3, stage_name="Evaluation",
            stage_confidence=0.75, health_score=99, health_breakdown=json.dumps([]),
            overall_confidence=0.75, momentum_direction="Improving",
            ai_forecast_category="Commit",
            created_at=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        )
        session.add(older)
        session.flush()

        from sis.alerts.engine import check_alerts
        alerts = check_alerts()
        score_drops = [a for a in alerts if a["type"] == "score_drop"]
        assert len(score_drops) >= 1

    def test_check_alerts_stale_call(self, seeded_db, mock_get_session):
        """Make transcripts old to trigger stale_call."""
        session = mock_get_session
        acct_id = seeded_db["critical_id"]

        # Update transcript dates to be very old
        transcripts = session.query(Transcript).filter_by(account_id=acct_id).all()
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        for t in transcripts:
            t.call_date = old_date
        session.flush()

        from sis.alerts.engine import check_alerts
        alerts = check_alerts()
        stale = [a for a in alerts if a["type"] == "stale_call" and a["account_id"] == acct_id]
        assert len(stale) == 1

    def test_check_alerts_new_critical(self, seeded_db, mock_get_session):
        from sis.alerts.engine import check_alerts
        alerts = check_alerts()
        critical = [a for a in alerts if a["type"] == "new_critical"]
        # CriticalInc has health 35 < 45, with single assessment → should trigger
        assert len(critical) >= 1


class TestSlackNotifier:
    def test_send_slack_alert_no_webhook(self):
        from sis.alerts.slack_notifier import send_slack_alert
        with patch("sis.alerts.slack_notifier.SLACK_WEBHOOK_URL", ""):
            result = send_slack_alert({"type": "score_drop", "severity": "critical",
                                       "account_name": "Test", "details": "test"})
            assert result is False

    def test_send_slack_alert_non_critical(self):
        from sis.alerts.slack_notifier import send_slack_alert
        result = send_slack_alert({"type": "stale_call", "severity": "warning",
                                   "account_name": "Test", "details": "test"})
        assert result is False

    def test_send_critical_alerts_count(self):
        from sis.alerts.slack_notifier import send_critical_alerts
        alerts = [
            {"type": "score_drop", "severity": "critical", "account_name": "A", "details": "d"},
            {"type": "stale_call", "severity": "warning", "account_name": "B", "details": "d"},
        ]
        with patch("sis.alerts.slack_notifier.send_slack_alert", return_value=False):
            sent = send_critical_alerts(alerts)
            assert sent == 0


class TestEmailDigest:
    def test_generate_daily_digest(self, seeded_db, mock_get_session):
        from sis.alerts.email_digest import generate_daily_digest
        digest = generate_daily_digest()
        assert "SIS Daily Digest" in digest
        assert "Generated" in digest
