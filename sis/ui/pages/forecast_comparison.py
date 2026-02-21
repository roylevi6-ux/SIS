"""Forecast Comparison — AI vs IC aggregate comparison per PRD P0-21.

Interactive Streamlit rendering of the forecast report with:
  - Summary metrics: Total MRR, AI Weighted, IC Weighted, Delta
  - Per-deal table with sortable columns
  - Per-team breakdown
  - Divergent deals highlighted
  - Export button
"""

from __future__ import annotations

import streamlit as st

from sis.services.forecast_data_service import load_forecast_data, get_team_names
from sis.services.export_service import export_forecast_report
from sis.ui.components.health_badge import render_forecast_badge
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, status_badge, score_badge,
    empty_state,
)
from sis.ui.theme import Colors

# Forecast category weights (same as export_service)
CATEGORY_WEIGHTS = {
    "Commit": 0.90,
    "Best Case": 0.70,
    "Pipeline": 0.40,
    "Upside": 0.25,
    "At Risk": 0.15,
    "No Decision Risk": 0.05,
}


def render():
    page_header(
        "Forecast Comparison",
        "AI aggregate vs IC aggregate: total weighted pipeline by team and org",
    )

    # Team filter
    teams = get_team_names()
    team_options = ["All Teams"] + sorted(teams)
    selected_team = st.selectbox("Team", team_options, key="forecast_team_filter")
    team_filter = None if selected_team == "All Teams" else selected_team

    rows = load_forecast_data(team_filter)

    if not rows:
        empty_state(
            "No scored deals found",
            "📊",
            "Run analysis first.",
        )
        return

    # --- Summary metrics ---
    total_mrr = sum(r["mrr"] for r in rows)
    ai_weighted = sum(r["mrr"] * CATEGORY_WEIGHTS.get(r["ai_forecast"], 0.25) for r in rows)
    ic_rows = [r for r in rows if r["ic_forecast"]]
    ic_weighted = sum(r["mrr"] * CATEGORY_WEIGHTS.get(r["ic_forecast"], 0.25) for r in ic_rows)
    delta = ai_weighted - ic_weighted
    divergent_count = sum(1 for r in rows if r["divergence"])

    metric_row([
        {"label": "Total Pipeline MRR", "value": f"${total_mrr:,.0f}"},
        {"label": "AI Weighted", "value": f"${ai_weighted:,.0f}"},
        {"label": "IC Weighted", "value": f"${ic_weighted:,.0f}"},
        {"label": "Delta (AI - IC)", "value": f"${delta:,.0f}"},
        {"label": "Divergent Deals", "value": divergent_count},
    ])

    section_divider()

    # --- Per-team breakdown ---
    teams_data: dict[str, list] = {}
    for r in rows:
        t = r["team_name"]
        if t not in teams_data:
            teams_data[t] = []
        teams_data[t].append(r)

    if len(teams_data) > 1:
        st.subheader("By Team")
        for t_name in sorted(teams_data.keys()):
            t_rows = teams_data[t_name]
            t_mrr = sum(r["mrr"] for r in t_rows)
            t_ai = sum(r["mrr"] * CATEGORY_WEIGHTS.get(r["ai_forecast"], 0.25) for r in t_rows)
            t_ic_rows = [r for r in t_rows if r["ic_forecast"]]
            t_ic = sum(r["mrr"] * CATEGORY_WEIGHTS.get(r["ic_forecast"], 0.25) for r in t_ic_rows)
            t_div = sum(1 for r in t_rows if r["divergence"])

            tc1, tc2, tc3, tc4, tc5 = st.columns(5)
            with tc1:
                st.markdown(f"**{t_name}** ({len(t_rows)} deals)")
            with tc2:
                st.caption(f"MRR: ${t_mrr:,.0f}")
            with tc3:
                st.caption(f"AI: ${t_ai:,.0f}")
            with tc4:
                st.caption(f"IC: ${t_ic:,.0f}")
            with tc5:
                if t_div:
                    st.caption(f"Divergent: {t_div}")
        section_divider()

    # --- Per-deal table ---
    st.subheader("Deal-Level Comparison")
    sorted_rows = sorted(rows, key=lambda x: -x["mrr"])

    for r in sorted_rows:
        with st.container(border=True):
            c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
            with c1:
                if st.button(r["account_name"], key=f"fc_{r['account_id']}"):
                    st.session_state["selected_account_id"] = r["account_id"]
                    st.rerun()
                st.caption(f"${r['mrr']:,.0f} | {r['ae_owner']} | {r['team_name']}")
            with c2:
                st.caption("AI Forecast")
                render_forecast_badge(r["ai_forecast"])
            with c3:
                st.caption("IC Forecast")
                if r["ic_forecast"]:
                    render_forecast_badge(r["ic_forecast"])
                else:
                    st.markdown("*Not set*")
            with c4:
                st.caption("Health")
                score = r["health_score"]
                st.markdown(
                    score_badge(score) if score is not None else "--",
                    unsafe_allow_html=True,
                )
            with c5:
                st.caption("Momentum")
                st.markdown(r["momentum"] or "--")
            with c6:
                if r["divergence"]:
                    st.markdown(
                        status_badge("DIVERGENT", "danger"),
                        unsafe_allow_html=True,
                    )

    # --- Export button ---
    section_divider()
    report_md = export_forecast_report(team=team_filter)
    st.download_button(
        label="Export Forecast Report (Markdown)",
        data=report_md,
        file_name="forecast_comparison.md",
        mime="text/markdown",
        key="forecast_export",
    )
