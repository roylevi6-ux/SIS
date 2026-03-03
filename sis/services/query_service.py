"""Query service — LLM-powered conversational interface with tool-use.

Two-tier context strategy:
  Tier 1 (always): pipeline summary injected as context
  Tier 2 (on-demand): Claude calls tools to fetch deal details, agent analyses, transcripts

Tool-use loop: max 3 rounds of tool calls per query.
"""

from __future__ import annotations

import json
import logging

import anthropic

from sis.config import MODEL_CHAT
from sis.llm.client import get_client
from sis.services.account_service import (
    list_accounts,
    get_account_detail,
    resolve_account_by_name,
)
from sis.services.analysis_service import get_latest_run_id, get_agent_analyses
from sis.services.transcript_service import search_transcript as _search_transcript
from sis.services.dashboard_service import (
    get_pipeline_overview,
    get_divergence_report,
    get_team_rollup,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5

# ── System prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the SIS (Sales Intelligence System) assistant for Riskified's sales team.
You answer questions about deal health, pipeline status, forecasts, and team performance.

You have:
1. A pipeline summary provided below with all deals at a glance.
2. Tools to fetch detailed data: deal assessments, agent analyses, transcript evidence, and transcript search.

TOOL STRATEGY (follow this order):
1. For simple pipeline questions (counts, lists, comparisons) — answer from the summary data directly, no tools needed.
2. For deal-specific questions (health, risks, forecast) — call get_deal_assessment first.
3. For evidence/quote questions — call get_all_agent_evidence FIRST. This returns curated transcript quotes already extracted by our analysis agents. This is usually sufficient.
4. For specific agent dimension questions — call get_agent_analysis with the agent name.
5. ONLY use search_transcript if agent evidence doesn't contain what's needed. Call list_deal_transcripts first to see available calls, then search the most relevant one.

Rules:
- Always complete your research and give a FINAL ANSWER. Never respond with just "Let me search..." — finish the search and present results.
- Always cite your sources: agent name, call date, or direct quotes when available.
- Be concise and specific. Use bullet points for lists.
- If a tool returns no results or an error, say so honestly — never hallucinate.
- Reference deal names, scores, and categories exactly as shown in the data.
- Some transcripts are in Japanese. When searching Japanese transcripts, use both English and Japanese keywords.
"""

# ── Tool definitions (Anthropic format) ──────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_deal_assessment",
        "description": (
            "Get the full deal assessment for a specific account: deal memo, health score, "
            "health breakdown by dimension, top risks, positive signals, recommended actions, "
            "key unknowns, contradictions, forecast details, and SF snapshot. "
            "Use this when the user asks about a specific deal's health, risks, or status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "The deal/account name (fuzzy matched — spaces and underscores both work)",
                },
            },
            "required": ["account_name"],
        },
    },
    {
        "name": "get_agent_analysis",
        "description": (
            "Get the full analysis output from a specific agent for a deal. "
            "Includes the complete narrative (not truncated), structured findings, "
            "evidence citations with transcript quotes, confidence score, and data gaps. "
            "Use when the user asks about a specific dimension like champion strength, "
            "competitive position, technical validation, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "The deal/account name",
                },
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Agent identifier. Use agent_id format (agent_1 through agent_9) or "
                        "descriptive name: agent_1=Stage Classification, agent_2=Relationship & Champion, "
                        "agent_3=Commercial Analysis, agent_4=Momentum & Engagement, "
                        "agent_5=Technical Validation, agent_6=Economic Buyer, "
                        "agent_7=MSP & Next Steps, agent_8=Competitive Intelligence, "
                        "agent_9=Open Discovery Questions"
                    ),
                },
            },
            "required": ["account_name", "agent_name"],
        },
    },
    {
        "name": "get_all_agent_evidence",
        "description": (
            "Get all evidence citations (transcript quotes) from every agent for a deal. "
            "This is the most token-efficient way to see what transcript evidence supports "
            "the deal assessment. Each citation includes the quote, source call, and relevance. "
            "Use when the user asks 'show me the evidence' or 'what supports this assessment'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "The deal/account name",
                },
            },
            "required": ["account_name"],
        },
    },
    {
        "name": "list_deal_transcripts",
        "description": (
            "List all call transcripts for a deal with metadata: date, title, duration, "
            "participants, topics, and token count. Use this to see what calls are available "
            "before searching within a specific transcript."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {
                    "type": "string",
                    "description": "The deal/account name",
                },
            },
            "required": ["account_name"],
        },
    },
    {
        "name": "search_transcript",
        "description": (
            "Search within a specific transcript for a keyword or phrase. Returns matching "
            "paragraphs with surrounding context. Use after list_deal_transcripts to search "
            "a specific call. Max 10 matches returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transcript_id": {
                    "type": "string",
                    "description": "UUID of the transcript (from list_deal_transcripts)",
                },
                "search_query": {
                    "type": "string",
                    "description": "Keyword or phrase to search for (case-insensitive)",
                },
            },
            "required": ["transcript_id", "search_query"],
        },
    },
]


# ── Tool executor ────────────────────────────────────────────────────


def execute_tool(
    tool_name: str,
    tool_input: dict,
    visible_user_ids: set[str] | None = None,
) -> str:
    """Execute a tool call and return the result as a JSON string."""
    try:
        if tool_name == "get_deal_assessment":
            return _exec_get_deal_assessment(tool_input, visible_user_ids)
        elif tool_name == "get_agent_analysis":
            return _exec_get_agent_analysis(tool_input, visible_user_ids)
        elif tool_name == "get_all_agent_evidence":
            return _exec_get_all_agent_evidence(tool_input, visible_user_ids)
        elif tool_name == "list_deal_transcripts":
            return _exec_list_deal_transcripts(tool_input, visible_user_ids)
        elif tool_name == "search_transcript":
            return _exec_search_transcript(tool_input)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.error("Tool execution error (%s): %s", tool_name, e)
        return json.dumps({"error": f"Tool error: {str(e)}"})


def _resolve_or_error(account_name: str, visible_user_ids: set[str] | None) -> dict | str:
    """Resolve account name or return a JSON error string."""
    acct = resolve_account_by_name(account_name, visible_user_ids=visible_user_ids)
    if not acct:
        return json.dumps({
            "error": f"No account found matching '{account_name}'. Check the deal name in the pipeline summary."
        })
    return acct


def _exec_get_deal_assessment(tool_input: dict, visible_user_ids: set[str] | None) -> str:
    acct = _resolve_or_error(tool_input["account_name"], visible_user_ids)
    if isinstance(acct, str):
        return acct

    try:
        detail = get_account_detail(acct["id"])
    except ValueError:
        return json.dumps({"error": f"Could not load details for {acct['account_name']}"})

    assessment = detail.get("assessment")
    if not assessment:
        return json.dumps({"account_name": acct["account_name"], "error": "No assessment available yet."})

    return json.dumps({
        "account_name": acct["account_name"],
        "health_score": assessment.get("health_score"),
        "momentum_direction": assessment.get("momentum_direction"),
        "ai_forecast_category": assessment.get("ai_forecast_category"),
        "deal_memo": assessment.get("deal_memo"),
        "manager_brief": assessment.get("manager_brief"),
        "health_breakdown": assessment.get("health_breakdown", []),
        "top_risks": assessment.get("top_risks", []),
        "top_positive_signals": assessment.get("top_positive_signals", []),
        "recommended_actions": assessment.get("recommended_actions", []),
        "key_unknowns": assessment.get("key_unknowns", []),
        "contradiction_map": assessment.get("contradiction_map", []),
        "stage": {
            "inferred": assessment.get("inferred_stage"),
            "name": assessment.get("stage_name"),
            "confidence": assessment.get("stage_confidence"),
        },
        "forecast": {
            "category": assessment.get("ai_forecast_category"),
            "rationale": assessment.get("forecast_rationale"),
            "divergence_flag": assessment.get("divergence_flag"),
            "divergence_explanation": assessment.get("divergence_explanation"),
        },
        "sf_snapshot": {
            "stage": assessment.get("sf_stage_at_run"),
            "forecast": assessment.get("sf_forecast_at_run"),
            "close_quarter": assessment.get("sf_close_quarter_at_run"),
        },
    }, default=str)


def _exec_get_agent_analysis(tool_input: dict, visible_user_ids: set[str] | None) -> str:
    acct = _resolve_or_error(tool_input["account_name"], visible_user_ids)
    if isinstance(acct, str):
        return acct

    run_id = get_latest_run_id(acct["id"])
    if not run_id:
        return json.dumps({"error": f"No analysis run found for {acct['account_name']}"})

    agent_outputs = get_agent_analyses(run_id)
    agent_query = tool_input["agent_name"].lower().strip()

    for agent in agent_outputs:
        agent_id = agent.get("agent_id", "").lower()
        agent_name = agent.get("agent_name", "").lower()
        if agent_query in agent_id or agent_query in agent_name or agent_id in agent_query:
            return json.dumps({
                "agent_id": agent["agent_id"],
                "agent_name": agent["agent_name"],
                "narrative": agent.get("narrative", ""),
                "findings": agent.get("findings", {}),
                "evidence": agent.get("evidence", []),
                "confidence_overall": agent.get("confidence_overall"),
                "confidence_rationale": agent.get("confidence_rationale"),
                "data_gaps": agent.get("data_gaps", []),
                "sparse_data_flag": agent.get("sparse_data_flag", False),
            }, default=str)

    available = [f"{a['agent_id']} ({a['agent_name']})" for a in agent_outputs]
    return json.dumps({
        "error": f"No agent matching '{tool_input['agent_name']}' found.",
        "available_agents": available,
    })


def _exec_get_all_agent_evidence(tool_input: dict, visible_user_ids: set[str] | None) -> str:
    acct = _resolve_or_error(tool_input["account_name"], visible_user_ids)
    if isinstance(acct, str):
        return acct

    run_id = get_latest_run_id(acct["id"])
    if not run_id:
        return json.dumps({"error": f"No analysis run found for {acct['account_name']}"})

    agent_outputs = get_agent_analyses(run_id)
    by_agent = []
    total = 0
    for agent in agent_outputs:
        evidence = agent.get("evidence", [])
        if evidence:
            by_agent.append({
                "agent_name": agent["agent_name"],
                "agent_id": agent["agent_id"],
                "evidence": evidence,
            })
            total += len(evidence)

    return json.dumps({
        "account_name": acct["account_name"],
        "total_evidence_items": total,
        "by_agent": by_agent,
    }, default=str)


def _exec_list_deal_transcripts(tool_input: dict, visible_user_ids: set[str] | None) -> str:
    acct = _resolve_or_error(tool_input["account_name"], visible_user_ids)
    if isinstance(acct, str):
        return acct

    try:
        detail = get_account_detail(acct["id"])
    except ValueError:
        return json.dumps({"error": f"Could not load details for {acct['account_name']}"})

    transcripts = detail.get("transcripts", [])
    return json.dumps({
        "account_name": acct["account_name"],
        "transcript_count": len(transcripts),
        "transcripts": [
            {
                "id": t["id"],
                "call_date": t.get("call_date"),
                "call_title": t.get("call_title"),
                "duration_minutes": t.get("duration_minutes"),
                "participants": t.get("participants"),
                "token_count": t.get("token_count"),
                "call_topics": t.get("call_topics"),
            }
            for t in sorted(transcripts, key=lambda x: x.get("call_date") or "", reverse=True)
        ],
    }, default=str)


def _exec_search_transcript(tool_input: dict) -> str:
    result = _search_transcript(tool_input["transcript_id"], tool_input["search_query"])
    if result is None:
        return json.dumps({"error": f"Transcript {tool_input['transcript_id']} not found."})
    return json.dumps(result, default=str)


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


# ── Helper ───────────────────────────────────────────────────────────


def _extract_text(response) -> str:
    """Extract text content from a Claude response."""
    texts = []
    for block in response.content:
        if hasattr(block, "text"):
            texts.append(block.text)
    return "\n".join(texts) if texts else "I wasn't able to generate a response. Please try again."


# ── Public API ───────────────────────────────────────────────────────


def query(
    user_message: str,
    history: list[dict] | None = None,
    visible_user_ids: set[str] | None = None,
) -> str:
    """Process a natural language query about the pipeline using tool-use.

    Args:
        user_message: The user's question.
        history: Previous messages as [{"role": "user"|"assistant", "content": str}].
        visible_user_ids: Role-based scoping (None = admin/see all).

    Returns:
        The LLM's answer as a string.
    """
    accounts = list_accounts(visible_user_ids=visible_user_ids)
    context = _build_context(accounts)

    # Early return if no pipeline data to query
    if "## All Deals\n" not in context or context.endswith("## All Deals\n"):
        return "No pipeline data available yet. Upload transcripts and run analysis first."

    # Build message list
    messages: list[dict] = []
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"<pipeline_data>\n{context}\n</pipeline_data>\n\n{user_message}",
    })

    client = get_client()

    try:
        # Agentic tool-use loop
        for _round in range(MAX_TOOL_ROUNDS + 1):
            response = client.messages.create(
                model=MODEL_CHAT,
                max_tokens=6000,
                temperature=0.2,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )

            # If Claude responded with text (no tool use), return it
            if response.stop_reason == "end_turn":
                return _extract_text(response)

            # If Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Add assistant message with tool_use blocks
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool call
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = execute_tool(
                            block.name, block.input, visible_user_ids
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason — return whatever text we have
            return _extract_text(response)

        # Fallback if loop exhausts without text response
        return _extract_text(response)

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
