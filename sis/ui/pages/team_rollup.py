"""Team Rollup — aggregate health metrics per team per PRD P0-12."""

from __future__ import annotations

import streamlit as st

from sis.services.dashboard_service import get_team_rollup
from sis.ui.components.layout import page_header, metric_row, empty_state


def render():
    page_header("Team Rollup")

    rollup = get_team_rollup()

    if not rollup:
        empty_state("No teams found.", "\U0001f465", "Add accounts with team assignments first.")
        return

    for team in rollup:
        with st.container(border=True):
            st.subheader(team["team_name"])

            avg = team.get("avg_health_score")
            metric_row([
                {"label": "Total Deals", "value": team["total_deals"]},
                {"label": "Avg Health", "value": f"{avg:.0f}" if avg else "--"},
                {"label": "Healthy", "value": team["healthy_count"]},
                {"label": "At Risk", "value": team["at_risk_count"]},
                {"label": "Critical", "value": team["critical_count"]},
            ])

            mrr = team.get("total_mrr", 0)
            metric_row([
                {"label": "Total MRR", "value": f"${mrr:,.0f}" if mrr else "--"},
                {"label": "Divergent", "value": team["divergent_count"]},
            ])
