"""Alert system — daily email digest + Slack push for critical changes.

Public API:
  - check_alerts(): detect alert conditions across all accounts
  - send_slack_alert(alert): push a single alert to Slack
  - generate_daily_digest(): produce markdown summary of alerts + insights
"""

from sis.alerts.engine import check_alerts
from sis.alerts.slack_notifier import send_slack_alert, send_critical_alerts
from sis.alerts.email_digest import generate_daily_digest

__all__ = [
    "check_alerts",
    "send_slack_alert",
    "send_critical_alerts",
    "generate_daily_digest",
]
