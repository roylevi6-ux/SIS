"""Activity Log — audit trail of all user actions.

Shows a filterable table of user actions with summary metrics.
"""

from __future__ import annotations

import html

import streamlit as st

from sis.services.user_action_log_service import get_action_logs, get_action_summary
from sis.ui.components.layout import page_header, metric_row, section_divider
from sis.ui.theme import Colors


# Display-friendly labels for action types
ACTION_LABELS = {
    "page_view": "Page View",
    "ic_forecast_set": "IC Forecast Set",
    "analysis_run": "Analysis Run",
    "transcript_upload": "Transcript Upload",
    "feedback_submit": "Feedback Submit",
    "chat_query": "Chat Query",
    "brief_export": "Brief Export",
    "calibration": "Calibration",
    "rerun_agent": "Rerun Agent",
    "resynthesize": "Resynthesize",
    "setting_change": "Setting Change",
}

# Color coding for action types
ACTION_COLORS = {
    "page_view": Colors.NEUTRAL,
    "ic_forecast_set": Colors.ACCENT,
    "analysis_run": Colors.PRIMARY,
    "transcript_upload": Colors.SUCCESS,
    "feedback_submit": Colors.WARNING,
    "chat_query": Colors.PRIMARY,
    "brief_export": Colors.ACCENT,
    "calibration": Colors.WARNING,
    "rerun_agent": Colors.PRIMARY,
    "resynthesize": Colors.PRIMARY,
    "setting_change": Colors.DANGER,
}


def render():
    page_header("Activity Log", "Audit trail of all user actions")

    # Filters
    col_days, col_type, col_user = st.columns(3)
    with col_days:
        days = st.selectbox("Time range", [7, 14, 30, 90], index=2, format_func=lambda d: f"Last {d} days")
    with col_type:
        type_options = ["All"] + list(ACTION_LABELS.keys())
        selected_type = st.selectbox(
            "Action type",
            type_options,
            format_func=lambda t: "All Actions" if t == "All" else ACTION_LABELS.get(t, t),
        )
    with col_user:
        user_filter = st.text_input("Filter by user", placeholder="username...")

    # Summary metrics
    summary = get_action_summary(days=days)
    metric_row([
        {"label": "Total Actions", "value": summary["total"]},
        {"label": "Unique Users", "value": len(summary.get("by_user", {}))},
        {"label": "Action Types", "value": len(summary.get("by_type", {}))},
        {"label": "Days Tracked", "value": days},
    ])

    # Top action types bar
    if summary["by_type"]:
        with st.expander("Action Type Breakdown", expanded=False):
            for action_type, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
                label = html.escape(ACTION_LABELS.get(action_type, action_type))
                color = ACTION_COLORS.get(action_type, Colors.NEUTRAL)
                pct = (count / summary["total"] * 100) if summary["total"] > 0 else 0
                st.markdown(
                    f'<div style="display:flex;align-items:center;margin:2px 0">'
                    f'<span style="width:160px;font-size:13px">{label}</span>'
                    f'<div style="flex:1;background:#e5e7eb;border-radius:4px;height:20px;margin:0 8px">'
                    f'<div style="width:{pct:.0f}%;background:{color};border-radius:4px;height:20px"></div>'
                    f'</div>'
                    f'<span style="font-size:13px;color:{Colors.TEXT_SUBTLE}">{count}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    section_divider()

    # Fetch logs
    logs = get_action_logs(
        days=days,
        action_type=selected_type if selected_type != "All" else None,
        user_name=user_filter if user_filter else None,
    )

    if not logs:
        st.info("No actions recorded for the selected filters.")
        return

    st.markdown(f"**Showing {len(logs)} actions**")

    # Render as table
    for log in logs:
        action_label = html.escape(ACTION_LABELS.get(log["action_type"], log["action_type"]))
        color = ACTION_COLORS.get(log["action_type"], Colors.NEUTRAL)
        ts = log["created_at"][:19].replace("T", " ") if log["created_at"] else ""

        detail_parts = []
        if log["action_detail"]:
            detail_parts.append(html.escape(log["action_detail"]))
        if log["account_name"]:
            detail_parts.append(f"Account: {html.escape(log['account_name'])}")
        if log["page_name"]:
            detail_parts.append(f"Page: {html.escape(log['page_name'])}")
        detail_str = " | ".join(detail_parts) if detail_parts else ""

        user_display = html.escape(log["user_name"]) if log["user_name"] else ""

        st.markdown(
            f'<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #f1f5f9;font-size:13px">'
            f'<span style="width:140px;color:{Colors.TEXT_SUBTLE}">{ts}</span>'
            f'<span style="width:100px;font-weight:600">{user_display}</span>'
            f'<span style="width:140px;color:{color};font-weight:500">{action_label}</span>'
            f'<span style="flex:1;color:{Colors.TEXT_SUBTLE}">{detail_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
