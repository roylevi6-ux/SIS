"""Conversational Interface — natural language queries over pipeline data per PRD P0-13, P0-14.

Uses structured query over stored data (NOT re-running pipeline per query).
"""

import json

import streamlit as st

from sis.services.account_service import list_accounts, get_account_detail
from sis.services.dashboard_service import get_pipeline_overview, get_divergence_report, get_team_rollup


def render():
    st.title("Chat — Pipeline Intelligence")
    st.caption("Ask questions about your pipeline, deals, and forecasts")

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your pipeline..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process query
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = _process_query(prompt)
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

    # Suggested queries
    if not st.session_state.chat_messages:
        st.markdown("**Suggested queries:**")
        suggestions = [
            "Which deals are at risk?",
            "Show me the pipeline overview",
            "Which deals have divergent forecasts?",
            "Tell me about the highest health deal",
            "What's the team rollup?",
        ]
        cols = st.columns(len(suggestions))
        for i, suggestion in enumerate(suggestions):
            with cols[i]:
                if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                    response = _process_query(suggestion)
                    st.session_state.chat_messages.append({"role": "user", "content": suggestion})
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()


def _process_query(query: str) -> str:
    """Process a natural language query by matching intent and retrieving data.

    This is a structured query system, NOT free-form LLM RAG.
    Matches common query patterns and returns formatted data.
    """
    query_lower = query.lower()

    # Pattern: deals at risk / critical deals
    if any(kw in query_lower for kw in ["at risk", "critical", "declining", "trouble", "concern"]):
        overview = get_pipeline_overview()
        critical = overview["critical"]
        at_risk = overview["at_risk"]
        deals = critical + at_risk

        if not deals:
            return "No deals are currently at risk or critical."

        lines = [f"**{len(deals)} deals need attention:**\n"]
        for d in deals:
            score = d.get("health_score", "--")
            momentum = d.get("momentum_direction", "Unknown")
            lines.append(
                f"- **{d['account_name']}** — Health: {score}, "
                f"Momentum: {momentum}, Forecast: {d.get('ai_forecast_category', 'N/A')}"
            )
        return "\n".join(lines)

    # Pattern: pipeline overview / summary
    if any(kw in query_lower for kw in ["pipeline", "overview", "summary", "all deals"]):
        overview = get_pipeline_overview()
        s = overview["summary"]
        return (
            f"**Pipeline Overview:**\n\n"
            f"- **{overview['total_deals']}** total deals\n"
            f"- **{s['healthy_count']}** healthy (${s['total_mrr_healthy']:,.0f} MRR)\n"
            f"- **{s['at_risk_count']}** at risk (${s['total_mrr_at_risk']:,.0f} MRR)\n"
            f"- **{s['critical_count']}** critical (${s['total_mrr_critical']:,.0f} MRR)\n"
            f"- **{s['unscored_count']}** unscored"
        )

    # Pattern: divergence / divergent
    if any(kw in query_lower for kw in ["diverg", "disagree", "ai vs ic", "forecast differ"]):
        divergences = get_divergence_report()
        if not divergences:
            return "No forecast divergences found. AI and IC forecasts align on all deals."

        lines = [f"**{len(divergences)} divergent forecasts:**\n"]
        for d in divergences:
            lines.append(
                f"- **{d['account_name']}** — AI: {d['ai_forecast_category']}, "
                f"IC: {d['ic_forecast_category']} (MRR: ${d.get('mrr_estimate', 0):,.0f})"
            )
        return "\n".join(lines)

    # Pattern: team rollup
    if any(kw in query_lower for kw in ["team", "rollup", "group"]):
        rollup = get_team_rollup()
        if not rollup:
            return "No team data available."

        lines = ["**Team Rollup:**\n"]
        for team in rollup:
            avg = team.get("avg_health_score")
            avg_text = f"{avg:.0f}" if avg else "--"
            lines.append(
                f"- **{team['team_name']}** — {team['total_deals']} deals, "
                f"Avg health: {avg_text}, MRR: ${team['total_mrr']:,.0f}"
            )
        return "\n".join(lines)

    # Pattern: specific deal lookup
    if any(kw in query_lower for kw in ["tell me about", "detail", "what about", "how is"]):
        accounts = list_accounts()
        # Try to match account name
        for acct in accounts:
            if acct["account_name"].lower() in query_lower:
                detail = get_account_detail(acct["id"])
                assessment = detail.get("assessment")
                if not assessment:
                    return f"**{acct['account_name']}** has no analysis yet."

                return (
                    f"**{acct['account_name']}**\n\n"
                    f"- Health Score: **{assessment['health_score']}**\n"
                    f"- Stage: {assessment['inferred_stage']} — {assessment['stage_name']}\n"
                    f"- Momentum: {assessment['momentum_direction']}\n"
                    f"- AI Forecast: {assessment['ai_forecast_category']}\n"
                    f"- Confidence: {assessment['overall_confidence']:.0%}\n\n"
                    f"**Deal Memo:**\n{assessment['deal_memo'][:500]}..."
                )

    # Pattern: highest / best / top
    if any(kw in query_lower for kw in ["highest", "best", "top", "strongest"]):
        overview = get_pipeline_overview()
        healthy = overview["healthy"]
        if healthy:
            top = healthy[0]
            return (
                f"**Highest-scoring deal:** {top['account_name']} "
                f"(Health: {top['health_score']}, "
                f"Forecast: {top.get('ai_forecast_category', 'N/A')})"
            )

    # Fallback
    return (
        "I can answer questions about:\n"
        "- **Pipeline overview** — \"Show me the pipeline\"\n"
        "- **At-risk deals** — \"Which deals are at risk?\"\n"
        "- **Divergences** — \"Which forecasts diverge?\"\n"
        "- **Team rollup** — \"Team performance\"\n"
        "- **Specific deals** — \"Tell me about [Account Name]\"\n\n"
        "Try rephrasing your question using one of these patterns."
    )
