"""SIS Global CSS — injected once via inject_global_css() in app.py.

Modern sales intelligence dashboard styling.
"""

import streamlit as st

from sis.ui.theme import Colors, Radius, Shadows, Spacing, Typography


def inject_global_css() -> None:
    """Inject global CSS overrides. Call once at top of main()."""
    st.markdown(
        f"""<style>
/* ══════════════════════════════════════════════════════════════════════
   DARK SIDEBAR
   ══════════════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {{
    background: {Colors.GRADIENT_DARK};
    color: {Colors.SIDEBAR_TEXT_BRIGHT};
    border-right: 1px solid rgba(255,255,255,0.06);
}}
/* All sidebar text */
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p {{
    color: {Colors.SIDEBAR_TEXT} !important;
}}
/* Navigation links (st.navigation) */
section[data-testid="stSidebar"] a {{
    color: {Colors.SIDEBAR_TEXT} !important;
    text-decoration: none !important;
    transition: all 0.15s ease;
    border-radius: {Radius.MD}px;
}}
section[data-testid="stSidebar"] a:hover {{
    color: #fff !important;
    background: {Colors.SIDEBAR_BG_HOVER} !important;
}}
/* Active nav link */
section[data-testid="stSidebar"] a[aria-current="page"],
section[data-testid="stSidebar"] li[data-active="true"] a,
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
    color: #fff !important;
    font-weight: {Typography.SEMIBOLD};
    background: {Colors.SIDEBAR_ACTIVE_BG} !important;
    border-left: 3px solid {Colors.PRIMARY_LIGHT} !important;
}}
/* Nav section headers */
section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"],
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {Colors.SIDEBAR_TEXT_MUTED} !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 1.8px !important;
    font-weight: {Typography.SEMIBOLD} !important;
    margin-top: {Spacing.XL}px !important;
    margin-bottom: {Spacing.SM}px !important;
}}
/* Sidebar select / input overrides */
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {{
    color: {Colors.SIDEBAR_TEXT} !important;
}}

/* ══════════════════════════════════════════════════════════════════════
   MAIN CONTENT AREA
   ══════════════════════════════════════════════════════════════════════ */
.main .block-container {{
    padding-top: {Spacing.XL}px;
    max-width: 1200px;
}}

/* ── Subtle hr override ── */
hr {{
    border: none;
    border-top: 1px solid {Colors.BORDER_LIGHT};
    margin: {Spacing.LG}px 0;
}}

/* ══════════════════════════════════════════════════════════════════════
   PAGE HEADER (gradient banner)
   ══════════════════════════════════════════════════════════════════════ */
.sis-page-header {{
    background: {Colors.GRADIENT_DARK};
    border-radius: {Radius.XL}px;
    padding: {Spacing.XL}px {Spacing.XXL}px;
    margin-bottom: {Spacing.XL}px;
    box-shadow: {Shadows.MD};
}}
.sis-page-header .title {{
    font-size: {Typography.H1}px;
    font-weight: {Typography.EXTRABOLD};
    color: #fff;
    margin: 0;
    letter-spacing: -0.5px;
}}
.sis-page-header .subtitle {{
    font-size: {Typography.BODY}px;
    color: {Colors.SIDEBAR_TEXT};
    margin-top: {Spacing.XS}px;
}}

/* ══════════════════════════════════════════════════════════════════════
   METRIC CARDS (elevated with shadow + accent top border)
   ══════════════════════════════════════════════════════════════════════ */
.sis-metric-card {{
    background: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-top: 3px solid {Colors.PRIMARY};
    border-radius: {Radius.XL}px;
    padding: {Spacing.XL}px {Spacing.LG}px;
    text-align: center;
    box-shadow: {Shadows.SM};
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}}
.sis-metric-card:hover {{
    box-shadow: {Shadows.MD};
    transform: translateY(-1px);
}}
.sis-metric-card .label {{
    font-size: 11px;
    color: {Colors.TEXT_MUTED};
    margin-bottom: {Spacing.SM}px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: {Typography.MEDIUM};
}}
.sis-metric-card .value {{
    font-size: {Typography.H1}px;
    font-weight: {Typography.EXTRABOLD};
    color: {Colors.TEXT_PRIMARY};
    letter-spacing: -0.5px;
}}
/* Color variants for metric cards */
.sis-metric-card-success {{ border-top-color: {Colors.SUCCESS}; }}
.sis-metric-card-warning {{ border-top-color: {Colors.WARNING}; }}
.sis-metric-card-danger  {{ border-top-color: {Colors.DANGER}; }}
.sis-metric-card-info    {{ border-top-color: {Colors.INFO}; }}

/* ══════════════════════════════════════════════════════════════════════
   STATUS BADGES (pill-shaped, vivid backgrounds)
   ══════════════════════════════════════════════════════════════════════ */
.sis-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: {Radius.FULL}px;
    font-size: 11px;
    font-weight: {Typography.SEMIBOLD};
    line-height: 1.5;
    letter-spacing: 0.3px;
}}
.sis-badge-success {{
    background: {Colors.BADGE_BG_SUCCESS};
    color: {Colors.BADGE_SUCCESS};
}}
.sis-badge-warning {{
    background: {Colors.BADGE_BG_WARNING};
    color: {Colors.BADGE_WARNING};
}}
.sis-badge-danger {{
    background: {Colors.BADGE_BG_DANGER};
    color: {Colors.BADGE_DANGER};
}}
.sis-badge-info {{
    background: {Colors.BADGE_BG_INFO};
    color: {Colors.BADGE_INFO};
}}
.sis-badge-neutral {{
    background: {Colors.BADGE_BG_NEUTRAL};
    color: {Colors.BADGE_NEUTRAL};
}}
.sis-badge-accent {{
    background: {Colors.BADGE_BG_ACCENT};
    color: {Colors.BADGE_ACCENT};
}}
.sis-badge-primary {{
    background: {Colors.BADGE_BG_PRIMARY};
    color: {Colors.BADGE_PRIMARY};
}}

/* ══════════════════════════════════════════════════════════════════════
   HEALTH SCORE — large display
   ══════════════════════════════════════════════════════════════════════ */
.sis-score-lg {{
    text-align: center;
    padding: {Spacing.XL}px;
    border-radius: {Radius.XXL}px;
    box-shadow: {Shadows.SM};
}}
.sis-score-lg .score-value {{
    font-size: 56px;
    font-weight: {Typography.EXTRABOLD};
    letter-spacing: -2px;
}}
.sis-score-lg .score-label {{
    font-weight: {Typography.SEMIBOLD};
    font-size: {Typography.BODY}px;
    margin-top: {Spacing.SM}px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

/* ══════════════════════════════════════════════════════════════════════
   EMPTY STATE
   ══════════════════════════════════════════════════════════════════════ */
.sis-empty-state {{
    text-align: center;
    padding: {Spacing.XXXL}px {Spacing.XL}px;
    color: {Colors.TEXT_MUTED};
    background: {Colors.BG_SECONDARY};
    border: 2px dashed {Colors.BORDER};
    border-radius: {Radius.XL}px;
    margin: {Spacing.LG}px 0;
}}
.sis-empty-state .icon {{
    font-size: 48px;
    margin-bottom: {Spacing.MD}px;
    opacity: 0.7;
}}
.sis-empty-state .message {{
    font-size: {Typography.BODY_LG}px;
    font-weight: {Typography.MEDIUM};
    margin-bottom: {Spacing.SM}px;
    color: {Colors.TEXT_SECONDARY};
}}
.sis-empty-state .hint {{
    font-size: {Typography.BODY}px;
    color: {Colors.TEXT_MUTED};
}}

/* ══════════════════════════════════════════════════════════════════════
   EVIDENCE QUOTE BLOCKS
   ══════════════════════════════════════════════════════════════════════ */
.sis-evidence {{
    border-left: 4px solid {Colors.ACCENT};
    padding: {Spacing.LG}px {Spacing.XL}px;
    margin: {Spacing.SM}px 0;
    background: {Colors.BADGE_BG_ACCENT};
    border-radius: 0 {Radius.LG}px {Radius.LG}px 0;
    box-shadow: {Shadows.SM};
}}
.sis-evidence .quote {{
    font-style: italic;
    color: {Colors.TEXT_PRIMARY};
    font-size: {Typography.BODY}px;
    line-height: 1.6;
}}
.sis-evidence .attribution {{
    color: {Colors.TEXT_MUTED};
    font-size: {Typography.CAPTION}px;
    margin-top: {Spacing.SM}px;
    font-weight: {Typography.MEDIUM};
}}

/* ══════════════════════════════════════════════════════════════════════
   ACTION ITEMS (colored left border + tinted bg)
   ══════════════════════════════════════════════════════════════════════ */
.sis-action-item {{
    padding: {Spacing.MD}px {Spacing.XL}px;
    margin: {Spacing.SM}px 0;
    border-radius: 0 {Radius.LG}px {Radius.LG}px 0;
    box-shadow: {Shadows.SM};
}}
.sis-action-item-p0 {{
    border-left: 4px solid {Colors.DANGER};
    background: {Colors.BADGE_BG_DANGER};
}}
.sis-action-item-p1 {{
    border-left: 4px solid {Colors.WARNING};
    background: {Colors.BADGE_BG_WARNING};
}}
.sis-action-item-p2 {{
    border-left: 4px solid {Colors.INFO};
    background: {Colors.BADGE_BG_INFO};
}}

/* ══════════════════════════════════════════════════════════════════════
   SECTION DIVIDER
   ══════════════════════════════════════════════════════════════════════ */
.sis-section-divider {{
    border: none;
    border-top: 1px solid {Colors.BORDER_LIGHT};
    margin: {Spacing.XL}px 0;
}}

/* ══════════════════════════════════════════════════════════════════════
   STREAMLIT COMPONENT OVERRIDES
   ══════════════════════════════════════════════════════════════════════ */

/* Buttons — primary teal */
.stButton > button[kind="primary"],
.stButton > button {{
    border-radius: {Radius.LG}px;
    font-weight: {Typography.SEMIBOLD};
    transition: all 0.15s ease;
    border: 1px solid {Colors.BORDER};
}}
.stButton > button:hover {{
    box-shadow: {Shadows.SM};
    transform: translateY(-1px);
}}

/* Containers with border (Streamlit cards) */
[data-testid="stExpander"] {{
    border: 1px solid {Colors.BORDER};
    border-radius: {Radius.XL}px;
    box-shadow: {Shadows.SM};
    overflow: hidden;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"][data-stale="false"]) {{
    border-radius: {Radius.XL}px;
    box-shadow: {Shadows.SM};
}}

/* Tabs — underline style */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 2px solid {Colors.BORDER_LIGHT};
}}
.stTabs [data-baseweb="tab"] {{
    padding: {Spacing.MD}px {Spacing.XL}px;
    font-weight: {Typography.MEDIUM};
    color: {Colors.TEXT_MUTED};
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {Colors.PRIMARY} !important;
    font-weight: {Typography.SEMIBOLD};
}}
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: {Colors.PRIMARY} !important;
}}

/* Metrics override */
[data-testid="stMetric"] {{
    background: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radius.XL}px;
    padding: {Spacing.LG}px;
    box-shadow: {Shadows.SM};
}}
[data-testid="stMetricLabel"] {{
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {Colors.TEXT_MUTED} !important;
}}
[data-testid="stMetricValue"] {{
    font-weight: {Typography.EXTRABOLD} !important;
    color: {Colors.TEXT_PRIMARY} !important;
}}

/* DataFrames */
[data-testid="stDataFrame"] {{
    border-radius: {Radius.XL}px;
    overflow: hidden;
    box-shadow: {Shadows.SM};
}}

/* Text input / select */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div {{
    border-radius: {Radius.LG}px !important;
}}

/* ══════════════════════════════════════════════════════════════════════
   RESPONSIVE
   ══════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {{
    [data-testid="column"]:nth-child(n+4) {{
        display: none;
    }}
    .sis-page-header {{
        padding: {Spacing.LG}px;
    }}
}}

/* Focus-visible outlines */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible {{
    outline: 2px solid {Colors.PRIMARY};
    outline-offset: 2px;
}}
</style>""",
        unsafe_allow_html=True,
    )
