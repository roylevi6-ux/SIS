"""Slack webhook notifier — push alerts for critical deal changes per PRD P0-23.

Uses urllib.request (no extra dependency) to post to a Slack webhook URL.
Only fires for critical-severity alerts (score_drop, forecast_flip).
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error

from sis.config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


def send_slack_alert(alert: dict) -> bool:
    """Post a single alert to Slack via webhook.

    Args:
        alert: Alert dict from engine.check_alerts() with type, account_name, details, severity.

    Returns:
        True if sent successfully, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured — skipping Slack alert")
        return False

    # Only send critical alerts
    if alert.get("severity") != "critical":
        logger.debug("Skipping non-critical alert for Slack: %s", alert.get("type"))
        return False

    emoji = {
        "score_drop": "\u26a0\ufe0f",
        "forecast_flip": "\ud83d\udd04",
        "new_critical": "\ud83d\udea8",
    }.get(alert["type"], "\u2757")

    text = (
        f"{emoji} *SIS Alert — {alert['type'].replace('_', ' ').title()}*\n"
        f"*Account:* {alert['account_name']}\n"
        f"{alert['details']}"
    )

    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Slack alert sent for %s: %s", alert["account_name"], alert["type"])
                return True
            logger.warning("Slack returned status %d", resp.status)
            return False
    except (urllib.error.URLError, OSError) as e:
        logger.error("Failed to send Slack alert: %s", e)
        return False


def send_critical_alerts(alerts: list[dict]) -> int:
    """Send all critical alerts to Slack.

    Returns count of successfully sent alerts.
    """
    sent = 0
    for alert in alerts:
        if alert.get("severity") == "critical":
            if send_slack_alert(alert):
                sent += 1
    return sent
