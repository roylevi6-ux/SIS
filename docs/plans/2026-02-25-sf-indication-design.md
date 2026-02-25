# SF Indication Fields — Design Document

**Date**: 2026-02-25
**Status**: Approved

## Problem

SIS produces independent deal assessments (stage, forecast, health) from transcript analysis, but there's no way to compare these against what the rep has in Salesforce. A VP Sales needs to see the gap: "SIS says Stage 3 based on the calls, but SF says Stage 5 — is the rep over-forecasting?"

## Solution

Add SF indication fields at upload time (both single and batch), snapshot them per analysis run, feed them to Agent 10 as a post-synthesis gap analysis step, and display the gap on the deal detail page and pipeline dashboard.

**POC mode:** Static manual input, labeled "SF indication at day of last analysis."
**Production mode:** Live data from Salesforce API (future work).

---

## Key Decisions

### Agent Visibility (AI Lead recommendation, approved)

- **Agents 1-9: BLOCKED** from SF data. The system's value depends on independent, transcript-based inference. Exposing SF stage/forecast would cause anchoring bias — the LLM would confirm the SF values instead of reading the transcripts independently.
- **Agent 10 (Synthesis): SEES SF data in Step 5 only** — after completing its independent synthesis (Steps 1-4). This preserves unbiased deal memo and health score, then adds gap interpretation.
- **CP Estimate: BLOCKED from agents 1-9**, shown to Agent 10 in Step 5 for gap context.

### Naming

- `mrr_estimate` → `cp_estimate` (Contribution Profit). This is how quota is denominated.
- SF stages use **name only** in the UI (Qualify, Discover, Scope, etc.) with numeric values (1-7) stored internally.
- SF stage values and forecast categories are identical to SIS's — no mapping table needed.
- `sf_close_quarter` is the expected close-won quarter (not the current calendar quarter).

---

## DB Schema Changes

### Account table — new/renamed columns

| Column | Type | Change | Description |
|--------|------|--------|-------------|
| `cp_estimate` | Float, nullable | Rename from `mrr_estimate` | Contribution Profit estimate ($) |
| `sf_stage` | Integer, nullable | New | SF stage number (1-7) |
| `sf_forecast_category` | Text, nullable | New | "Commit" / "Realistic" / "Upside" / "At Risk" |
| `sf_close_quarter` | Text, nullable | New | Expected close quarter, e.g. "Q2 2026" |

### DealAssessment table — new columns (snapshot at run time)

| Column | Type | Description |
|--------|------|-------------|
| `sf_stage_at_run` | Integer, nullable | SF stage when analysis ran |
| `sf_forecast_at_run` | Text, nullable | SF forecast category when analysis ran |
| `sf_close_quarter_at_run` | Text, nullable | SF close quarter when analysis ran |
| `cp_estimate_at_run` | Float, nullable | CP estimate when analysis ran |
| `stage_gap_direction` | Text, nullable | "Aligned" / "SF-ahead" / "SIS-ahead" |
| `stage_gap_magnitude` | Integer, nullable | Absolute stage difference (0-6) |
| `forecast_gap_direction` | Text, nullable | "Aligned" / "SF-more-optimistic" / "SIS-more-optimistic" |
| `sf_gap_interpretation` | Text, nullable | Agent 10's natural language gap analysis |

---

## Upload UX

### SF Indication Section

Both single and batch upload flows get an **"SF Indication"** section with a muted header: *"Salesforce indication at day of last analysis"*.

**Fields (all optional):**
- **SF Stage** — Dropdown: Qualify, Discover, Scope, Validate, Negotiate, Prove, Close
- **SF Forecast Category** — Dropdown: Commit, Realistic, Upside, At Risk
- **Close Quarter** — Dropdown: current Q through Q+4 (auto-populated)
- **CP Estimate ($)** — Number input (replaces MRR Estimate)

### Single Upload (Paste / Local Folder)

SF fields appear below the deal type and IC dropdowns, in a visually grouped section.

### Batch Upload (Google Drive)

The multi-select table gets 4 new per-row columns for checked rows:

```
┌─────┬──────────────┬──────────┬────────────┬───────────┬──────────┬──────────┬──────────┬──────────┐
│  [x]│ Airalo       │ 5 of 34  │ [New Logo] │ [J.Smith] │ [Scope]  │ [Commit] │ [Q2 '26] │ [$350K]  │
│  [x]│ Wirex        │ 5 of 12  │ [Upsell]   │ [M.Jones] │ [Negot.] │ [Upside] │ [Q1 '26] │ [$120K]  │
│  [ ]│ Rakuten      │  — 28    │            │           │          │          │          │          │
└─────┴──────────────┴──────────┴────────────┴───────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Pipeline Integration

### Data Flow

1. **Upload:** SF fields saved to Account model
2. **Analysis start:** `analysis_service.py` reads SF fields from Account, snapshots to DealAssessment columns
3. **Pipeline:** `deal_context` does NOT include SF fields (agents 1-9 stay blind)
4. **Agent 10 Step 5:** `synthesis.py:build_call()` accepts optional `sf_data` dict, appends gap analysis prompt after agent outputs
5. **Post-pipeline:** Deterministic gap computation (code-level, zero LLM cost)
6. **Persist:** Gap fields stored on DealAssessment

### Agent 10 Step 5 Prompt Addition

Appended to user prompt after all agent outputs:

```
## STEP 5: SALESFORCE GAP ANALYSIS
Compare your independent assessment from Steps 1-4 against these Salesforce
values provided by the rep. Do NOT revise your deal memo, health score, or
forecast. Analyze the gaps only.

