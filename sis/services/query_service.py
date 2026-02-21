"""Query service — LLM-powered conversational interface per Section 6.5.

Gathers all pipeline data into a context string, sends it with the user's
question to the LLM, and returns a formatted answer.  This is a structured
query layer over stored data — NOT re-running the pipeline per query.
"""

from __future__ import annotations

import anthropic

from sis.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL_CHAT
from sis.services.account_service import list_accounts
from sis.services.dashboard_service import (
    get_pipeline_overview,
    get_divergence_report,
    get_team_rollup,
)

SYSTEM_PROMPT = """You are the SIS (Sales Intelligence System) assistant for Riskified's sales team.
You answer questions about deal health, pipeline status, forecasts, and team performance.

You have access to structured pipeline data provided below. Answer based ONLY on this data.
If the data does not contain the answer, say so — never hallucinate.

Rules:
- Be concise and specific. Use bullet points for lists.
- Reference deal names, scores, and categories exactly as shown in the data.
- When comparing deals, cite specific health scores and momentum directions.
- If asked about a specific deal, include: health score, stage, momentum, forecast, top risks.
- For pipeline questions, summarize by health tier (Healthy 70+, At Risk 45-69, Critical <45).
- When asked about forecast divergence, explain both AI and IC categories and the delta.
"""


def _build_context() -> str:
    """Build a context string with all pipeline data for the LLM."""
    accounts = list_accounts()
    overview = get_pipeline_overview()
    divergences = get_divergence_report()
    rollup = get_team_rollup()

    sections: list[str] = []

    sections.append("## Pipeline Summary")
    s = overview["summary"]
    sections.append(
        f"Total: {overview['total_deals']} deals | "
        f"Healthy: {s['healthy_count']} (${s['total_mrr_healthy']:,.0f}) | "
        f"At Risk: {s['at_risk_count']} (${s['total_mrr_at_risk']:,.0f}) | "
        f"Critical: {s['critical_count']} (${s['total_mrr_critical']:,.0f})"
    )

    sections.append("\n## All Deals")
    for a in accounts:
        hs = a.get("health_score", "N/A")
        mom = a.get("momentum_direction", "N/A")
        ai_fc = a.get("ai_forecast_category", "N/A")
        ic_fc = a.get("ic_forecast_category", "Not set")
        stage = f"{a.get('inferred_stage', '?')} ({a.get('stage_name', 'N/A')})"
        mrr = f"${a['mrr_estimate']:,.0f}" if a.get("mrr_estimate") else "N/A"
        div = " [DIVERGENT]" if a.get("divergence_flag") else ""
        sections.append(
            f"- {a['account_name']}: Health={hs}, Momentum={mom}, "
            f"Stage={stage}, AI={ai_fc}, IC={ic_fc}, MRR={mrr}, "
            f"TL={a.get('team_lead', 'N/A')}{div}"
        )

    if divergences:
        sections.append("\n## Divergent Forecasts")
        for d in divergences:
            sections.append(
                f"- {d['account_name']}: AI={d['ai_forecast_category']}, "
                f"IC={d['ic_forecast_category']}, MRR=${d.get('mrr_estimate', 0):,.0f}"
            )

    if rollup:
        sections.append("\n## Team Rollup")
        for t in rollup:
            avg = f"{t['avg_health_score']:.0f}" if t.get("avg_health_score") else "N/A"
            sections.append(
                f"- {t['team_name']}: {t['total_deals']} deals, "
                f"Avg Health={avg}, MRR=${t['total_mrr']:,.0f}, "
                f"Divergent={t.get('divergent_count', 0)}"
            )

    return "\n".join(sections)


def query(user_message: str, history: list[dict] | None = None) -> str:
    """Process a natural language query about the pipeline.

    Args:
        user_message: The user's question.
        history: Previous messages as [{"role": "user"|"assistant", "content": str}].

    Returns:
        The LLM's answer as a string.
    """
    context = _build_context()

    messages: list[dict] = []
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"<pipeline_data>\n{context}\n</pipeline_data>\n\n{user_message}",
    })

    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
        timeout=60.0,
        max_retries=1,
    )

    response = client.messages.create(
        model=MODEL_CHAT,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    return response.content[0].text
