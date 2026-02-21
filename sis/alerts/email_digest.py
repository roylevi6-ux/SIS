"""Email digest generator — daily morning summary per PRD P0-23.

Produces a markdown string summarizing all alerts and pipeline insights.
For POC: renders in the Daily Digest UI page. Actual email delivery post-POC.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sis.alerts.engine import check_alerts
from sis.services.dashboard_service import get_pipeline_insights


def generate_daily_digest() -> str:
    """Generate a markdown daily digest combining alerts and pipeline insights.

    Returns:
        Markdown string suitable for display or email body.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    alerts = check_alerts()
    insights = get_pipeline_insights()

    lines = [
        f"# SIS Daily Digest",
        f"*Generated {now}*",
        "",
    ]

    # --- Alerts section ---
    critical_alerts = [a for a in alerts if a["severity"] == "critical"]
    warning_alerts = [a for a in alerts if a["severity"] == "warning"]

    if critical_alerts:
        lines.append(f"## Critical Alerts ({len(critical_alerts)})")
        lines.append("")
        for a in critical_alerts:
            lines.append(f"- **{a['account_name']}** — {a['type'].replace('_', ' ').title()}: {a['details']}")
        lines.append("")

    if warning_alerts:
        lines.append(f"## Warnings ({len(warning_alerts)})")
        lines.append("")
        for a in warning_alerts:
            lines.append(f"- **{a['account_name']}** — {a['details']}")
        lines.append("")

    if not alerts:
        lines.append("## Alerts")
        lines.append("")
        lines.append("No alerts today.")
        lines.append("")

    # --- Insights section ---
    lines.append("## Pipeline Insights")
    lines.append("")

    insight_sections = [
        ("Stuck Deals", insights["stuck"]),
        ("Declining Deals", insights["declining"]),
        ("Improving Deals", insights["improving"]),
        ("New Risks", insights["new_risks"]),
        ("Forecast Flips", insights["forecast_flips"]),
        ("Stale Deals", insights["stale"]),
    ]

    has_any = False
    for section_name, items in insight_sections:
        if items:
            has_any = True
            lines.append(f"### {section_name} ({len(items)})")
            for item in items:
                lines.append(f"- **{item['account_name']}**: {item['description']}")
            lines.append("")

    if not has_any:
        lines.append("No significant pipeline changes detected.")
        lines.append("")

    # --- Summary stats ---
    lines.append("---")
    lines.append(f"*Total alerts: {len(alerts)} | "
                 f"Critical: {len(critical_alerts)} | "
                 f"Warnings: {len(warning_alerts)}*")

    return "\n".join(lines)