SF Stage: Negotiate (5)
SF Forecast Category: Commit
SF Close Quarter: Q2 2026
CP Estimate: $350,000

Produce an 'sf_gap_analysis' field with:
- stage_gap: { direction, interpretation (1-2 sentences) }
- forecast_gap: { direction, interpretation (1-2 sentences) }
- overall_gap_assessment: 2-3 sentences for the VP Sales
```

### SynthesisOutput Model Addition

```python
class SFGapAnalysis(BaseModel):
    """Agent 10's interpretation of SIS vs SF gaps."""
    stage_gap_direction: str  # "Aligned" / "SF-ahead" / "SIS-ahead"
    stage_gap_interpretation: str  # 1-2 sentences
    forecast_gap_direction: str  # "Aligned" / "SF-more-optimistic" / "SIS-more-optimistic"
    forecast_gap_interpretation: str  # 1-2 sentences
    overall_gap_assessment: str  # 2-3 sentences for the manager
```

New optional field on `SynthesisOutput`:
```python
sf_gap_analysis: Optional[SFGapAnalysis] = None
```

### Deterministic Gap Computation

After Agent 10, code computes:
- `stage_gap_direction`: Compare `inferred_stage` vs `sf_stage_at_run`
- `stage_gap_magnitude`: `abs(inferred_stage - sf_stage_at_run)`
- `forecast_gap_direction`: Rank Commit(4) > Realistic(3) > Upside(2) > At Risk(1), compare

---

## Gap Display

### Deal Detail Page — SF Gap Card

New card below the assessment card:

```
┌────────────────────────────────────────────────────────────┐
│  Salesforce Gap Analysis                                    │
│  SF indication at day of last analysis                      │
├────────────────────────────────────────────────────────────┤
│  Stage    SIS: Scope (3)    SF: Negotiate (5)   SF +2      │
│  Forecast AI: Upside        SF: Commit           SF > AI   │
│  Close Q  Q2 2026                                          │
│  CP Est.  $350,000                                         │
├────────────────────────────────────────────────────────────┤
│  "SIS inferred Stage 3 (Scope) while SF shows Stage 5     │
│   (Negotiate). This 2-stage gap suggests the rep may have  │
│   advanced the deal in SF before transcript evidence       │
│   supports it. SIS forecast is Upside vs SF Commit — the   │
│   manager should validate whether commitment-level evidence│
│   exists beyond what was discussed on recorded calls."     │
└────────────────────────────────────────────────────────────┘
```

### Pipeline Dashboard — Gap Indicator Column

New "SF Gap" column using **directional arrows with text** (no colors):
- `=` — Aligned (stage and forecast match)
- `SF +2` — SF is 2 stages ahead
- `SIS +1` — SIS is 1 stage ahead
- `SF > AI` / `AI > SF` — forecast gap direction
- Tooltip shows full breakdown on hover

---

## Change Summary

| Layer | What | Type |
|-------|------|------|
| Backend | `sis/db/models.py` — rename mrr_estimate→cp_estimate, add SF cols to Account + DealAssessment | Modified |
| Backend | `sis/api/schemas/accounts.py` — update AccountCreate/Summary/Detail for SF fields + rename | Modified |
| Backend | `sis/api/schemas/analyses.py` — update BatchItemRequest with SF fields | Modified |
| Backend | `sis/services/analysis_service.py` — snapshot SF fields, compute deterministic gap | Modified |
| Backend | `sis/agents/synthesis.py` — add sf_data param, Step 5 prompt, SFGapAnalysis model | Modified |
| Backend | `sis/orchestrator/pipeline.py` — pass sf_data to synthesis build_call | Modified |
| Backend | `sis/api/routes/analyses.py` — pass SF fields through batch worker | Modified |
| Frontend | `frontend/src/app/upload/page.tsx` — SF fields on single + batch upload | Modified |
| Frontend | `frontend/src/app/deals/[id]/page.tsx` — SF Gap card | Modified |
| Frontend | `frontend/src/app/pipeline/page.tsx` (or equivalent) — gap column | Modified |
| Frontend | `frontend/src/lib/api-types.ts` — SF field types | Modified |

**Unchanged:** Agents 1-9 prompts, agent runner, progress store, SSE endpoints, Google Drive service.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Agent 10 anchoring on SF data despite Step 5 ordering | Explicit instruction: "Do NOT revise Steps 1-4." Prompt placement after all agent outputs. |
| mrr_estimate rename breaks existing data | SQLite column rename via ALTER TABLE or application-layer alias. POC DB can be recreated. |
| SF fields empty (user skips) | All fields nullable. Gap card hidden when no SF data. Agent 10 Step 5 skipped when no sf_data. |
| Batch table too wide with 4 new columns | Compact dropdowns, abbreviated labels (Stg, Fct, Q, $). Consider horizontal scroll. |
| Cost increase from Agent 10 Step 5 | ~500 extra output tokens per run ≈ $0.01. Negligible. |
