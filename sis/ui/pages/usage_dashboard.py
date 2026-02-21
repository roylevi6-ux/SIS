"""Usage Dashboard — CRO success criteria tracking per PRD Sec 12 Condition 1.

Displays the 6 CRO metrics with pass/fail indicators, event counts,
per-user activity breakdown, and per-page view counts.
"""

import streamlit as st

from sis.services.usage_tracking_service import get_usage_summary, get_cro_metrics
from sis.ui.components.layout import page_header, section_divider, empty_state


def render():
    page_header("Usage Dashboard", "CRO success criteria and platform adoption metrics")

    # --- CRO Scorecard ---
    st.subheader("CRO Success Criteria")
    metrics = get_cro_metrics()

    cols = st.columns(3)
    for i, m in enumerate(metrics):
        with cols[i % 3]:
            if m["passed"] is True:
                status = ":green[PASS]"
            elif m["passed"] is False:
                status = ":red[FAIL]"
            else:
                status = ":orange[N/A]"

            with st.container(border=True):
                st.markdown(f"**{m['metric']}** {status}")
                st.caption(m["description"])
                st.metric(
                    label="Actual vs Target",
                    value=m["actual"],
                    delta=f"Target: {m['target']}",
                    delta_color="off",
                )

    passed_count = sum(1 for m in metrics if m["passed"] is True)
    total_evaluable = sum(1 for m in metrics if m["passed"] is not None)
    section_divider()
    st.markdown(
        f"**Overall: {passed_count}/{total_evaluable} criteria met** "
        f"({len(metrics) - total_evaluable} not yet evaluable)"
    )

    section_divider()

    # --- Event Summary ---
    days = st.selectbox("Time range", [7, 14, 30, 60, 90], index=2)
    summary = get_usage_summary(days=days)

    st.subheader(f"Event Summary (Last {days} Days)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Events by Type**")
        if summary["by_type"]:
            for event_type, count in sorted(summary["by_type"].items(), key=lambda x: -x[1]):
                st.text(f"  {event_type}: {count}")
        else:
            empty_state(
                "No events recorded yet",
                "\U0001f4e1",
            )

    with col2:
        st.markdown("**Views by Page**")
        if summary["by_page"]:
            for page, count in sorted(summary["by_page"].items(), key=lambda x: -x[1]):
                st.text(f"  {page}: {count}")
        else:
            empty_state(
                "No page views recorded yet",
                "\U0001f4c4",
            )

    section_divider()

    # --- Per-User Activity ---
    st.subheader("Per-User Activity")
    if summary["by_user"]:
        user_data = [
            {"User": user, "Events": count}
            for user, count in sorted(summary["by_user"].items(), key=lambda x: -x[1])
        ]
        st.dataframe(user_data, use_container_width=True, hide_index=True)
    else:
        empty_state(
            "No user-attributed events yet",
            "\U0001f464",
            "Events are tracked anonymously by default.",
        )

    # --- Daily Trend ---
    st.subheader("Daily Event Trend")
    if summary["by_day"]:
        day_data = [
            {"Date": day, "Events": count}
            for day, count in sorted(summary["by_day"].items())
        ]
        st.bar_chart(
            data={d["Date"]: d["Events"] for d in day_data},
        )
    else:
        empty_state(
            "No events to display",
            "\U0001f4c8",
        )
