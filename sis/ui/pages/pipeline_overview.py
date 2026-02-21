"""Pipeline Overview — main dashboard page per PRD P0-9.

Two-level grouping: Team/TL then Forecast Category.
Shows: deal name, MRR, stage, health score, momentum, AI forecast, IC forecast, days since last call.
"""

import streamlit as st

from sis.services.dashboard_service import get_pipeline_overview
from sis.ui.components.health_badge import render_health_badge, render_momentum_indicator, render_forecast_badge


def render():
    st.title("Pipeline Overview")

    # Team filter
    overview = get_pipeline_overview()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Deals", overview["total_deals"])
    with col2:
        st.metric("Healthy (70+)", overview["summary"]["healthy_count"])
    with col3:
        st.metric("At Risk (45-69)", overview["summary"]["at_risk_count"])
    with col4:
        st.metric("Critical (<45)", overview["summary"]["critical_count"])

    st.divider()

    # Render each tier
    for tier_name, tier_deals, tier_color in [
        ("Critical", overview["critical"], "#ef4444"),
        ("At Risk", overview["at_risk"], "#f59e0b"),
        ("Healthy", overview["healthy"], "#22c55e"),
        ("Unscored", overview["unscored"], "#6b7280"),
    ]:
        if not tier_deals:
            continue

        st.markdown(
            f'<h3 style="color:{tier_color}">{tier_name} ({len(tier_deals)} deals)</h3>',
            unsafe_allow_html=True,
        )

        for deal in tier_deals:
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
                with c1:
                    # Clickable deal name
                    if st.button(
                        f"**{deal['account_name']}**",
                        key=f"deal_{deal['account_id']}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_account_id"] = deal["account_id"]
                        st.rerun()

                    mrr = deal.get("mrr_estimate")
                    if mrr:
                        st.caption(f"MRR: ${mrr:,.0f} | {deal.get('ae_owner', 'N/A')}")
                    else:
                        st.caption(f"AE: {deal.get('ae_owner', 'N/A')}")

                with c2:
                    st.caption("Health")
                    render_health_badge(deal.get("health_score"), size="small")

                with c3:
                    st.caption("Momentum")
                    render_momentum_indicator(deal.get("momentum_direction"))

                with c4:
                    st.caption("Stage")
                    stage = deal.get("inferred_stage")
                    st.markdown(f"**{stage}** {deal.get('stage_name', '')}" if stage else "--")

                with c5:
                    st.caption("AI Forecast")
                    render_forecast_badge(deal.get("ai_forecast_category"))

                with c6:
                    st.caption("IC Forecast")
                    ic = deal.get("ic_forecast_category")
                    if ic:
                        render_forecast_badge(ic)
                        if deal.get("divergence_flag"):
                            st.markdown(
                                '<span style="color:#ef4444;font-size:12px">⚠ DIVERGENT</span>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown("*Not set*")

                # IC Forecast entry (P0-8c)
                with st.expander("Set IC Forecast", expanded=False):
                    categories = ["", "Commit", "Best Case", "Pipeline", "Upside", "At Risk", "No Decision Risk"]
                    current_ic = deal.get("ic_forecast_category") or ""
                    current_idx = categories.index(current_ic) if current_ic in categories else 0
                    new_ic = st.selectbox(
                        "IC Forecast",
                        categories,
                        index=current_idx,
                        key=f"ic_{deal['account_id']}",
                        label_visibility="collapsed",
                    )
                    if new_ic and new_ic != current_ic:
                        if st.button("Save", key=f"save_ic_{deal['account_id']}"):
                            from sis.services.account_service import set_ic_forecast
                            result = set_ic_forecast(deal["account_id"], new_ic)
                            if result["divergence_flag"]:
                                st.toast(f"Divergence: {result['explanation'][:100]}", icon="\u26a0\ufe0f")
                            else:
                                st.toast("IC forecast saved. Matches AI forecast.", icon="\u2705")
                            st.rerun()
