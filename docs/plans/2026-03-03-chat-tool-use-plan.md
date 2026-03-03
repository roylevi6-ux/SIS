# Chat Tool-Use Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the chat bot's static context-stuffing with Claude tool-use so it can answer ANY question by querying the DB on demand.

**Architecture:** Keep Tier 1 pipeline summary always-injected. Add 5 tools (get_deal_assessment, get_agent_analysis, get_all_agent_evidence, list_deal_transcripts, search_transcript). Claude decides which to call. Server-side tool loop with max 3 rounds.

**Tech Stack:** Anthropic Python SDK tool-use, FastAPI, SQLAlchemy, existing service layer.

**Design Doc:** `docs/plans/2026-03-03-chat-tool-use-design.md`

---

### Task 1: Add `resolve_account_by_name()` to account_service.py

**Files:**
- Modify: `sis/services/account_service.py`
- Test: `tests/unit/test_resolve_account.py`

**Step 1: Write the failing tests**

Create `tests/unit/test_resolve_account.py`:

```python
"""Tests for fuzzy account name resolution."""
from __future__ import annotations
import pytest
from sis.services.account_service import resolve_account_by_name


class TestResolveAccountByName:

    def test_exact_match(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("HealthyCorp")
        assert result is not None
        assert result["account_name"] == "HealthyCorp"

    def test_case_insensitive(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("healthycorp")
        assert result is not None
        assert result["account_name"] == "HealthyCorp"

    def test_underscore_to_space(self, seeded_db, mock_get_session):
        """The original bug: users type spaces, DB has underscores."""
        # Seed an underscore-named account for this test
        from sis.db.models import Account
        mock_get_session.add(Account(
            id="underscore-test", account_name="Rakuten_Ichiba",
            cp_estimate=70000, deal_type="new_logo",
        ))
        mock_get_session.flush()

        result = resolve_account_by_name("Rakuten Ichiba")
        assert result is not None
        assert result["account_name"] == "Rakuten_Ichiba"

    def test_partial_match(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("Healthy")
        assert result is not None
        assert result["account_name"] == "HealthyCorp"

    def test_no_match_returns_none(self, seeded_db, mock_get_session):
        result = resolve_account_by_name("NonExistentDeal")
        assert result is None

    def test_multi_word_match(self, seeded_db, mock_get_session):
        from sis.db.models import Account
        mock_get_session.add(Account(
            id="multi-word-test", account_name="We_Love_Holidays",
            cp_estimate=30000, deal_type="new_logo",
        ))
        mock_get_session.flush()

        result = resolve_account_by_name("love holidays")
        assert result is not None
        assert result["account_name"] == "We_Love_Holidays"

    def test_prefers_longest_match(self, seeded_db, mock_get_session):
        from sis.db.models import Account
        mock_get_session.add(Account(
            id="short-test", account_name="Risk",
            cp_estimate=10000, deal_type="new_logo",
        ))
        mock_get_session.add(Account(
            id="long-test", account_name="AtRiskCo_Extended",
            cp_estimate=20000, deal_type="new_logo",
        ))
        mock_get_session.flush()

        # "AtRiskCo" should match the seeded AtRiskCo, not "Risk"
        result = resolve_account_by_name("AtRiskCo")
        assert result is not None
        assert result["account_name"] == "AtRiskCo"

    def test_visible_user_ids_scoping(self, seeded_db, mock_get_session):
        """Respects role-based scoping."""
        ae1_id = seeded_db["user_ids"]["ae1"]
        result = resolve_account_by_name("CriticalInc", visible_user_ids={ae1_id})
        # CriticalInc is owned by ae3, not ae1 — should not resolve
        assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_resolve_account.py -v`
Expected: FAIL — `resolve_account_by_name` not found

**Step 3: Implement `resolve_account_by_name`**

Add to `sis/services/account_service.py` after the existing `list_accounts` function (~line 250):

