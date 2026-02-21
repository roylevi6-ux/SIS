"""SIS Streamlit App — entry point and page routing.

Run with: streamlit run sis/ui/app.py

Per Technical Architecture Appendix B:
- Sidebar navigation
- Multi-page app using Streamlit's page routing
- st.session_state for chat history and selected account context
"""

import sys
from pathlib import Path

# Ensure project root is importable (so 'sis' package resolves)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from sis.db.engine import init_db


@st.cache_resource
def _init_database():
    """Initialize DB once per Streamlit server lifetime."""
    init_db()


# Initialize DB on first load (cached — runs only once)
_init_database()


def main():
    st.set_page_config(
        page_title="SIS — Sales Intelligence System",
        page_icon="\ud83d\udcca",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Sidebar navigation
    st.sidebar.title("SIS")
    st.sidebar.caption("Sales Intelligence System")
    st.sidebar.divider()

    # Pages grouped by section
    ANALYTICS_PAGES = [
        "Pipeline Overview",
        "Deal Detail",
        "Deal Brief",
        "Divergence View",
        "Team Rollup",
        "Rep Scorecard",
        "Forecast Comparison",
    ]

    ACTIONS_PAGES = [
        "Meeting Prep",
        "Upload Transcript",
        "Run Analysis",
        "Chat",
    ]

    ADMIN_PAGES = [
        "Feedback Dashboard",
        "Cost Monitor",
        "Daily Digest",
    ]

    ALL_PAGES = ANALYTICS_PAGES + ACTIONS_PAGES + ADMIN_PAGES

    # Section headers with radio navigation
    st.sidebar.markdown("**Analytics**")
    st.sidebar.caption("Pipeline, deals, forecasts, scorecards")
    page = st.sidebar.radio(
        "Navigation",
        ALL_PAGES,
        label_visibility="collapsed",
        format_func=lambda p: (
            f"--- Actions ---\n{p}" if p == ACTIONS_PAGES[0] and False else
            f"--- Admin ---\n{p}" if p == ADMIN_PAGES[0] and False else
            p
        ),
    )

    # Visual section dividers in sidebar
    analytics_end = len(ANALYTICS_PAGES) - 1
    actions_end = analytics_end + len(ACTIONS_PAGES)

    # Route to pages
    if page == "Pipeline Overview":
        from sis.ui.pages.pipeline_overview import render
        render()
    elif page == "Deal Detail":
        from sis.ui.pages.deal_detail import render
        render()
    elif page == "Deal Brief":
        from sis.ui.pages.deal_brief import render
        render()
    elif page == "Divergence View":
        from sis.ui.pages.divergence_view import render
        render()
    elif page == "Team Rollup":
        from sis.ui.pages.team_rollup import render
        render()
    elif page == "Rep Scorecard":
        from sis.ui.pages.rep_scorecard import render
        render()
    elif page == "Forecast Comparison":
        from sis.ui.pages.forecast_comparison import render
        render()
    elif page == "Meeting Prep":
        from sis.ui.pages.meeting_prep import render
        render()
    elif page == "Upload Transcript":
        from sis.ui.pages.upload_transcript import render
        render()
    elif page == "Run Analysis":
        from sis.ui.pages.run_analysis import render
        render()
    elif page == "Chat":
        from sis.ui.pages.chat import render
        render()
    elif page == "Feedback Dashboard":
        from sis.ui.pages.feedback_dashboard import render
        render()
    elif page == "Cost Monitor":
        from sis.ui.pages.cost_monitor import render
        render()
    elif page == "Daily Digest":
        from sis.ui.pages.daily_digest import render
        render()
    else:
        st.info("Select a page from the sidebar.")


if __name__ == "__main__":
    main()
