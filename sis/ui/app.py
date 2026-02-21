"""SIS Streamlit App — entry point and page routing.

Run with: streamlit run sis/ui/app.py

Per Technical Architecture Appendix B:
- Sidebar navigation
- Multi-page app using Streamlit's page routing
- st.session_state for chat history and selected account context
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

# ── Page registry ──────────────────────────────────────────────────────
# Maps display name → module path under sis.ui.pages

ANALYTICS_PAGES = [
    "Pipeline Overview",
    "Deal Detail",
    "Deal Brief",
    "Divergence View",
    "Team Rollup",
    "Rep Scorecard",
    "Trend Analysis",
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
    "Activity Log",
    "Daily Digest",
    "Prompt Versions",
    "Calibration",
    "Golden Tests",
    "Usage Dashboard",
    "Retrospective Seeding",
]

PAGE_REGISTRY: dict[str, str] = {}
for name in ANALYTICS_PAGES + ACTIONS_PAGES + ADMIN_PAGES:
    module_name = name.lower().replace(" ", "_")
    PAGE_REGISTRY[name] = f"sis.ui.pages.{module_name}"


def _render_sidebar_section(
    label: str,
    pages: list[str],
    section_key: str,
) -> str | None:
    """Render a sidebar section with header and radio group.

    Returns the selected page name, or None if nothing selected in this section.
    """
    st.sidebar.markdown(
        f'<div class="sidebar-section-header">{label}</div>',
        unsafe_allow_html=True,
    )

    # Determine default index: 0 if this section owns the active page, else None
    active = st.session_state.get("active_section")
    default_idx = 0 if active == section_key else None

    # If this section is active and has a stored page, find its index
    if active == section_key:
        stored = st.session_state.get("active_page", pages[0])
        if stored in pages:
            default_idx = pages.index(stored)

    selected = st.sidebar.radio(
        label,
        pages,
        index=default_idx,
        key=f"nav_{section_key}",
        label_visibility="collapsed",
    )

    return selected


def main():
    st.set_page_config(
        page_title="SIS — Sales Intelligence System",
        page_icon="📊",
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

    # ── Initialize session state ───────────────────────────────────────
    if "active_section" not in st.session_state:
        st.session_state.active_section = "analytics"
    if "active_page" not in st.session_state:
        st.session_state.active_page = ANALYTICS_PAGES[0]

    # ── Grouped navigation radios ──────────────────────────────────────
    sections = [
        ("Analytics", ANALYTICS_PAGES, "analytics"),
        ("Actions", ACTIONS_PAGES, "actions"),
        ("Admin", ADMIN_PAGES, "admin"),
    ]

    page = None
    for label, pages, key in sections:
        selected = _render_sidebar_section(label, pages, key)
        # Detect if user clicked in this section
        if selected and selected != st.session_state.get(f"_prev_{key}"):
            st.session_state.active_section = key
            st.session_state.active_page = selected
            page = selected
        st.session_state[f"_prev_{key}"] = selected

    # Fallback: use stored active page
    if page is None:
        page = st.session_state.get("active_page", ANALYTICS_PAGES[0])

    # ── Track + route ──────────────────────────────────────────────────
    track_event("page_view", page_name=page)

    module_path = PAGE_REGISTRY.get(page)
    if module_path:
        mod = importlib.import_module(module_path)
        mod.render()
    else:
        st.info("Select a page from the sidebar.")


if __name__ == "__main__":
    main()