```python
def resolve_account_by_name(
    name: str,
    visible_user_ids: set[str] | None = None,
) -> dict | None:
    """Fuzzy-match an account name from user input.

    Handles underscores vs spaces, case differences, partial matches.
    Returns the best-matching account summary dict or None.
    """
    accounts = list_accounts(visible_user_ids=visible_user_ids)
    if not accounts:
        return None

    def _normalize(s: str) -> str:
        return s.replace("_", " ").lower().strip()

    query_norm = _normalize(name)
    best_match = None
    best_length = 0

    for acct in accounts:
        acct_name = acct.get("account_name", "")
        if not acct_name:
            continue
        acct_norm = _normalize(acct_name)

        # Exact normalized match
        if acct_norm == query_norm:
            return acct

        # Full-name substring match (prefer longest)
        if acct_norm in query_norm or query_norm in acct_norm:
            match_len = len(acct_norm)
            if match_len > best_length:
                best_match = acct
                best_length = match_len
            continue

        # Multi-word: all significant words present
        words = [w for w in query_norm.split() if len(w) > 2]
        if words and all(w in acct_norm for w in words):
            match_len = sum(len(w) for w in words)
            if match_len > best_length:
                best_match = acct
                best_length = match_len

    return best_match
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_resolve_account.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add sis/services/account_service.py tests/unit/test_resolve_account.py
git commit -m "feat(chat): add fuzzy account name resolution with underscore/space handling"
```

---

### Task 2: Add `search_transcript()` to transcript_service.py

**Files:**
- Modify: `sis/services/transcript_service.py`
- Test: `tests/unit/test_search_transcript.py`

**Step 1: Write the failing tests**

Create `tests/unit/test_search_transcript.py`:

```python
"""Tests for transcript keyword search."""
from __future__ import annotations
import json
import pytest
from sis.db.models import Account, Transcript
from sis.services.transcript_service import search_transcript


@pytest.fixture
def transcript_with_content(mock_get_session):
    """Seed an account with a transcript containing searchable text."""
    session = mock_get_session
    acct = Account(
        id="search-test-acct", account_name="SearchCorp",
        cp_estimate=50000, deal_type="new_logo",
    )
    session.add(acct)
    session.flush()

    text = (
        "SARAH CHEN (Riskified): Let me walk you through our pricing model.\n\n"
        "MIKE JOHNSON (SearchCorp): We have some concerns about the cost.\n"
        "The current budget allocation is tight this quarter.\n\n"
        "SARAH CHEN (Riskified): I understand. Let me address the pricing concern.\n"
        "We can offer a phased approach to reduce upfront cost.\n\n"
        "MIKE JOHNSON (SearchCorp): That sounds reasonable. What about the POC?\n"
        "We need to validate the chargeback reduction value before committing.\n\n"
        "SARAH CHEN (Riskified): Absolutely. The POC timeline would be 4 weeks.\n"
        "We guarantee a 15% reduction in chargebacks during the trial.\n\n"
        "MIKE JOHNSON (SearchCorp): The guarantee is important but we have cost concerns.\n"
        "We might need to exclude the guarantee from the POC scope.\n"
    )
    t = Transcript(
        id="search-test-t1", account_id="search-test-acct",
        call_date="2026-02-15", raw_text=text, preprocessed_text=text,
        token_count=500, call_title="QBR", is_active=1,
        participants=json.dumps([
            {"name": "Sarah Chen", "role": "AE", "company": "Riskified"},
            {"name": "Mike Johnson", "role": "VP", "company": "SearchCorp"},
        ]),
    )
    session.add(t)
    session.flush()
    return {"account_id": "search-test-acct", "transcript_id": "search-test-t1"}


class TestSearchTranscript:

    def test_finds_keyword(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "pricing")
        assert result["total_matches"] > 0
        assert any("pricing" in m["text"].lower() for m in result["matches"])

    def test_case_insensitive(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "POC")
        assert result["total_matches"] > 0

    def test_returns_metadata(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "pricing")
        assert result["call_title"] == "QBR"
        assert result["call_date"] == "2026-02-15"
        assert result["transcript_id"] == "search-test-t1"

    def test_no_matches(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "kubernetes")
        assert result["total_matches"] == 0
        assert result["matches"] == []

    def test_invalid_transcript_id(self, mock_get_session):
        result = search_transcript("nonexistent", "anything")
        assert result is None

    def test_max_matches_cap(self, transcript_with_content, mock_get_session):
        """Matches capped at 10 to control token usage."""
        # "the" appears in almost every paragraph
        result = search_transcript("search-test-t1", "the")
        assert result["total_matches"] <= 10

    def test_multi_word_search(self, transcript_with_content, mock_get_session):
        result = search_transcript("search-test-t1", "chargeback reduction")
        assert result["total_matches"] > 0
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_search_transcript.py -v`
Expected: FAIL — `search_transcript` not found

