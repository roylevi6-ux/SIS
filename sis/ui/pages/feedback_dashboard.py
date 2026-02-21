"""Feedback Dashboard — VP-level aggregated feedback view per PRD P0-17.

Filterable by TL, signal direction, resolution status.
Includes resolution buttons and account drill-down.
"""

from __future__ import annotations

import streamlit as st

from sis.services.feedback_service import list_feedback, resolve_feedback, get_feedback_summary
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, status_badge, empty_state,
)
from sis.ui.theme import Colors


def render():
    page_header("Feedback Dashboard", "All TL score feedback across deals")

    # Show resolution toasts from previous rerun
    for key in list(st.session_state.keys()):
        if key.startswith("resolved_"):
            resolution = st.session_state.pop(key)
            icon = "\u2705" if resolution == "accepted" else "\u274c"
            st.toast(f"Feedback {resolution}", icon=icon)

    summary = get_feedback_summary()

    if summary["total"] == 0:
        empty_state(
            "No feedback submitted yet",
            "\U0001f4ec",
            "Score feedback will appear here once team leads submit it.",
        )
        return

    # --- Summary metrics ---
    resolved = summary["by_resolution"].get("accepted", 0) + summary["by_resolution"].get("rejected", 0)
    metric_row([
        {"label": "Total Feedback", "value": summary["total"]},
        {"label": "Too High", "value": summary["by_direction"].get("too_high", 0)},
        {"label": "Too Low", "value": summary["by_direction"].get("too_low", 0)},
        {"label": "Pending", "value": summary["by_resolution"].get("pending", 0)},
        {"label": "Resolved", "value": resolved},
    ])

    section_divider()

    # --- Filter sidebar ---
    with st.sidebar:
        st.markdown("**Feedback Filters**")
        author_options = ["All"] + summary["authors"]
        selected_author = st.selectbox("Author", author_options, key="fb_author_filter")
        selected_direction = st.radio(
            "Direction", ["All", "too_high", "too_low"], key="fb_direction_filter"
        )
        selected_status = st.radio(
            "Resolution", ["All", "pending", "accepted", "rejected"], key="fb_status_filter"
        )

    # --- Apply filters ---
    filter_author = None if selected_author == "All" else selected_author
    filter_status = None if selected_status == "All" else selected_status
    feedback = list_feedback(author=filter_author, status=filter_status)
    if selected_direction != "All":
        feedback = [f for f in feedback if f["direction"] == selected_direction]

    if not feedback:
        empty_state(
            "No feedback matches the current filters",
            "\U0001f50d",
            "Try adjusting the filters in the sidebar.",
        )
        return

    # --- Reason breakdown ---
    st.subheader("Feedback by Reason")
    reasons = {}
    for f in feedback:
        r = f["reason"]
        reasons[r] = reasons.get(r, 0) + 1
    cols = st.columns(min(len(reasons), 4))
    for i, (reason, count) in enumerate(sorted(reasons.items(), key=lambda x: -x[1])):
        with cols[i % len(cols)]:
            st.metric(reason.replace("_", " ").title(), count)

    section_divider()

    # --- Group by account for drill-down ---
    st.subheader(f"Feedback Items ({len(feedback)})")

    by_account: dict[str, list] = {}
    for f in feedback:
        name = f.get("account_name", f["account_id"])
        if name not in by_account:
            by_account[name] = []
        by_account[name].append(f)

    for account_name, items in sorted(by_account.items()):
        with st.expander(f"{account_name} ({len(items)} items)", expanded=len(by_account) <= 5):
            for f in items:
                if f["resolution"] == "accepted":
                    resolution_status = "success"
                elif f["resolution"] == "rejected":
                    resolution_status = "danger"
                else:
                    resolution_status = "warning"

                direction_icon = "\u2191" if f["direction"] == "too_low" else "\u2193"

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
                    with c1:
                        st.markdown(f"**{f['author']}** {direction_icon} Score: {f['health_score_at_time']}")
                    with c2:
                        st.caption(f["reason"].replace("_", " "))
                    with c3:
                        st.markdown(
                            status_badge(f["resolution"], resolution_status),
                            unsafe_allow_html=True,
                        )
                    with c4:
                        if f.get("free_text"):
                            st.caption(f["free_text"][:120])

                    # Resolution buttons for pending items
                    if f["resolution"] == "pending":
                        rc1, rc2, rc3 = st.columns([2, 1, 1])
                        with rc1:
                            notes = st.text_input(
                                "Resolution notes",
                                key=f"resolve_notes_{f['id']}",
                                placeholder="Optional notes...",
                                label_visibility="collapsed",
                            )
                        with rc2:
                            if st.button("Accept", key=f"accept_{f['id']}", type="primary"):
                                resolve_feedback(f["id"], "accepted", notes, "VP")
                                st.session_state[f"resolved_{f['id']}"] = "accepted"
                                st.rerun()
                        with rc3:
                            if st.button("Reject", key=f"reject_{f['id']}"):
                                resolve_feedback(f["id"], "rejected", notes, "VP")
                                st.session_state[f"resolved_{f['id']}"] = "rejected"
                                st.rerun()
