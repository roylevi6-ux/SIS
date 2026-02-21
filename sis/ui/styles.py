"""SIS Global CSS — injected once via inject_global_css() in app.py."""

import streamlit as st

from sis.ui.theme import Colors, Radius, Spacing, Typography


def inject_global_css() -> None:
    """Inject global CSS overrides. Call once at top of main()."""
    st.markdown(
        f"""<style>
/* ── Dark sidebar ── */
section[data-testid="stSidebar"] {{
    background-color: {Colors.SIDEBAR_BG};
    color: {Colors.SIDEBAR_TEXT_BRIGHT};
}}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio label {{
    color: {Colors.SIDEBAR_TEXT} !important;
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] {{
    color: #fff !important;
    font-weight: 600;
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"]::before {{
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: {Colors.PRIMARY};
    border-radius: 0 2px 2px 0;
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {{
    position: relative;
}}

/* ── Subtle hr override ── */
hr {{
    border: none;
    border-top: 1px solid {Colors.BORDER};
    margin: {Spacing.LG}px 0;
}}

/* ── Metric card ── */
.sis-metric-card {{
    background: {Colors.BG_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radius.LG}px;
    padding: {Spacing.LG}px;
    text-align: center;
}}
.sis-metric-card .label {{
    font-size: {Typography.CAPTION}px;
    color: {Colors.TEXT_MUTED};
    margin-bottom: {Spacing.XS}px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.sis-metric-card .value {{
    font-size: {Typography.H2}px;
    font-weight: {Typography.BOLD};
    color: {Colors.TEXT_PRIMARY};
}}

/* ── Status badges ── */
.sis-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: {Radius.SM}px;
    font-size: {Typography.CAPTION}px;
    font-weight: {Typography.SEMIBOLD};
    line-height: 1.5;
}}
.sis-badge-success {{
    background: {Colors.with_alpha(Colors.SUCCESS)};
    color: {Colors.BADGE_SUCCESS};
}}
.sis-badge-warning {{
    background: {Colors.with_alpha(Colors.WARNING)};
    color: {Colors.BADGE_WARNING};
}}
.sis-badge-danger {{
    background: {Colors.with_alpha(Colors.DANGER)};
    color: {Colors.BADGE_DANGER};
}}
.sis-badge-info {{
    background: {Colors.with_alpha(Colors.INFO)};
    color: {Colors.BADGE_INFO};
}}
.sis-badge-neutral {{
    background: {Colors.with_alpha(Colors.NEUTRAL)};
    color: {Colors.BADGE_NEUTRAL};
}}
.sis-badge-accent {{
    background: {Colors.with_alpha(Colors.ACCENT)};
    color: {Colors.BADGE_ACCENT};
}}
.sis-badge-primary {{
    background: {Colors.with_alpha(Colors.PRIMARY)};
    color: {Colors.BADGE_PRIMARY};
}}

/* ── Large health score display ── */
.sis-score-lg {{
    text-align: center;
    padding: {Spacing.LG}px;
    border-radius: {Radius.XL}px;
}}
.sis-score-lg .score-value {{
    font-size: 48px;
    font-weight: {Typography.BOLD};
}}
.sis-score-lg .score-label {{
    font-weight: {Typography.SEMIBOLD};
    margin-top: {Spacing.XS}px;
}}

/* ── Empty state ── */
.sis-empty-state {{
    text-align: center;
    padding: {Spacing.XXL}px {Spacing.LG}px;
    color: {Colors.TEXT_MUTED};
}}
.sis-empty-state .icon {{
    font-size: 36px;
    margin-bottom: {Spacing.SM}px;
}}
.sis-empty-state .message {{
    font-size: {Typography.BODY}px;
    margin-bottom: {Spacing.SM}px;
}}
.sis-empty-state .hint {{
    font-size: {Typography.CAPTION}px;
    color: {Colors.NEUTRAL};
}}

/* ── Evidence quote blocks ── */
.sis-evidence {{
    border-left: 3px solid {Colors.ACCENT};
    padding: {Spacing.MD}px {Spacing.LG}px;
    margin: {Spacing.XS}px 0;
    background: {Colors.with_alpha(Colors.ACCENT, "10")};
    border-radius: 0 {Radius.SM}px {Radius.SM}px 0;
}}
.sis-evidence .quote {{
    font-style: italic;
    color: {Colors.TEXT_PRIMARY};
}}
.sis-evidence .attribution {{
    color: {Colors.TEXT_MUTED};
    font-size: {Typography.CAPTION}px;
    margin-top: {Spacing.XS}px;
}}

/* ── Action items ── */
.sis-action-item {{
    padding: {Spacing.SM}px {Spacing.LG}px;
    margin: {Spacing.XS}px 0;
    border-radius: 0 {Radius.SM}px {Radius.SM}px 0;
}}
.sis-action-item-p0 {{
    border-left: 3px solid {Colors.DANGER};
    background: {Colors.with_alpha(Colors.DANGER, "08")};
}}
.sis-action-item-p1 {{
    border-left: 3px solid {Colors.WARNING};
    background: {Colors.with_alpha(Colors.WARNING, "08")};
}}
.sis-action-item-p2 {{
    border-left: 3px solid {Colors.INFO};
    background: {Colors.with_alpha(Colors.INFO, "08")};
}}

/* ── Section divider ── */
.sis-section-divider {{
    border: none;
    border-top: 1px solid {Colors.BORDER};
    margin: {Spacing.LG}px 0;
}}

/* ── Minimum font size fix ── */
small, .small-text {{
    font-size: {Typography.CAPTION}px !important;
}}

/* ── Sidebar section headers ── */
.sidebar-section-header {{
    font-size: {Typography.CAPTION}px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: {Colors.SIDEBAR_TEXT_MUTED};
    margin: 16px 0 4px 0;
    font-weight: 600;
}}

/* ── Responsive column hiding ── */
@media (max-width: 768px) {{
    [data-testid="column"]:nth-child(n+4) {{
        display: none;
    }}
}}

/* ── Focus-visible outlines ── */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[role="radio"]:focus-visible {{
    outline: 2px solid {Colors.PRIMARY};
    outline-offset: 2px;
}}
</style>""",
        unsafe_allow_html=True,
    )
