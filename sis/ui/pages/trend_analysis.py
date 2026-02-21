"""Trend Analysis — pipeline health change over time per PRD P1-3.

Shows portfolio summary, team trends, and per-deal health trajectories
with line charts for deals with multiple data points.
"""

import html

import pandas as pd
import streamlit as st

from sis.services.trend_service import (
    get_deal_trends,
    get_team_trends,
    get_portfolio_summary,
)
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, direction_badge, empty_state,
)
from sis.ui.theme import Colors, Typography


def _delta_display(delta: int | float) -> str:
    if delta > 0:
        return f'<span style="color:{Colors.SUCCESS};font-weight:bold">+{delta}</span>'
    elif delta < 0:
        return f'<span style="color:{Colors.DANGER};font-weight:bold">{delta}</span>'
    return f'<span style="color:{Colors.NEUTRAL}">0</span>'


def render():
    page_header("Trend Analysis", "Pipeline health change over time — per-deal and per-team")

    # Time range selector
    week_options = {
        "2 weeks": 2,
        "4 weeks": 4,
        "8 weeks": 8,
        "12 weeks": 12,
    }
    selected_label = st.selectbox(
        "Time Range",
        list(week_options.keys()),
        index=1,
        key="trend_weeks",
    )
    weeks = week_options[selected_label]

    # Load data (single DB query, derived views reuse it)
    deal_trends = get_deal_trends(weeks=weeks)
    portfolio = get_portfolio_summary(weeks=weeks, deal_trends=deal_trends)
    team_trends = get_team_trends(weeks=weeks, deal_trends=deal_trends)

    # --- Portfolio Summary ---
    st.subheader("Portfolio Summary")
    if portfolio["total_deals"] == 0:
        empty_state(
            "No assessment data in the selected time range",
            "📈",
            "Run analysis on accounts first.",
        )
        return

    metric_row([
        {"label": "Total Deals", "value": portfolio["total_deals"]},
        {"label": "Improving", "value": portfolio["improving"]},
        {"label": "Stable", "value": portfolio["stable"]},
        {"label": "Declining", "value": portfolio["declining"]},
    ])

    # Portfolio direction badge + avg delta on a separate row
    dir_col, delta_col = st.columns(2)
    with dir_col:
        st.markdown(
            f'<div style="text-align:center;padding:8px">'
            f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">Trend</div>'
            f'<div style="margin-top:4px">{direction_badge(portfolio["portfolio_direction"])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with delta_col:
        st.metric("Avg Delta", f"{portfolio['avg_delta']:+.1f}")

    # Biggest movers
    mover_cols = st.columns(2)
    with mover_cols[0]:
        imp = portfolio.get("biggest_improver")
        if imp:
            st.markdown(
                f'**Biggest Improver:** {html.escape(imp["account_name"])} '
                f'(+{imp["delta"]}, now {imp["last_score"]})',
            )
        else:
            st.caption("No improving deals")
    with mover_cols[1]:
        dec = portfolio.get("biggest_decliner")
        if dec:
            st.markdown(
                f'**Biggest Decliner:** {html.escape(dec["account_name"])} '
                f'({dec["delta"]}, now {dec["last_score"]})',
            )
        else:
            st.caption("No declining deals")

    section_divider()

    # --- Team Trends ---
    st.subheader("Team Trends")
    if not team_trends:
        empty_state("No team data available", "👥")
    else:
        for team in team_trends:
            with st.container(border=True):
                h_col, badge_col = st.columns([3, 1])
                with h_col:
                    st.markdown(f"#### {html.escape(team['team_name'])}")
                with badge_col:
                    st.markdown(direction_badge(team["team_direction"]), unsafe_allow_html=True)

                metric_row([
                    {"label": "Deals", "value": team["deal_count"]},
                    {"label": "Avg Health", "value": f"{team['avg_health']:.0f}"},
                    {"label": "Avg Delta", "value": f"{team['avg_delta']:+.1f}"},
                    {"label": "Improving", "value": team["improving_count"]},
                    {"label": "Declining", "value": team["declining_count"]},
                ])

    section_divider()

    # --- Per-Deal Trajectories ---
    st.subheader("Per-Deal Trajectories")

    # Filters
    filter_cols = st.columns(2)
    with filter_cols[0]:
        direction_options = ["All", "Improving", "Stable", "Declining"]
        sel_direction = st.selectbox("Direction", direction_options, key="trend_direction_filter")
    with filter_cols[1]:
        teams = sorted(set(d["team_name"] for d in deal_trends))
        team_options = ["All Teams"] + teams
        sel_team = st.selectbox("Team", team_options, key="trend_team_filter")

    filtered = deal_trends
    if sel_direction != "All":
        filtered = [d for d in filtered if d["trend_direction"] == sel_direction]
    if sel_team != "All Teams":
        filtered = [d for d in filtered if d["team_name"] == sel_team]

    if not filtered:
        empty_state("No deals match the selected filters", "🔍")
    else:
        for deal in filtered:
            with st.container(border=True):
                d_col1, d_col2, d_col3 = st.columns([3, 1, 1])
                with d_col1:
                    if st.button(
                        deal["account_name"],
                        key=f"trend_deal_{deal['account_id']}",
                    ):
                        st.session_state["selected_account_id"] = deal["account_id"]
                        st.rerun()
                    st.caption(
                        f"{html.escape(deal['team_name'])} | {html.escape(deal['ae_owner'])}"
                    )
                with d_col2:
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">Score</div>'
                        f'<div style="font-size:22px;font-weight:bold">{deal["last_score"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with d_col3:
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div style="font-size:{Typography.CAPTION}px;color:{Colors.TEXT_MUTED}">Delta</div>'
                        f'<div style="font-size:22px">{_delta_display(deal["delta"])}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(direction_badge(deal["trend_direction"]), unsafe_allow_html=True)

                # Line chart for deals with 2+ data points
                points = deal["data_points"]
                if len(points) >= 2:
                    df = pd.DataFrame(points)
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.set_index("date")
                    st.line_chart(df["health_score"], height=150)
                else:
                    st.caption(f"Single data point: {points[0]['date']} — Health {points[0]['health_score']}")
