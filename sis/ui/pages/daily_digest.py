"""Daily Digest — alert summary + pipeline insights per PRD P0-23.

Renders the daily digest markdown in-app. Actual email delivery is post-POC.
Also provides Slack push button for critical alerts.
"""

from __future__ import annotations

import html

import streamlit as st

from sis.alerts.engine import check_alerts
from sis.alerts.email_digest import generate_daily_digest
from sis.alerts.slack_notifier import send_critical_alerts
from sis.ui.components.layout import page_header, section_divider, metric_row
from sis.ui.theme import Colors


def render():
    page_header("Daily Digest", "Morning summary: deal changes, new risks, significant score drops")

    # Single check_alerts call, reused everywhere
    alerts = check_alerts()
    critical = [a for a in alerts if a["severity"] == "critical"]
    warnings = [a for a in alerts if a["severity"] == "warning"]

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Refresh Digest", key="digest_refresh", type="primary"):
            st.rerun()
    with col2:
        if st.button("Push Critical to Slack", key="digest_slack"):
            sent = send_critical_alerts(alerts)
            if sent:
                st.toast(f"Sent {sent} critical alert(s) to Slack", icon="\u2705")
            else:
                st.toast("No critical alerts to send (or Slack not configured)", icon="\u2139\ufe0f")

    # Alert summary metrics
    metric_row([
        {"label": "Total Alerts", "value": len(alerts)},
        {"label": "Critical", "value": len(critical), "color": Colors.DANGER},
        {"label": "Warnings", "value": len(warnings), "color": Colors.WARNING},
    ])

    section_divider()

    # Critical alerts with clickable accounts
    if critical:
        st.subheader("Critical Alerts")
        for a in critical:
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                with c1:
                    if st.button(a["account_name"], key=f"digest_{a['account_id']}_{a['type']}"):
                        st.session_state["selected_account_id"] = a["account_id"]
                        st.rerun()
                with c2:
                    type_label = a["type"].replace("_", " ").title()
                    details = html.escape(a.get("details", ""))
                    st.markdown(
                        f'<span style="color:{Colors.DANGER};font-weight:bold">{type_label}</span>: '
                        f'{details}',
                        unsafe_allow_html=True,
                    )
        section_divider()

    # Full digest markdown (pass alerts to avoid re-querying)
    digest_md = generate_daily_digest()

    with st.expander("Full Digest (Markdown)", expanded=not critical):
        st.markdown(digest_md)

    # Download digest
    st.download_button(
        label="Download Digest (Markdown)",
        data=digest_md,
        file_name="sis_daily_digest.md",
        mime="text/markdown",
        key="digest_download",
    )
