# Chat Tool-Use Redesign

**Date:** 2026-03-03
**Status:** Approved
**Author:** Claude + Roy

## Problem

The SIS chatbot can't answer questions about transcript evidence, agent findings, or detailed deal data. It pre-builds a text context and stuffs it into the prompt, but:

1. **Deal name matching fails** — account names use underscores (`Rakuten_Ichiba`) but users type spaces (`Rakuten Ichiba`). The `_detect_deal()` function does substring matching that misses these.
2. **Transcript evidence excluded** — `_build_deal_context()` only includes call metadata (dates, titles), not the actual transcript content or agent evidence citations.
3. **Agent findings truncated** — only `narrative` (capped at 500 chars) is included. The `evidence` and `findings` fields are never sent to the LLM.
4. **Static context = brittle** — every new data type requires code changes to include it in the context builder.

## Solution: Claude Tool-Use

Replace the Tier 2 context-stuffing approach with Claude's native tool-use (function calling). The LLM decides which data to fetch based on the user's question, calls parameterized DB query functions, and synthesizes results into an answer.

### Architecture

```
User Question
    │
    ▼
┌─────────────────────────────────┐
│  Tier 1 Context (always)        │  ◄── Pipeline summary, deal one-liners,
│  Injected as system context     │      divergences, team rollup, rep perf
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Claude API (tool-use mode)     │
│  - Reads Tier 1 for simple Q's  │
│  - Calls tools for deep-dive    │
└─────────┬───────────────────────┘
          │ tool_use blocks
          ▼
┌─────────────────────────────────┐
│  Tool Executor (server-side)    │
│  - Parameterized DB queries     │
│  - Returns structured JSON      │
│  - Max 3 tool rounds per query  │
└─────────┬───────────────────────┘
          │ tool_result blocks
          ▼
┌─────────────────────────────────┐
│  Claude synthesizes final answer│
│  (streamed to frontend)         │
└─────────────────────────────────┘
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tier 1 context | Keep always-injected | Simple questions ("how many at risk?") answered in one round-trip without tools |
| Latency | Acceptable (3-8s) | Accuracy > speed for this use case |
| Transcript access | Keyword search | Token-efficient; avoids dumping 40K tokens of raw text |
| Scope | Single-deal Phase 1 | Ship fast, add cross-deal search in Phase 2 |
| Tool call cap | 3 rounds max | Prevents runaway token/cost per query |
| Frontend changes | None | Backend handles tool loop internally, returns final string |
| Streaming | Keep | Stream final response to avoid 60s proxy timeout |

## Tool Definitions (Phase 1)

### 1. `get_deal_assessment`

**Purpose:** Full deal assessment for a specific account.

**Parameters:**
- `account_name` (string, required) — deal name (fuzzy matched)

**Returns:**
```json
{
  "account_name": "Rakuten_Ichiba",
  "health_score": 38,
  "momentum_direction": "Declining",
  "ai_forecast_category": "At Risk",
  "deal_memo": "...",
  "manager_brief": "...",
  "health_breakdown": [...],
  "top_risks": [...],
  "top_positive_signals": [...],
  "recommended_actions": [...],
  "key_unknowns": [...],
  "contradiction_map": [...],
  "stage": { "inferred": 3, "name": "Establish Business Case", "confidence": 0.85 },
  "forecast": { "category": "At Risk", "rationale": "...", "divergence": "..." },
  "sf_snapshot": { "stage": 4, "forecast": "Realistic", "close_quarter": "Q2 2026" }
}
```

**DB query:** `get_account_detail(account_id)` → existing function, already returns all this data.

### 2. `get_agent_analysis`

**Purpose:** Full output from a specific agent for a deal.

**Parameters:**
- `account_name` (string, required)
- `agent_name` (string, required) — e.g. "Champion Analysis", "Stage Classification", or agent_id like "agent_2"

**Returns:**
```json
{
  "agent_id": "agent_2_relationship",
  "agent_name": "Relationship & Champion Analysis",
  "narrative": "Full narrative text (no truncation)",
  "findings": { "champion_identified": true, "champion_name": "Sarah Chen", ... },
  "evidence": [
    { "quote": "Sarah mentioned she's been pushing internally...", "source": "2026-02-15 QBR", "relevance": "Champion advocacy" }
  ],
  "confidence_overall": 72,
  "confidence_rationale": "...",
  "data_gaps": ["No direct conversation with economic buyer"],
  "sparse_data_flag": false
}
```

**DB query:** `get_agent_analyses(run_id)` → existing function, filter by agent_id/name.

### 3. `get_all_agent_evidence`

**Purpose:** Curated transcript quotes from ALL agents for a deal. The most token-efficient way to answer "show me evidence" questions.

**Parameters:**
- `account_name` (string, required)

**Returns:**
```json
{
  "account_name": "Rakuten_Ichiba",
  "total_evidence_items": 24,
  "by_agent": [
    {
      "agent_name": "Relationship & Champion Analysis",
      "evidence": [
        { "quote": "...", "source": "2026-02-15 QBR", "relevance": "..." }
      ]
    },
    ...
  ]
}
```

**DB query:** `get_agent_analyses(run_id)` → extract `evidence` field from each.

### 4. `list_deal_transcripts`

**Purpose:** List all calls for a deal with metadata (so the AI can decide which to search).

**Parameters:**
- `account_name` (string, required)

**Returns:**
```json
{
  "account_name": "Rakuten_Ichiba",
  "transcript_count": 4,
  "transcripts": [
    {
      "id": "abc-123",
      "call_date": "2026-02-15",
      "call_title": "QBR",
      "duration_minutes": 45,
      "participants": ["Sarah Chen", "Mike Johnson"],
      "token_count": 6200,
      "call_topics": [{"name": "Pricing", "duration": 120}]
    }
  ]
}
```

**DB query:** `get_account_detail(account_id)` → extract `transcripts` list.

### 5. `search_transcript`

**Purpose:** Keyword search within a specific transcript. Returns matching paragraphs with surrounding context.

**Parameters:**
- `transcript_id` (string, required) — from `list_deal_transcripts`
- `search_query` (string, required) — keyword or phrase to search for

**Returns:**
```json
{
  "transcript_id": "abc-123",
  "call_title": "QBR",
  "call_date": "2026-02-15",
  "query": "pricing",
  "matches": [
    {
      "text": "...surrounding paragraph with the keyword...",
      "position": 0.45
    }
  ],
  "total_matches": 3
}
```

**Implementation:** Load `preprocessed_text` (or `raw_text` fallback) from DB. Split into paragraphs. Case-insensitive search for query terms. Return matching paragraphs with +-1 paragraph of context. Cap at 10 matches to control token usage.

## Deal Name Resolution

All tools accept `account_name` as a fuzzy string. A shared `_resolve_account()` function handles matching:

1. Normalize: replace underscores with spaces, lowercase both sides
2. Exact match (normalized)
3. Substring match (longest wins)
4. Multi-word match: split on spaces AND underscores, check all significant words (>2 chars) present
5. If no match: return error with closest suggestions (Levenshtein or first-letter match)

This replaces the current broken `_detect_deal()` function.

## System Prompt Update

```
You are the SIS (Sales Intelligence System) assistant for Riskified's sales team.
You answer questions about deal health, pipeline status, forecasts, and team performance.