**Step 3: Implement `search_transcript`**

Add to `sis/services/transcript_service.py` at the end of the file:

```python
MAX_SEARCH_MATCHES = 10


def search_transcript(transcript_id: str, query: str) -> dict | None:
    """Keyword search within a transcript. Returns matching paragraphs.

    Args:
        transcript_id: UUID of the transcript to search.
        query: Keyword or phrase to search for (case-insensitive).

    Returns:
        Dict with metadata + matching text snippets, or None if transcript not found.
    """
    with get_session() as session:
        t = session.query(Transcript).filter_by(id=transcript_id).first()
        if not t:
            return None

        text = t.preprocessed_text or t.raw_text
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        query_lower = query.lower()
        query_words = query_lower.split()

        matches = []
        for i, para in enumerate(paragraphs):
            para_lower = para.lower()
            # Match if all words in the query appear in the paragraph
            if all(w in para_lower for w in query_words):
                # Include +-1 paragraph of context
                context_parts = []
                if i > 0:
                    context_parts.append(paragraphs[i - 1])
                context_parts.append(para)
                if i < len(paragraphs) - 1:
                    context_parts.append(paragraphs[i + 1])

                matches.append({
                    "text": "\n\n".join(context_parts),
                    "position": round(i / max(len(paragraphs), 1), 2),
                })

                if len(matches) >= MAX_SEARCH_MATCHES:
                    break

        participants = json.loads(t.participants) if t.participants else []

        return {
            "transcript_id": t.id,
            "call_title": t.call_title,
            "call_date": t.call_date,
            "participants": participants,
            "query": query,
            "matches": matches,
            "total_matches": len(matches),
        }
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_search_transcript.py -v`
Expected: All PASS

**Step 5: Update conftest patch targets**

