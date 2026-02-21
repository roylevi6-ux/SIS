"""Feedback Dashboard — aggregated feedback view for VP per PRD P0-17."""

import streamlit as st

from sis.services.feedback_service import list_feedback


def render():
    st.title("Feedback Dashboard")
    st.caption("All TL score feedback across deals")

    feedback = list_feedback()

    if not feedback:
        st.info("No feedback submitted yet.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Feedback", len(feedback))
    with col2:
        too_high = sum(1 for f in feedback if f["direction"] == "too_high")
        st.metric("Score Too High", too_high)
    with col3:
        too_low = sum(1 for f in feedback if f["direction"] == "too_low")
        st.metric("Score Too Low", too_low)
    with col4:
        pending = sum(1 for f in feedback if f["resolution"] == "pending")
        st.metric("Pending Resolution", pending)

    st.divider()

    # Reason breakdown
    st.subheader("Feedback by Reason")
    reasons = {}
    for f in feedback:
        r = f["reason"]
        reasons[r] = reasons.get(r, 0) + 1

    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        st.markdown(f"- **{reason}**: {count} submissions")

    st.divider()

    # Individual feedback items
    st.subheader("All Feedback")
    for f in feedback:
        status_color = "#22c55e" if f["resolution"] == "accepted" else "#ef4444" if f["resolution"] == "rejected" else "#f59e0b"
        direction_icon = "↑" if f["direction"] == "too_low" else "↓"

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
            with c1:
                st.markdown(f"**{f['author']}** {direction_icon} Score at time: {f['health_score_at_time']}")
            with c2:
                st.caption(f["reason"])
            with c3:
                st.markdown(
                    f'<span style="color:{status_color}">{f["resolution"]}</span>',
                    unsafe_allow_html=True,
                )
            with c4:
                if f.get("free_text"):
                    st.caption(f["free_text"][:100])
