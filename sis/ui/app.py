"""SIS Streamlit App — entry point and page routing.

Run with: streamlit run sis/ui/app.py

Uses st.navigation() (Streamlit 1.36+) for explicit page routing.
This disables Streamlit's auto-detection of the pages/ directory
and gives us grouped sidebar navigation with proper render() calls.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Ensure project root is importable (so 'sis' package resolves)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from sis.db.engine import init_db
from sis.services.usage_tracking_service import track_event
from sis.ui.styles import inject_global_css
from sis.ui.theme import Colors


@st.cache_resource
def _init_database():
    """Initialize DB once per Streamlit server lifetime."""
    init_db()


# Initialize DB on first load (cached — runs only once)
_init_database()

# ── Page definitions ──────────────────────────────────────────────────
# Each entry: (display_name, module_name under sis.ui.pages)

ANALYTICS_PAGES = [
    ("Pipeline Overview", "pipeline_overview"),
    ("Deal Detail", "deal_detail"),
    ("Deal Brief", "deal_brief"),
    ("Divergence View", "divergence_view"),
    ("Team Rollup", "team_rollup"),
    ("Rep Scorecard", "rep_scorecard"),
    ("Trend Analysis", "trend_analysis"),
    ("Forecast Comparison", "forecast_comparison"),
]

ACTIONS_PAGES = [
    ("Meeting Prep", "meeting_prep"),
    ("Import & Analyze", "upload_transcript"),
    ("Chat", "chat"),
]

ADMIN_PAGES = [
    ("Feedback Dashboard", "feedback_dashboard"),
    ("Cost Monitor", "cost_monitor"),
    ("Activity Log", "activity_log"),
    ("Daily Digest", "daily_digest"),
    ("Prompt Versions", "prompt_versions"),
    ("Calibration", "calibration"),
    ("Golden Tests", "golden_tests"),
    ("Usage Dashboard", "usage_dashboard"),
    ("Retrospective Seeding", "retrospective_seeding"),
]


def _make_page_callable(display_name: str, module_name: str):
    """Create a callable that imports and renders a page module."""
    def _render_page():
        track_event("page_view", page_name=display_name)
        mod = importlib.import_module(f"sis.ui.pages.{module_name}")
        mod.render()
    return _render_page


def _build_st_pages(page_defs: list[tuple[str, str]]) -> list:
    """Build list of st.Page objects from (display_name, module_name) tuples."""
    return [
        st.Page(_make_page_callable(name, mod), title=name, url_path=mod)
        for name, mod in page_defs
    ]


def main():
    st.set_page_config(
        page_title="SIS — Sales Intelligence System",
        page_icon="\U0001f4ca",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject global design-system CSS
    inject_global_css()

    # ── Sidebar branding ───────────────────────────────────────────────
    st.sidebar.markdown(
        f'<div style="padding:8px 0 4px 0">'
        f'<span style="color:{Colors.PRIMARY};font-size:24px;font-weight:800;'
        f'letter-spacing:-0.5px">SIS</span>'
        f'<br><span style="color:{Colors.TEXT_SUBTLE};font-size:12px">Sales Intelligence System</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<hr class="sis-section-divider">', unsafe_allow_html=True)

    # ── Navigation (disables pages/ auto-detection) ────────────────────
    pg = st.navigation({
        "Analytics": _build_st_pages(ANALYTICS_PAGES),
        "Actions": _build_st_pages(ACTIONS_PAGES),
        "Admin": _build_st_pages(ADMIN_PAGES),
    })

    pg.run()


if __name__ == "__main__":
    main()
