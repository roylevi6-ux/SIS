"""Pipeline Overview — main dashboard page per PRD P0-9.

Two-level grouping: Team/TL then Forecast Category.
Shows: deal name, MRR, stage, health score, momentum, AI forecast, IC forecast, days since last call.
"""

import streamlit as st

from sis.services.dashboard_service import get_pipeline_overview, get_pipeline_insights
from sis.ui.components.health_badge import render_health_badge, render_momentum_indicator, render_forecast_badge
from sis.ui.components.layout import (
    page_header, section_divider, metric_row, status_badge,
)
from sis.ui.theme import Colors


def _render_insight_items(items: list[dict], color: str, section_key: str) -> None:
    """Render a list of insight items with clickable account names."""
    for item in items:
        col_name, col_desc = st.columns([1, 3])
        with col_name:
            if st.button(item["account_name"], key=f"insight_{section_key}_{item['account_id']}"):
                st.session_state["selected_account_id"] = item["account_id"]
                st.rerun()
        with col_desc:
            delta = item.get("score_delta")
            delta_str = f" ({'+' if delta > 0 else ''}{delta} pts)" if delta else ""
            st.markdown(
                f'<span style="color:{color}">{item["description"]}{delta_str}</span>',
                unsafe_allow_html=True,
            )


def render():
    page_header("Pipeline Overview")

    # Pipeline Insights panel
    insights = get_pipeline_insights()
    has_insights = any(insights[k] for k in insights)
    if has_insights:
        with st.expander("Pipeline Insights", expanded=True):
            insight_sections = [
                ("Stuck Deals", insights["stuck"], Colors.DANGER),
                ("Declining Deals", insights["declining"], Colors.DANGER),
                ("Improving Deals", insights["improving"], Colors.SUCCESS),
                ("New Risks", insights["new_risks"], Colors.WARNING),
                ("Forecast Flips", insights["forecast_flips"], Colors.ACCENT),
                ("Stale Deals", insights["stale"], Colors.NEUTRAL),
            ]
            for section_name, items, color in insight_sections:
                if items:
                    section_key = section_name.lower().replace(" ", "_")
                    st.markdown(
                        f'<h4 style="color:{color};margin-bottom:4px">{section_name} ({len(items)})</h4>',
                        unsafe_allow_html=True,
                    )
                    _render_insight_items(items, color, section_key)

    # Team filter
    overview = get_pipeline_overview()

    metric_row([
        {"label": "Total Deals", "value": overview["total_deals"]},
        {"label": "Healthy (70+)", "value": overview["summary"]["healthy_count"]},
        {"label": "At Risk (45-69)", "value": overview["summary"]["at_risk_count"]},
        {"label": "Critical (<45)", "value": overview["summary"]["critical_count"]},
    ])

    section_divider()

    # Render each tier
    for tier_name, tier_deals, tier_color in [
        ("Critical", overview["critical"], Colors.DANGER),
        ("At Risk", overview["at_risk"], Colors.WARNING),
        ("Healthy", overview["healthy"], Colors.SUCCESS),
        ("Unscored", overview["unscored"], Colors.NEUTRAL),
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
                                status_badge("DIVERGENT", "danger"),
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