Add `"sis.services.transcript_service.get_session"` to `_patch_targets` in `tests/conftest.py` (it's already there at line 84, so this is a no-op — verify).

**Step 6: Commit**

```bash
git add sis/services/transcript_service.py tests/unit/test_search_transcript.py
git commit -m "feat(chat): add keyword search within transcripts"
```

---

### Task 3: Define tool schemas and executor in query_service.py

**Files:**
- Modify: `sis/services/query_service.py` (major rewrite)
- Test: `tests/unit/test_chat_tools.py`

**Step 1: Write failing tests for tool definitions and executor**

Create `tests/unit/test_chat_tools.py`:

```python
"""Tests for chat tool definitions and executor."""
from __future__ import annotations
import json
import pytest
from unittest.mock import patch, MagicMock
from sis.services.query_service import (
    TOOL_DEFINITIONS,
    execute_tool,
)


class TestToolDefinitions:

    def test_all_tools_defined(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        assert names == {
            "get_deal_assessment",
            "get_agent_analysis",
            "get_all_agent_evidence",
            "list_deal_transcripts",
            "search_transcript",
        }

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_account_name_required_on_deal_tools(self):
        for tool in TOOL_DEFINITIONS:
            if tool["name"] != "search_transcript":
                assert "account_name" in tool["input_schema"]["properties"]
                assert "account_name" in tool["input_schema"]["required"]


class TestExecuteTool:

    def test_get_deal_assessment(self, seeded_db, mock_get_session):
        result = execute_tool("get_deal_assessment", {"account_name": "HealthyCorp"})
        parsed = json.loads(result)
        assert parsed["account_name"] == "HealthyCorp"
        assert "health_score" in parsed
        assert "deal_memo" in parsed

    def test_get_agent_analysis(self, seeded_db, mock_get_session):
        result = execute_tool("get_agent_analysis", {
            "account_name": "HealthyCorp",
            "agent_name": "agent_2",
        })
        parsed = json.loads(result)
        assert parsed["agent_id"] == "agent_2"
        assert "narrative" in parsed
        assert "evidence" in parsed
        assert "findings" in parsed

    def test_get_all_agent_evidence(self, seeded_db, mock_get_session):
        result = execute_tool("get_all_agent_evidence", {"account_name": "HealthyCorp"})
        parsed = json.loads(result)
        assert parsed["account_name"] == "HealthyCorp"
        assert "by_agent" in parsed
        assert len(parsed["by_agent"]) > 0

    def test_list_deal_transcripts(self, seeded_db, mock_get_session):
        result = execute_tool("list_deal_transcripts", {"account_name": "HealthyCorp"})
        parsed = json.loads(result)
        assert parsed["transcript_count"] > 0
        assert "transcripts" in parsed

    def test_search_transcript(self, seeded_db, mock_get_session):
        t_id = seeded_db["transcript_ids"][seeded_db["healthy_id"]][0]
        result = execute_tool("search_transcript", {
            "transcript_id": t_id,
            "search_query": "discovery",
        })
        parsed = json.loads(result)
        assert parsed["total_matches"] > 0

    def test_unknown_tool_returns_error(self, seeded_db, mock_get_session):
        result = execute_tool("nonexistent_tool", {})
        parsed = json.loads(result)
        assert "error" in parsed

    def test_unresolved_account_returns_error(self, seeded_db, mock_get_session):
        result = execute_tool("get_deal_assessment", {"account_name": "FakeCo"})
        parsed = json.loads(result)
        assert "error" in parsed
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_chat_tools.py -v`
Expected: FAIL — imports not found

**Step 3: Implement tool definitions and executor**

Rewrite `sis/services/query_service.py`. The key additions:

1. `TOOL_DEFINITIONS` — list of Claude tool schemas
2. `execute_tool(name, input)` — dispatches to the right service function
3. Each tool handler: resolves account name, queries DB, returns JSON string

```python
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

MAX_TOOL_ROUNDS = 3

# ── System prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the SIS (Sales Intelligence System) assistant for Riskified's sales team.
You answer questions about deal health, pipeline status, forecasts, and team performance.

You have:
1. A pipeline summary provided below with all deals at a glance.
2. Tools to fetch detailed data: deal assessments, agent analyses, transcript evidence, and transcript search.

Rules:
- For simple pipeline questions (counts, lists, comparisons), answer from the summary data directly.
- For deal-specific questions, USE YOUR TOOLS to fetch the relevant data before answering.
- When asked about evidence, quotes, or "why" questions, use get_all_agent_evidence or search_transcript.
- Always cite your sources: agent name, call date, or direct quotes when available.
- Be concise and specific. Use bullet points for lists.
- If a tool returns no results or an error, say so honestly — never hallucinate.
- Reference deal names, scores, and categories exactly as shown in the data.
- When comparing deals, cite specific health scores and momentum directions.
- For rep performance questions, reference avg health, deal count, MRR, and momentum trends.
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_chat_tools.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add sis/services/query_service.py tests/unit/test_chat_tools.py
git commit -m "feat(chat): add tool definitions and executor for 5 chat tools"
```

---

### Task 4: Implement the tool-use agentic loop

**Files:**
- Modify: `sis/services/query_service.py` (the `query()` function)
- Test: `tests/unit/test_chat_tool_loop.py`

**Step 1: Write failing tests for the agentic loop**

Create `tests/unit/test_chat_tool_loop.py`:

```python
"""Tests for the chat tool-use agentic loop."""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
import pytest
from sis.services.query_service import query


def _make_text_response(text: str):
    """Mock a Claude response with just text (no tool use)."""
    msg = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg.content = [block]
    msg.stop_reason = "end_turn"
    msg.usage = MagicMock(input_tokens=100, output_tokens=50)
    return msg


def _make_tool_use_response(tool_name: str, tool_input: dict, tool_use_id: str = "tool_1"):
    """Mock a Claude response that requests a tool call."""
    msg = MagicMock()
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_use_id
    msg.content = [block]
    msg.stop_reason = "tool_use"
    msg.usage = MagicMock(input_tokens=100, output_tokens=50)
    return msg


class TestQueryToolLoop:

    @patch("sis.services.query_service.get_client")
    @patch("sis.services.query_service.list_accounts")
    @patch("sis.services.query_service.get_pipeline_overview")
    @patch("sis.services.query_service.get_divergence_report")
    @patch("sis.services.query_service.get_team_rollup")
    def test_simple_question_no_tools(
        self, mock_rollup, mock_div, mock_overview, mock_accounts, mock_client
    ):
        """Simple pipeline question answered without tools."""
        mock_accounts.return_value = [
            {"account_name": "TestCo", "health_score": 80, "id": "1",
             "momentum_direction": "Improving", "ai_forecast_category": "Commit",
             "sf_forecast_category": "Commit", "inferred_stage": 5,
             "stage_name": "Negotiate", "cp_estimate": 50000,
             "team_lead": "TL", "divergence_flag": False},
        ]
        mock_overview.return_value = {"total_deals": 1, "summary": {
            "healthy_count": 1, "total_mrr_healthy": 50000,
            "neutral_count": 0, "total_mrr_neutral": 0,
            "needs_attention_count": 0, "total_mrr_needs_attention": 0,
        }}
        mock_div.return_value = []
        mock_rollup.return_value = []

        # Claude returns text directly
        client = MagicMock()
        mock_client.return_value = client
        client.messages.create.return_value = _make_text_response("You have 1 deal.")

        result = query("How many deals?")
        assert result == "You have 1 deal."

    @patch("sis.services.query_service.execute_tool")
    @patch("sis.services.query_service.get_client")
    @patch("sis.services.query_service.list_accounts")
    @patch("sis.services.query_service.get_pipeline_overview")
    @patch("sis.services.query_service.get_divergence_report")
    @patch("sis.services.query_service.get_team_rollup")
    def test_tool_use_round_trip(
        self, mock_rollup, mock_div, mock_overview, mock_accounts,
        mock_client, mock_exec_tool
    ):
        """Claude calls a tool, gets results, then answers."""
        mock_accounts.return_value = [
            {"account_name": "TestCo", "health_score": 80, "id": "1",
             "momentum_direction": "Improving", "ai_forecast_category": "Commit",
             "sf_forecast_category": "Commit", "inferred_stage": 5,
             "stage_name": "Negotiate", "cp_estimate": 50000,
             "team_lead": "TL", "divergence_flag": False},
        ]
        mock_overview.return_value = {"total_deals": 1, "summary": {
            "healthy_count": 1, "total_mrr_healthy": 50000,
            "neutral_count": 0, "total_mrr_neutral": 0,
            "needs_attention_count": 0, "total_mrr_needs_attention": 0,
        }}
        mock_div.return_value = []
        mock_rollup.return_value = []

        client = MagicMock()
        mock_client.return_value = client

        # First call: Claude requests a tool
        tool_response = _make_tool_use_response(
            "get_deal_assessment", {"account_name": "TestCo"}
        )
        # Second call: Claude answers with text
        text_response = _make_text_response("TestCo health is 80.")

        client.messages.create.side_effect = [tool_response, text_response]
        mock_exec_tool.return_value = json.dumps({"health_score": 80})

        result = query("How is TestCo?")
        assert result == "TestCo health is 80."
        assert mock_exec_tool.call_count == 1

    @patch("sis.services.query_service.execute_tool")
    @patch("sis.services.query_service.get_client")
    @patch("sis.services.query_service.list_accounts")
    @patch("sis.services.query_service.get_pipeline_overview")
    @patch("sis.services.query_service.get_divergence_report")
    @patch("sis.services.query_service.get_team_rollup")
    def test_max_tool_rounds_enforced(
        self, mock_rollup, mock_div, mock_overview, mock_accounts,
        mock_client, mock_exec_tool
    ):
        """Tool loop stops after MAX_TOOL_ROUNDS even if Claude keeps calling tools."""
        mock_accounts.return_value = []
        mock_overview.return_value = {"total_deals": 0, "summary": {
            "healthy_count": 0, "total_mrr_healthy": 0,
            "neutral_count": 0, "total_mrr_neutral": 0,
            "needs_attention_count": 0, "total_mrr_needs_attention": 0,
        }}
        mock_div.return_value = []
        mock_rollup.return_value = []

        client = MagicMock()
        mock_client.return_value = client

        # Claude keeps requesting tools beyond the limit
        tool_resp = _make_tool_use_response("get_deal_assessment", {"account_name": "X"})
        mock_exec_tool.return_value = json.dumps({"error": "not found"})

        # 3 tool rounds + the forced final text
        client.messages.create.side_effect = [tool_resp, tool_resp, tool_resp,
                                               _make_text_response("Gave up.")]

        result = query("Tell me everything")
        # Should have called execute_tool exactly 3 times (MAX_TOOL_ROUNDS)
        assert mock_exec_tool.call_count == 3
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_chat_tool_loop.py -v`
Expected: FAIL — `query()` still uses old implementation

**Step 3: Rewrite the `query()` function with tool-use loop**

Replace the `query()` function and supporting code in `sis/services/query_service.py`. Keep `_build_context` and `_build_rep_context` unchanged (Tier 1). Remove `_detect_deal` and `_build_deal_context` (replaced by tools).

The new `query()`:

```python
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

                # If we've hit the max rounds, let Claude answer on next iteration
                # (the loop will break naturally since we add 1 to range)
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


def _extract_text(response) -> str:
    """Extract text content from a Claude response."""
    texts = []
    for block in response.content:
        if hasattr(block, "text"):
            texts.append(block.text)
    return "\n".join(texts) if texts else "I wasn't able to generate a response. Please try again."
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/unit/test_chat_tool_loop.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add sis/services/query_service.py tests/unit/test_chat_tool_loop.py
git commit -m "feat(chat): implement tool-use agentic loop replacing static context"
```

---

### Task 5: Update existing chat tests + run full suite

**Files:**
- Modify: `tests/test_api/test_chat.py`
- Modify: `tests/conftest.py` (if needed)

**Step 1: Update test_chat.py mocks**

The existing API tests mock `query_service.query` at the route level, so they should still pass unchanged. Verify:

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/test_api/test_chat.py -v`
Expected: All PASS (these tests mock the service, not the internals)

**Step 2: Run full test suite to check for regressions**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/ -v --tb=short -q`
Expected: All existing tests PASS

**Step 3: Fix any regressions if found**

If tests break due to the removed `_detect_deal` or `_build_deal_context`:
- These were private functions, no test should import them directly
- If any do, update those tests to use the new tool-based approach

**Step 4: Commit**

```bash
git add -u
git commit -m "test(chat): verify existing tests pass with tool-use refactor"
```

---

### Task 6: Manual QA — test the exact failing scenario

**Files:** None (manual testing)

**Step 1: Start the backend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m uvicorn sis.api.main:app --reload --port 8000`

**Step 2: Test via curl — the original failing scenario**

```bash
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "in the rakuten ichiba vp summary, i read this: Champion went from advocating chargeback reduction value to actively excluding the guarantee from POC due to cost concerns. Can you bring me the transcript evidence?"}'
```

**Expected:** The response should include actual transcript quotes or agent evidence citations, NOT "I don't have access to call transcripts."

**Step 3: Test simple pipeline question (no regression)**

```bash
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "How many deals are at risk?"}'
```

**Expected:** Quick answer from Tier 1 context, no tool calls needed.

**Step 4: Test via the UI**

Open `http://localhost:3000/chat` and ask both questions. Verify the frontend displays responses correctly (no changes expected to frontend).

