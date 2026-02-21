"""Deal Detail — per-account drill-down per PRD P0-10.

Synthesis-first: deal memo + health breakdown + recommended actions.
Per-agent analysis collapsed behind expand controls.
"""

import html
import json

import streamlit as st

from sis.services.account_service import get_account_detail, list_accounts
from sis.services.analysis_service import get_agent_analyses, get_latest_run_id, get_carry_forward_actions
from sis.services.feedback_service import list_feedback
from sis.ui.components.health_badge import render_health_badge, render_momentum_indicator, render_forecast_badge
from sis.ui.components.divergence_badge import render_divergence_badge
from sis.ui.components.agent_card import render_agent_card
from sis.ui.components.layout import (
    page_header, section_divider, empty_state,
)
from sis.ui.theme import Colors


def render():
    page_header("Deal Detail")

    # Account selector
    accounts = list_accounts()
    if not accounts:
        empty_state("No accounts yet.", "\U0001f4ed", "Upload transcripts first.")
        return

    # Check if coming from pipeline overview click
    selected_id = st.session_state.get("selected_account_id")
    account_names = [a["account_name"] for a in accounts]
    account_ids = [a["id"] for a in accounts]

    default_idx = 0
    if selected_id and selected_id in account_ids:
        default_idx = account_ids.index(selected_id)

    selected_name = st.selectbox("Select Account", account_names, index=default_idx)
    idx = account_names.index(selected_name)
    account_id = account_ids[idx]

    detail = get_account_detail(account_id)
    assessment = detail.get("assessment")

    if not assessment:
        st.warning("No analysis run yet for this account. Go to 'Run Analysis' to start.")
        return

    # ── Header metrics ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_health_badge(assessment["health_score"])
    with col2:
        st.metric("Stage", f"{assessment['inferred_stage']} - {assessment['stage_name']}")
        st.caption(f"Confidence: {assessment['stage_confidence']:.0%}")
    with col3:
        st.markdown("**Momentum**")
        render_momentum_indicator(assessment["momentum_direction"])
        if assessment.get("momentum_trend"):
            st.caption(assessment["momentum_trend"])
    with col4:
        st.markdown("**Forecast**")
        render_forecast_badge(assessment["ai_forecast_category"])
        if detail.get("ic_forecast_category"):
            st.caption(f"IC: {detail['ic_forecast_category']}")
            if assessment.get("divergence_flag"):
                render_divergence_badge(
                    assessment["ai_forecast_category"],
                    detail["ic_forecast_category"],
                    assessment.get("divergence_explanation"),
                )

    section_divider()

    # ── Deal Memo ──
    st.subheader("Deal Memo")
    st.markdown(assessment["deal_memo"])

    # ── Health Score Breakdown ──
    st.subheader("Health Score Breakdown")
    breakdown = assessment.get("health_breakdown", [])
    if isinstance(breakdown, list):
        cols = st.columns(4)
        for i, component in enumerate(breakdown):
            with cols[i % 4]:
                if isinstance(component, dict):
                    name = html.escape(component.get("component", "Unknown"))
                    score = component.get("score", 0)
                    max_score = component.get("max_score", 20)
                    pct = score / max_score if max_score > 0 else 0
                    color = Colors.status_color(pct * 100)
                    st.markdown(
                        f'<div style="padding:8px;border-radius:8px;'
                        f'background:{Colors.with_alpha(color)};'
                        f'border:1px solid {Colors.with_alpha(color, "40")}">'
                        f'<b>{name}</b><br>'
                        f'<span style="font-size:24px;color:{color}">{score}/{max_score}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    section_divider()

    # ── Signals & Risks ──
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Top Positive Signals")
        for signal in assessment.get("top_positive_signals", []):
            if isinstance(signal, dict):
                st.success(f"**{signal.get('signal', '')}**")
                agents = ", ".join(signal.get("supporting_agents", []))
                if agents:
                    st.caption(f"Sources: {agents}")

    with col_right:
        st.subheader("Top Risks")
        for risk in assessment.get("top_risks", []):
            if isinstance(risk, dict):
                severity = risk.get("severity", "Medium")
                icon = "\U0001f534" if severity == "Critical" else "\U0001f7e1" if severity == "High" else "\U0001f7e0"
                st.warning(f"{icon} **{risk.get('risk', '')}** ({severity})")
                agents = ", ".join(risk.get("supporting_agents", []))
                if agents:
                    st.caption(f"Sources: {agents}")

    section_divider()

    # ── Recommended Actions ──
    st.subheader("Recommended Actions")
    for action in assessment.get("recommended_actions", []):
        if isinstance(action, dict):
            priority = html.escape(action.get("priority", "P2"))
            color = Colors.DANGER if priority == "P0" else Colors.WARNING if priority == "P1" else Colors.NEUTRAL
            css_class = "p0" if priority == "P0" else "p1" if priority == "P1" else "p2"
            action_text = html.escape(action.get("action", ""))
            owner_text = html.escape(action.get("owner", "TBD"))
            rationale_text = html.escape(action.get("rationale", ""))
            st.markdown(
                f'<div class="sis-action-item sis-action-item-{css_class}" '
                f'style="padding:8px;margin:4px 0;border-left:4px solid {color};'
                f'background:{Colors.with_alpha(color, "08")}">'
                f'<b>[{priority}]</b> {action_text}<br>'
                f'<span style="color:{Colors.NEUTRAL}">Owner: {owner_text} | {rationale_text}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Carry-Forward: Unfollowed Actions from Previous Run ──
    unfollowed = get_carry_forward_actions(account_id)
    if unfollowed:
        st.markdown(
            f'<div style="padding:8px;margin:8px 0;border-left:4px solid {Colors.DANGER};'
            f'background:{Colors.with_alpha(Colors.DANGER, "08")}">'
            f'<b>Unfollowed Actions from Previous Run ({len(unfollowed)})</b></div>',
            unsafe_allow_html=True,
        )
        for uf in unfollowed:
            if isinstance(uf, dict):
                priority = html.escape(uf.get("priority", "P2"))
                action_text = html.escape(uf.get("action", ""))
                owner_text = html.escape(uf.get("owner", "TBD"))
                st.markdown(
                    f'<div style="padding:6px;margin:2px 0;border-left:4px solid {Colors.DANGER};'
                    f'background:{Colors.with_alpha(Colors.DANGER, "08")};opacity:0.85">'
                    f'<b>[{priority}]</b> {action_text} '
                    f'<span style="color:{Colors.DANGER};font-weight:600">(not addressed)</span><br>'
                    f'<span style="color:{Colors.NEUTRAL}">Owner: {owner_text}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Contradiction Map ──
    contradictions = assessment.get("contradiction_map", [])
    if contradictions:
        with st.expander(f"Contradiction Map ({len(contradictions)} items)"):
            for c in contradictions:
                if isinstance(c, dict):
                    st.markdown(f"**{c.get('dimension', 'Unknown')}**")
                    st.markdown(f"- Agree: {', '.join(c.get('agents_agree', []))}")
                    st.markdown(f"- Contradict: {', '.join(c.get('agents_contradict', []))}")
                    st.markdown(f"- Resolution: {c.get('resolution', 'N/A')}")
                    section_divider()

    # ── Per-Agent Analysis (collapsed) ──
    section_divider()
    st.subheader("Per-Agent Analysis")

    # Find the latest run ID via service layer
    latest_run_id = get_latest_run_id(account_id)
    if latest_run_id:
        agent_analyses = get_agent_analyses(latest_run_id)
        for analysis in agent_analyses:
            render_agent_card(analysis)

    # ── Score Feedback Button ──
    section_divider()
    with st.expander("Flag This Score"):
        with st.form("feedback_form"):
            direction = st.radio("Score is:", ["too_high", "too_low"])
            reason = st.selectbox("Reason:", [
                "off_channel", "stakeholder_context", "stage_mismatch",
                "score_too_high", "recent_change", "other",
            ])
            free_text = st.text_area("Additional context (optional)")
            author = st.text_input("Your name")
            off_channel = st.checkbox("Off-channel activity not captured?")

            if st.form_submit_button("Submit Feedback"):
                if not author:
                    st.error("Please enter your name.")
                else:
                    from sis.services.feedback_service import submit_feedback
                    result = submit_feedback(
                        account_id=account_id,
                        assessment_id=assessment["id"],
                        author=author,
                        direction=direction,
                        reason=reason,
                        free_text=free_text if free_text else None,
                        off_channel=off_channel,
                    )
                    st.success(f"Feedback submitted. ID: {result['id'][:8]}...")
