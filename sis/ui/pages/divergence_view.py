"""Divergence View — AI vs IC forecast comparison per PRD P0-11."""

from __future__ import annotations

import streamlit as st

from sis.services.dashboard_service import get_divergence_report
from sis.ui.components.health_badge import render_forecast_badge
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, empty_state,
)


def render():
    page_header("Divergence View", "Deals where AI and IC forecasts differ, sorted by MRR impact")

    divergences = get_divergence_report()

    if not divergences:
        empty_state(
            "No divergences found.",
            "\u2705",
            "Either no IC forecasts have been entered, or AI and IC agree on all deals.",
        )
        return

    metric_row([
        {"label": "Divergent Deals", "value": len(divergences)},
    ])
    section_divider()

    for d in divergences:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
            with c1:
                st.markdown(f"### {d['account_name']}")
                mrr = d.get("mrr_estimate")
                if mrr:
                    st.caption(f"MRR: ${mrr:,.0f} | TL: {d.get('team_lead', 'N/A')}")

            with c2:
                st.markdown("**AI Forecast**")
                render_forecast_badge(d.get("ai_forecast_category"))
                st.caption(f"Health: {d.get('health_score', '--')}")

            with c3:
                st.markdown("**IC Forecast**")
                render_forecast_badge(d.get("ic_forecast_category"))

            with c4:
                explanation = d.get("divergence_explanation") or d.get("forecast_rationale")
                if explanation:
                    st.markdown("**AI Reasoning:**")
                    st.caption(explanation[:300])