You have:
1. A pipeline summary injected below with all deals at a glance.
2. Tools to fetch detailed data: deal assessments, agent analyses, transcript evidence, and transcript search.

Rules:
- For simple pipeline questions, answer from the summary data directly.
- For deal-specific questions, USE YOUR TOOLS to fetch the relevant data before answering.
- When asked about evidence, quotes, or "why" questions, use get_all_agent_evidence or search_transcript.
- Always cite your sources: agent name, call date, or direct quotes when available.
- Be concise and specific. Use bullet points for lists.
- If a tool returns no results, say so honestly — never hallucinate.
- You may call up to 3 tools per question. If you need more, summarize what you found and suggest the user ask a follow-up.
```

## Implementation Scope

### Files to modify:
- `sis/services/query_service.py` — Major rewrite: add tool definitions, tool executor, agentic loop
- `sis/services/account_service.py` — Add `resolve_account_by_name()` with fuzzy matching
- `sis/services/analysis_service.py` — Add `get_agent_analysis_by_name()` helper
- `sis/services/transcript_service.py` — New: `search_transcript()` function

### Files unchanged:
- `sis/api/routes/chat.py` — No changes (same request/response contract)
- `sis/api/schemas/chat.py` — No changes
- `frontend/` — No changes at all

### New file:
- `sis/services/transcript_service.py` — Transcript search logic

## Token Budget Estimate

| Scenario | Tokens (approx) |
|----------|-----------------|
| Simple pipeline question (no tools) | ~4K input + ~500 output = ~4.5K |
| Deal deep-dive (1-2 tools) | ~6K input + ~3K tool results + ~1K output = ~10K |
| Transcript search (2-3 tools) | ~6K input + ~5K tool results + ~1K output = ~12K |
| Worst case (3 tool rounds) | ~6K input + ~10K tool results + ~2K output = ~18K |

Current cost per chat query: ~4.5K tokens (~$0.02).
After redesign: ~4.5K-18K tokens (~$0.02-$0.08).

## Phase 2 (Future): Cross-Deal Search

Additional tools for Phase 2:
- `search_across_deals(query)` — keyword search across all deal evidence/transcripts
- `compare_deals(deal_names[])` — side-by-side comparison of multiple deals
- `get_team_deals(team_lead)` — all deals for a specific TL with summaries

## Testing Strategy

1. Unit tests for each tool function (DB queries return expected data)
2. Unit test for `_resolve_account()` fuzzy matching (underscores, partial names, typos)
3. Integration test: mock Claude API, verify tool-use loop executes correctly
4. Manual QA: test the exact failing scenario (Rakuten Ichiba transcript evidence)
