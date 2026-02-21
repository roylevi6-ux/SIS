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
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Sidebar navigation
    st.sidebar.title("SIS")
    st.sidebar.caption("Sales Intelligence System")
    st.sidebar.divider()

    PAGES = [
        "Pipeline Overview",
        "Deal Detail",
        "Divergence View",
        "Team Rollup",
        "Upload Transcript",
        "Run Analysis",
        "Chat",
        "Feedback Dashboard",
        "Cost Monitor",
    ]

    # Section headers for visual grouping
    st.sidebar.markdown("**Analytics**")
    page = st.sidebar.radio(
        "Navigation",
        PAGES,
        label_visibility="collapsed",
    )

    # Route to pages
    if page == "Pipeline Overview":
        from sis.ui.pages.pipeline_overview import render
        render()
    elif page == "Deal Detail":
        from sis.ui.pages.deal_detail import render
        render()
    elif page == "Divergence View":
        from sis.ui.pages.divergence_view import render
        render()
    elif page == "Team Rollup":
        from sis.ui.pages.team_rollup import render
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
    else:
        st.info("Select a page from the sidebar.")


if __name__ == "__main__":
    main()
