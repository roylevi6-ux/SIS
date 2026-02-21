"""Deal Detail — per-account drill-down per PRD P0-10.

Synthesis-first: deal memo + health breakdown + recommended actions.
Per-agent analysis collapsed behind expand controls.
"""

import json

import streamlit as st

from sis.services.account_service import get_account_detail, list_accounts
from sis.services.analysis_service import get_agent_analyses, get_latest_run_id
from sis.services.feedback_service import list_feedback
from sis.ui.components.health_badge import render_health_badge, render_momentum_indicator, render_forecast_badge


def render():
    st.title("Deal Detail")

    # Account selector
    accounts = list_accounts()
    if not accounts:
        st.info("No accounts yet. Upload transcripts first.")
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
                st.error("DIVERGENT — AI and IC forecasts differ")

    st.divider()

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
                    name = component.get("component", "Unknown")
                    score = component.get("score", 0)
                    max_score = component.get("max_score", 20)
                    pct = score / max_score if max_score > 0 else 0
                    color = "#22c55e" if pct >= 0.7 else "#f59e0b" if pct >= 0.45 else "#ef4444"
                    st.markdown(
                        f'<div style="padding:8px;border-radius:8px;background:{color}10;border:1px solid {color}40">'
                        f'<b>{name}</b><br>'
                        f'<span style="font-size:24px;color:{color}">{score}/{max_score}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    st.divider()

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
                icon = "🔴" if severity == "Critical" else "🟡" if severity == "High" else "🟠"
                st.warning(f"{icon} **{risk.get('risk', '')}** ({severity})")
                agents = ", ".join(risk.get("supporting_agents", []))
                if agents:
                    st.caption(f"Sources: {agents}")

    st.divider()

    # ── Recommended Actions ──
    st.subheader("Recommended Actions")
    for action in assessment.get("recommended_actions", []):
        if isinstance(action, dict):
            priority = action.get("priority", "P2")
            color = "#ef4444" if priority == "P0" else "#f59e0b" if priority == "P1" else "#6b7280"
            st.markdown(
                f'<div style="padding:8px;margin:4px 0;border-left:4px solid {color};background:{color}08">'
                f'<b>[{priority}]</b> {action.get("action", "")}<br>'
                f'<span style="color:#6b7280">Owner: {action.get("owner", "TBD")} | {action.get("rationale", "")}</span>'
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
                    st.divider()

    # ── Per-Agent Analysis (collapsed) ──
    st.divider()
    st.subheader("Per-Agent Analysis")

    # Find the latest run ID via service layer
    latest_run_id = get_latest_run_id(account_id)
    if latest_run_id:
        agent_analyses = get_agent_analyses(latest_run_id)
        for analysis in agent_analyses:
            conf = analysis.get('confidence_overall')
            label = (
                f"Agent: {analysis['agent_name']} (confidence: {conf:.0%})"
                if conf else f"Agent: {analysis['agent_name']}"
            )
            with st.expander(label):
                st.markdown(analysis.get("narrative", ""))

                findings = analysis.get("findings", {})
                if findings:
                    st.json(findings)

                evidence = analysis.get("evidence", [])
                if evidence:
                    st.markdown("**Evidence:**")
                    for ev in evidence[:5]:
                        if isinstance(ev, dict):
                            st.markdown(
                                f'> *"{ev.get("quote", "")}"*\n'
                                f'> — {ev.get("speaker", "Unknown")}, '
                                f'Call {ev.get("transcript_index", "?")}\n'
                                f'> {ev.get("interpretation", "")}'
                            )

    # ── Score Feedback Button ──
    st.divider()
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
