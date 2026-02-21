"""Calibration — feedback pattern analysis and calibration change logging per PRD P0-18, Sec 7.9.

Displays feedback patterns, current calibration config, calibration log form,
and calibration history.
"""

from __future__ import annotations

import streamlit as st

from sis.services.calibration_service import (
    get_feedback_patterns,
    get_current_calibration,
    create_calibration_log,
    list_calibration_history,
)
from sis.ui.components.layout import page_header, section_divider, metric_row, empty_state


def render():
    page_header("Calibration", "Feedback pattern analysis and calibration change logging")

    # Show toast from previous rerun
    if st.session_state.get("_cal_toast"):
        st.toast(st.session_state.pop("_cal_toast"))

    # --- Feedback Patterns ---
    st.subheader("Feedback Patterns")
    patterns = get_feedback_patterns()

    if patterns["total_feedback"] == 0:
        empty_state(
            "No feedback data yet",
            "\U0001f4cb",
            "Submit score feedback to see patterns here.",
        )
    else:
        too_high = patterns["by_direction"].get("too_high", 0)
        too_low = patterns["by_direction"].get("too_low", 0)
        skew = "Too High" if too_high > too_low else "Too Low" if too_low > too_high else "Balanced"
        top_reason = patterns["top_flagged_reasons"][0] if patterns["top_flagged_reasons"] else ("N/A", 0)

        metric_row([
            {"label": "Total Feedback", "value": patterns["total_feedback"]},
            {"label": "Direction Skew", "value": skew},
            {"label": "Top Flagged Reason", "value": top_reason[0].replace("_", " ").title()},
        ])

        # Top flagged reasons
        st.markdown("**Feedback by Reason**")
        if patterns["by_reason"]:
            reason_data = [
                {"Reason": r.replace("_", " ").title(), "Count": c}
                for r, c in sorted(patterns["by_reason"].items(), key=lambda x: -x[1])
            ]
            st.dataframe(reason_data, use_container_width=True, hide_index=True)

        # Agent-level skew
        if patterns["direction_per_agent"]:
            st.markdown("**Direction Skew by Agent**")
            agent_skew = []
            for agent_id, dirs in sorted(patterns["direction_per_agent"].items()):
                agent_skew.append({
                    "Agent": agent_id,
                    "Too High": dirs.get("too_high", 0),
                    "Too Low": dirs.get("too_low", 0),
                })
            st.dataframe(agent_skew, use_container_width=True, hide_index=True)

    section_divider()

    # --- Current Calibration Config ---
    st.subheader("Current Calibration Config")
    config = get_current_calibration()
    if config:
        st.code(
            _format_config(config),
            language="yaml",
        )
    else:
        empty_state(
            "No calibration config file found",
            "\u2699\ufe0f",
        )

    section_divider()

    # --- Log Calibration Change ---
    st.subheader("Log Calibration Change")
    with st.expander("New Calibration Log Entry"):
        cal_version = st.text_input("Config version", placeholder="e.g. v1.1")
        cal_prev = st.text_input("Previous version", placeholder="e.g. v1.0")
        cal_changes = st.text_area(
            "Changes description",
            placeholder="Describe what was changed and why...",
            height=150,
        )
        cal_reviewed = st.number_input("Feedback items reviewed", min_value=0, value=0)
        cal_approved = st.text_input("Approved by", placeholder="e.g. VP Sales")

        if st.button("Log Change", type="primary", disabled=not cal_version):
            try:
                create_calibration_log(
                    config_version=cal_version,
                    previous_version=cal_prev or None,
                    changes=cal_changes or None,
                    feedback_items_reviewed=cal_reviewed,
                    approved_by=cal_approved or None,
                )
                st.session_state["_cal_toast"] = f"Logged calibration change: {cal_version}"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    section_divider()

    # --- Calibration History ---
    st.subheader("Calibration History")
    history = list_calibration_history()
    if history:
        for h in history:
            with st.expander(f"v{h['config_version']} — {h['calibration_date'][:19]}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Previous:** {h['config_previous_version'] or 'N/A'}")
                with c2:
                    st.markdown(f"**Reviewed:** {h['feedback_items_reviewed'] or 0} items")
                with c3:
                    st.markdown(f"**Approved by:** {h['approved_by'] or 'N/A'}")
                if h.get("config_changes"):
                    st.markdown("**Changes:**")
                    st.text(h["config_changes"])
    else:
        empty_state(
            "No calibration history logged yet",
            "\U0001f4c6",
        )


def _format_config(config: dict) -> str:
    """Format config dict as readable YAML string."""
    import yaml
    return yaml.dump(config, default_flow_style=False, sort_keys=False)