---

### Task 7: Final cleanup and commit

**Step 1: Remove dead code**

Delete `_detect_deal()` and `_build_deal_context()` from `query_service.py` if not already removed in Task 3/4.

**Step 2: Run full test suite one more time**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/ -v --tb=short -q`
Expected: All PASS

**Step 3: Final commit**

```bash
git add -u
git commit -m "refactor(chat): remove dead Tier 2 context-stuffing code"
```

---

## Summary

| Task | What it does | Files |
|------|-------------|-------|
| 1 | Fuzzy account name resolution (underscore fix) | `account_service.py`, `test_resolve_account.py` |
| 2 | Transcript keyword search | `transcript_service.py`, `test_search_transcript.py` |
| 3 | Tool definitions + executor (5 tools) | `query_service.py`, `test_chat_tools.py` |
| 4 | Agentic tool-use loop | `query_service.py`, `test_chat_tool_loop.py` |
| 5 | Regression check on existing tests | `test_chat.py` |
| 6 | Manual QA — the exact failing scenario | None |
| 7 | Cleanup dead code | `query_service.py` |

**Total new test files:** 3 (`test_resolve_account.py`, `test_search_transcript.py`, `test_chat_tools.py`, `test_chat_tool_loop.py`)
**Frontend changes:** Zero
**API contract changes:** Zero (same request/response)
