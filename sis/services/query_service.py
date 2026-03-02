"""Query service — LLM-powered conversational interface per Section 6.5.

Gathers all pipeline data into a context string, sends it with the user's
question to the LLM, and returns a formatted answer.  This is a structured
query layer over stored data — NOT re-running the pipeline per query.

Two-tier context strategy:
  Tier 1 (always): pipeline summary, all deals one-liner, divergences, team rollup
  Tier 2 (on-demand): full assessment, agent analyses, call history for a detected deal
"""

from __future__ import annotations

import logging

import anthropic

from sis.config import MODEL_CHAT
from sis.llm.client import get_client
from sis.services.account_service import list_accounts, get_account_detail
from sis.services.analysis_service import get_latest_run_id, get_agent_analyses
from sis.services.dashboard_service import (
    get_pipeline_overview,
    get_divergence_report,
    get_team_rollup,
)

logger = logging.getLogger(__name__)

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
- For rep performance questions ("How is X doing?", "Compare reps", "Who is underperforming?"):
  - Reference their avg health score, deal count, MRR, and health tier breakdown.
  - Highlight momentum trends (how many deals improving vs declining).
  - Flag divergent forecasts and critical deals by name.
  - When comparing reps, use a consistent format: health, MRR, momentum, risks.

When deal-specific data is available (marked with "## Deal Deep Dive"):
- Reference specific agent findings and confidence levels when explaining assessments.
- Cite health breakdown dimensions (e.g. "Champion Strength scored 4/10") when explaining why a score is low.
- Reference specific risks, positive signals, and recommended actions by name.
- Use the deal memo as the primary narrative, then supplement with agent details.
- When explaining "why" a deal is at risk, cite the lowest-scoring health dimensions and top risks.
- Reference call history dates and topics to give recency context.
"""


# ── Intent detection ─────────────────────────────────────────────────


def _detect_deal(message: str, accounts: list[dict]) -> dict | None:
    """Detect if the user is asking about a specific deal.

    Heuristic matching: checks if any account name (or all its significant
    words) appear in the user message.  Returns the best match or None.
    """
    msg_lower = message.lower()

    best_match = None
    best_length = 0

    for acct in accounts:
        name = acct.get("account_name", "")
        if not name:
            continue
        name_lower = name.lower()

        # Full-name substring match (prefer longest)
        if name_lower in msg_lower:
            if len(name_lower) > best_length:
                best_match = acct
                best_length = len(name_lower)
            continue

        # Multi-word: all significant words (>2 chars) present in message
        words = [w for w in name_lower.split() if len(w) > 2]
        if words and all(w in msg_lower for w in words):
            match_length = sum(len(w) for w in words)
            if match_length > best_length:
                best_match = acct
                best_length = match_length

    return best_match


# ── Tier 2: deal deep-dive context ──────────────────────────────────


def _build_deal_context(account_id: str) -> str:
    """Build Tier 2 deep-dive context for a specific deal."""
    try:
        detail = get_account_detail(account_id)
    except ValueError:
        return ""

    sections: list[str] = []
    name = detail["account_name"]
    sections.append(f"\n## Deal Deep Dive: {name}")

    assessment = detail.get("assessment")
    if not assessment:
        sections.append("No assessment available for this deal yet.")
        return "\n".join(sections)

    # Deal Memo
    if assessment.get("deal_memo"):
        sections.append(f"\n### Deal Memo\n{assessment['deal_memo']}")

    # Health Breakdown
    breakdown = assessment.get("health_breakdown", [])
    if breakdown:
        sections.append("\n### Health Breakdown")
        for dim in breakdown:
            if isinstance(dim, dict):
                dim_name = dim.get("dimension", dim.get("name", "Unknown"))
                score = dim.get("score", "N/A")
                weight = dim.get("weight", "")
                rationale = dim.get("rationale", "")
                weight_str = f" (weight: {weight})" if weight else ""
                sections.append(
                    f"- {dim_name}: {score}/10{weight_str} — {rationale}"
                )

    # Top Risks
    risks = assessment.get("top_risks", [])
    if risks:
        sections.append("\n### Top Risks")
        for r in risks:
            if isinstance(r, dict):
                sections.append(
                    f"- {r.get('risk', r.get('description', str(r)))}"
                )
            else:
                sections.append(f"- {r}")

    # Positive Signals
    signals = assessment.get("top_positive_signals", [])
    if signals:
        sections.append("\n### Positive Signals")
        for s in signals:
            if isinstance(s, dict):
                sections.append(
                    f"- {s.get('signal', s.get('description', str(s)))}"
                )
            else:
                sections.append(f"- {s}")

    # Recommended Actions
    actions = assessment.get("recommended_actions", [])
    if actions:
        sections.append("\n### Recommended Actions")
        for a in actions:
            if isinstance(a, dict):
                sections.append(
                    f"- {a.get('action', a.get('description', str(a)))}"
                )
            else:
                sections.append(f"- {a}")

    # Key Unknowns
    unknowns = assessment.get("key_unknowns", [])
    if unknowns:
        sections.append("\n### Key Unknowns")
        for u in unknowns:
            sections.append(f"- {u}")

    # Contradictions
    contradictions = assessment.get("contradiction_map", [])
    if contradictions:
        sections.append("\n### Contradictions")
        for c in contradictions:
            if isinstance(c, dict):
                sections.append(
                    f"- {c.get('description', c.get('contradiction', str(c)))}"
                )
            else:
                sections.append(f"- {c}")

    # Forecast
    sections.append("\n### Forecast")
    sections.append(
        f"- AI Forecast: {assessment.get('ai_forecast_category', 'N/A')}"
    )
    if assessment.get("forecast_rationale"):
        sections.append(f"- Rationale: {assessment['forecast_rationale']}")
    sf = detail.get("sf_forecast_category")
    if sf:
        sections.append(f"- SF Forecast: {sf}")
    if assessment.get("divergence_flag"):
        sections.append(
            f"- DIVERGENT: {assessment.get('divergence_explanation', 'AI and SF disagree')}"
        )

    # Agent Analyses
    run_id = get_latest_run_id(account_id)
    if run_id:
        agent_outputs = get_agent_analyses(run_id)
        if agent_outputs:
            sections.append("\n### Agent Analyses")
            for agent in agent_outputs:
                conf = agent.get("confidence_overall")
                if conf is not None:
                    conf_str = (
                        f" (confidence: {conf:.0f}%)"
                        if conf > 1
                        else f" (confidence: {conf:.0%})"
                    )
                else:
                    conf_str = ""
                agent_name = agent.get(
                    "agent_name", agent.get("agent_id", "Unknown")
                )
                narrative = agent.get("narrative", "")
                if len(narrative) > 500:
                    narrative = narrative[:500] + "..."
                sections.append(f"- **{agent_name}**{conf_str}: {narrative}")

    # Call History (metadata only — no raw transcript text)
    transcripts = detail.get("transcripts", [])
    if transcripts:
        sections.append("\n### Call History")
        sorted_transcripts = sorted(
            transcripts,
            key=lambda t: t.get("call_date") or "",
            reverse=True,
        )
        for t in sorted_transcripts:
            parts: list[str] = [str(t.get("call_date", "Unknown date"))]
            if t.get("call_title"):
                parts.append(t["call_title"])
            if t.get("duration_minutes"):
                parts.append(f"{t['duration_minutes']} min")
            participants = t.get("participants")
            if participants and isinstance(participants, list):
                parts.append(f"with {', '.join(str(p) for p in participants)}")
            sections.append(f"- {' | '.join(parts)}")

    return "\n".join(sections)


# ── Rep performance context ─────────────────────────────────────────


def _build_rep_context(accounts: list[dict]) -> str:
    """Build per-rep performance summary from account data.

    Groups accounts by ae_owner (the rep who owns the deal), aggregates
    health scores, MRR, momentum, forecast distribution, and flags.
    """
    reps: dict[str, list[dict]] = {}
    for a in accounts:
        rep = a.get("ae_owner") or a.get("team_lead") or "Unassigned"
        reps.setdefault(rep, []).append(a)

    if not reps or (len(reps) == 1 and "Unassigned" in reps):
        return ""

    lines: list[str] = ["\n## Rep Performance"]

    for rep_name in sorted(reps.keys()):
        deals = reps[rep_name]
        scored = [d for d in deals if d.get("health_score") is not None]
        total_mrr = sum(d.get("cp_estimate") or 0 for d in deals)

        # Health tiers
        healthy = sum(1 for d in scored if d["health_score"] >= 70)
        neutral = sum(1 for d in scored if 40 <= d["health_score"] < 70)
        needs_attention = sum(1 for d in scored if d["health_score"] < 40)
        avg_health = (
            round(sum(d["health_score"] for d in scored) / len(scored), 1)
            if scored else None
        )

        # Momentum breakdown
        momentum_counts: dict[str, int] = {}
        for d in scored:
            mom = d.get("momentum_direction", "Unknown")
            momentum_counts[mom] = momentum_counts.get(mom, 0) + 1

        # Forecast distribution
        forecast_counts: dict[str, int] = {}
        for d in scored:
            fc = d.get("ai_forecast_category", "Unknown")
            forecast_counts[fc] = forecast_counts.get(fc, 0) + 1

        divergent = sum(1 for d in scored if d.get("divergence_flag"))

        # Build rep line
        avg_str = f"{avg_health:.0f}" if avg_health is not None else "N/A"
        mom_str = ", ".join(f"{k}={v}" for k, v in sorted(momentum_counts.items()))
        fc_str = ", ".join(f"{k}={v}" for k, v in sorted(forecast_counts.items()))
        deal_names = [d["account_name"] for d in deals]

        lines.append(
            f"### {rep_name}\n"
            f"  Deals ({len(deals)}): {', '.join(deal_names)}\n"
            f"  Avg Health: {avg_str} | MRR: ${total_mrr:,.0f}\n"
            f"  Healthy: {healthy}, Neutral: {neutral}, Needs Attention: {needs_attention}\n"
            f"  Momentum: {mom_str}\n"
            f"  Forecast: {fc_str}\n"
            f"  Divergent: {divergent}"
        )

    return "\n".join(lines)


# ── Tier 1: pipeline-wide context ───────────────────────────────────


def _build_context(accounts: list[dict]) -> str:
    """Build a Tier 1 context string with all pipeline data for the LLM."""
    overview = get_pipeline_overview()
    divergences = get_divergence_report()
    rollup = get_team_rollup()

    sections: list[str] = []

    sections.append("## Pipeline Summary")
    s = overview["summary"]
    sections.append(
        f"Total: {overview['total_deals']} deals | "
        f"Healthy: {s['healthy_count']} (${s['total_mrr_healthy']:,.0f}) | "
        f"Neutral: {s['neutral_count']} (${s['total_mrr_neutral']:,.0f}) | "
        f"Needs Attention: {s['needs_attention_count']} (${s['total_mrr_needs_attention']:,.0f})"
    )

    sections.append("\n## All Deals")
    for a in accounts:
        hs = a.get("health_score", "N/A")
        mom = a.get("momentum_direction", "N/A")
        ai_fc = a.get("ai_forecast_category", "N/A")
        sf_fc = a.get("sf_forecast_category", "Not set")
        stage = f"{a.get('inferred_stage', '?')} ({a.get('stage_name', 'N/A')})"
        mrr = f"${a['cp_estimate']:,.0f}" if a.get("cp_estimate") else "N/A"
        div = " [DIVERGENT]" if a.get("divergence_flag") else ""
        sections.append(
            f"- {a['account_name']}: Health={hs}, Momentum={mom}, "
            f"Stage={stage}, AI={ai_fc}, SF={sf_fc}, MRR={mrr}, "
            f"TL={a.get('team_lead', 'N/A')}{div}"
        )

    if divergences:
        sections.append("\n## Divergent Forecasts")
        for d in divergences:
            sections.append(
                f"- {d['account_name']}: AI={d['ai_forecast_category']}, "
                f"SF={d['sf_forecast_category']}, CP Est.=${d.get('cp_estimate', 0):,.0f}"
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

    # Rep performance
    rep_section = _build_rep_context(accounts)
    if rep_section:
        sections.append(rep_section)

    return "\n".join(sections)


# ── Public API ───────────────────────────────────────────────────────


def query(user_message: str, history: list[dict] | None = None) -> str:
    """Process a natural language query about the pipeline.

    Args:
        user_message: The user's question.
        history: Previous messages as [{"role": "user"|"assistant", "content": str}].
                 Should NOT include the current user_message.

    Returns:
        The LLM's answer as a string.
    """
    accounts = list_accounts()
    context = _build_context(accounts)

    # Early return if no pipeline data to query
    if "## All Deals\n" not in context or context.endswith("## All Deals\n"):
        return "No pipeline data available yet. Upload transcripts and run analysis first."

    # Tier 2: detect if user is asking about a specific deal
    matched = _detect_deal(user_message, accounts)
    if matched and matched.get("id"):
        deal_context = _build_deal_context(matched["id"])
        if deal_context:
            context = context + "\n" + deal_context

    messages: list[dict] = []
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Current query with injected pipeline context
    messages.append({
        "role": "user",
        "content": f"<pipeline_data>\n{context}\n</pipeline_data>\n\n{user_message}",
    })

    client = get_client()

    try:
        # Use streaming to avoid Riskified proxy 60s timeout (matches runner.py pattern)
        with client.messages.stream(
            model=MODEL_CHAT,
            max_tokens=6000,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        return response.content[0].text
    except anthropic.APITimeoutError:
        logger.warning("Chat query timed out")
        return "Sorry, the request timed out. Please try again."
    except anthropic.RateLimitError:
        logger.warning("Chat query rate limited")
        return "Rate limit reached. Please wait a moment and try again."
    except anthropic.APIConnectionError as e:
        logger.error("Chat API connection error: %s", e)
        return "Could not reach the AI service. Please check your connection and try again."
    except anthropic.APIError as e:
        logger.error("Chat API error: %s", e)
        return f"API error: {e}"
