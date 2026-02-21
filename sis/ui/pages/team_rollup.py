"""Team Rollup — aggregate health metrics per team per PRD P0-12."""

import streamlit as st

from sis.services.dashboard_service import get_team_rollup


def render():
    st.title("Team Rollup")

    rollup = get_team_rollup()

    if not rollup:
        st.info("No teams found. Add accounts with team assignments first.")
        return

    for team in rollup:
        with st.container(border=True):
            st.subheader(team["team_name"])

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Total Deals", team["total_deals"])
            with c2:
                avg = team.get("avg_health_score")
                st.metric("Avg Health", f"{avg:.0f}" if avg else "--")
            with c3:
                st.metric("Healthy", team["healthy_count"])
            with c4:
                st.metric("At Risk", team["at_risk_count"])
            with c5:
                st.metric("Critical", team["critical_count"])

            c6, c7 = st.columns(2)
            with c6:
                mrr = team.get("total_mrr", 0)
                st.metric("Total MRR", f"${mrr:,.0f}" if mrr else "--")
            with c7:
                st.metric("Divergent", team["divergent_count"])
