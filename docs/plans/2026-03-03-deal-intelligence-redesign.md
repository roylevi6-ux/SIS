# Product Design Brief: Deal Intelligence Section Redesign

**Date**: 2026-03-03
**Author**: Product Manager
**Status**: Draft -- Awaiting User Review
**Priority**: P0 -- Core Product Experience

---

## 1. Problem Statement

The Deal Intelligence section is the most important screen in SIS. It synthesizes output from 10 AI agents into a deal assessment that VP Sales and Team Leads use to make pipeline decisions. Today, it fails both audiences:

**For VPs**: The page dumps the same dense layout on a VP reviewing their 30th deal of the week as it does on a TL deep-diving one deal. A VP cannot answer "is this deal real?" in 30 seconds. The `manager_brief` -- purpose-built for VPs by Agent 10 -- is generated but never reaches the UI. The "Leadership Summary" tab is a fake: it auto-truncates the TL's deal memo to 3 sentences, losing the VP-specific framing entirely.

**For TLs**: The deal memo and manager actions panel are separate cards with no narrative thread between them. Per-agent `manager_insight` fields (up to 9 of them) are hidden behind two levels of click -- first expand the Manager Actions panel, then expand each individual agent row. The coaching moments are buried.

**For both**: There is no role-aware information hierarchy. Both users see identical default content in identical order. The system knows the user's role (`vp`, `team_lead`, etc. via `usePermissions()`) but does nothing with that knowledge on this page.

---

## 2. User Stories

### VP Sales (Reviews 20-40 deals/week)

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| VP-1 | As a VP, when I click into a deal, I want to see a verdict in under 10 seconds | The `manager_brief` (not truncated deal memo) is the first thing visible above the fold, with health score, forecast category, and momentum direction in a single glanceable strip |
| VP-2 | As a VP, I want to know "should I intervene?" without reading paragraphs | A single "attention required" visual signal (color/icon) derived from: At Risk forecast, declining momentum, high-severity risks, or divergence flag |
| VP-3 | As a VP, I want to understand what changed since the last analysis | The `WhatChangedCard` should appear immediately after the brief, showing deltas in health, stage, forecast, momentum |
| VP-4 | As a VP, I want to drill deeper ONLY when the brief raises a flag | Progressive disclosure: brief visible by default, full deal memo and agent detail available on demand, not competing for attention |
| VP-5 | As a VP, I want this deal's context to help me in the portfolio review | The brief's language should map to pipeline review language: forecast confidence, risk level, required action, timeline |

### Team Lead (Owns 6-10 deals, coaches reps)

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| TL-1 | As a TL, when I click into a deal, I want to prepare for a rep 1:1 in under 3 minutes | The full deal memo is prominent, structured with clear section headers (People, Commercial, Momentum, etc.), and reads as a coherent narrative |
| TL-2 | As a TL, I want to find coaching moments without reading every agent output | Per-agent `manager_insight` fields are synthesized into a "coaching brief" -- grouped by theme (relationship gaps, commercial gaps, execution gaps), not by agent number |
| TL-3 | As a TL, I want to see what questions to ask my rep | Recommended actions filtered to show `owner: AE` or `owner: SE` actions prominently, since those are the ones the TL will assign |
| TL-4 | As a TL, I want to understand agent disagreements | Contradictions surfaced inline where relevant, not in a separate "Contradictions" card that nobody clicks |
| TL-5 | As a TL, I want to track deal trajectory over time | Deal timeline and "what changed" are visible and connected to the narrative ("Health dropped 12 points because champion went silent") |

---

## 3. Information Architecture

### 3.1 Design Principle: One Page, Role-Aware Defaults

**Decision**: Single page with role-adaptive layout, NOT two separate views.

**Rationale**: A VP sometimes needs TL-depth. A TL sometimes wants the VP-level quick read. Two completely separate views would force users to switch contexts and create a maintenance burden. Instead, the same components render in a different default order and expansion state based on role.

### 3.2 Page Structure (Both Roles)

```
+------------------------------------------------------------------+
|  HEADER (shared)                                                  |
|  Account Name / AE / TL / Team / CP Est / Deal Type               |
|  Status Strip: Health [62] | Momentum [Declining] | Stage [4]     |
|               AI Forecast [Upside] | SF Forecast [Realistic]      |
|               Confidence [72%] | [Divergence badge if applicable] |
+------------------------------------------------------------------+
|                                                                    |
|  DEAL INTELLIGENCE SECTION                                         |
|  (role-adaptive content below)                                     |
|                                                                    |
+------------------------------------------------------------------+
```

### 3.3 VP Default Layout (role === 'vp' || role === 'gm' || role === 'admin')

The VP layout optimizes for SCAN then DRILL. The entire "answer" should be above the fold on a 1080p monitor (~700px viewport below the header).

```
+------------------------------------------------------------------+
| [1] VP BRIEF                                     [Attention flag] |
|     manager_brief text (3-5 sentences)                            |
|     "This deal needs [X]. The forecast risk is [Y].              |
|      This week: [Z]."                                             |
+------------------------------------------------------------------+
| [2] WHAT CHANGED (delta badges inline)                            |
|     Health: 74 -> 62 (-12) | Stage: 4 (same) | Forecast: ...     |
+------------------------------------------------------------------+
| [3] KEY METRICS ROW                                               |
|  +-------------+  +-------------+  +-------------+                |
|  | Top Risk    |  | Top Action  |  | Key Unknown |                |
|  | [Critical]  |  | [P0, AE]   |  | EB not seen |                |
|  | Champion... |  | Schedule... |  | since Q3    |                |
|  +-------------+  +-------------+  +-------------+                |
+------------------------------------------------------------------+
|                                                                    |
| [4] FULL DEAL MEMO              [collapsed by default]            |
|     > Click to expand                                              |
+------------------------------------------------------------------+
| [5] HEALTH BREAKDOWN            [collapsed by default]            |
+------------------------------------------------------------------+
| [6] ACTIONS & RISKS             [collapsed by default]            |
+------------------------------------------------------------------+
| [7] AGENT ANALYSES              [collapsed by default]            |
+------------------------------------------------------------------+
```

**Key design decisions for VP:**
- `manager_brief` is the HERO content -- no tabs, no collapse, always visible
- "What Changed" is second because the VP is scanning across deals and needs to know "did anything move?"
- "Key Metrics Row" extracts the #1 risk, #1 action, and #1 unknown as scannable cards -- the VP does not need all 8 risks, just the most critical one
- Everything below the fold is collapsed -- the VP ONLY expands if the brief raises concern
- The Deal Memo tab structure is removed entirely; if expanded, it shows the full memo

### 3.4 TL Default Layout (role === 'team_lead' || role === 'ic')

The TL layout optimizes for PREPARE then COACH. The narrative is primary. Coaching signals are woven in, not siloed.

```
+------------------------------------------------------------------+
| [1] DEAL NARRATIVE                                                |
|     The Bottom Line (paragraph 1 from deal_memo, bold)            |
|     ------------------------------------------------              |
|     Deal Situation & Stage                                        |
|     People & Power                                                |
|     Commercial & Competitive                                      |
|     Why Now?                                                       |
|     Momentum & Structural Advancement                             |
|     Technical & Integration                                       |
|     Red Flags & Silence Signals                                   |
|     (Expansion Dynamics if applicable)                             |
|                                                                    |
|     Each section has a left-margin icon/color indicating:          |
|     - green: strength area                                        |
|     - amber: watch area                                            |
|     - red: concern area                                            |
|     (derived from health_breakdown component scores)              |
+------------------------------------------------------------------+
| [2] KEY FINDINGS BY DIMENSION                                     |
|     Per-agent manager_insights presented as practical findings     |
|                                                                    |
|     [Relationship] Champion went dark after pricing call...       |
|     [Commercial] No budget discussion in last 3 calls...          |
|     [Momentum] Meeting cadence dropped from weekly to biweekly... |
|     [Economic Buyer] EB hasn't appeared since discovery...        |
|     [Competitive] Competitor mentioned by prospect in call 4...   |
+------------------------------------------------------------------+
| [3] WHAT CHANGED                                                  |
|     Delta card (same as VP but expanded by default)               |
+------------------------------------------------------------------+
| [4] REP ACTION PLAN                                               |
|     Recommended actions filtered/sorted:                          |
|     - P0 first, then P1, then P2                                  |
|     - Actions owned by AE/SE highlighted (these are the ones     |
|       TL will discuss in 1:1)                                     |
|     - Manager-owned actions shown separately                      |
+------------------------------------------------------------------+
| [5] HEALTH BREAKDOWN            [expanded by default]             |
+------------------------------------------------------------------+
| [6] RISKS & SIGNALS             [expanded by default]             |
+------------------------------------------------------------------+
| [7] SF GAP ANALYSIS             [if SF data exists]              |
+------------------------------------------------------------------+
| [8] AGENT DEEP DIVES            [collapsed by default]           |
+------------------------------------------------------------------+
```

**Key design decisions for TL:**
- The full deal memo is the HERO -- no tabs, no truncation, properly formatted with section headers
- "Key Findings by Dimension" replaces the old nested-collapsible Manager Actions panel -- per-agent insights presented as practical sales findings in a flat, scannable list
- The "Bottom Line" paragraph (first paragraph of deal_memo) gets visual emphasis -- bold, slightly larger, bordered
- Health breakdown is expanded by default because TLs use it to understand WHERE the deal is weak
- Recommended actions are reframed as "Rep Action Plan" and sorted by who owns them
- No coaching framing -- everything is about "what you need to know to win this deal"

---

## 4. Data-to-UI Mapping

### 4.1 Data Source Inventory

| Data Field | Source | Current Location | Storage Status |
|-----------|--------|-----------------|---------------|
| `manager_brief` | Agent 10 `SynthesisOutput.manager_brief` | NOT in UI | NOT in DB -- generated but discarded during persistence |
| `deal_memo` | Agent 10 `SynthesisOutput.deal_memo` | `DealMemo` component (tabs) | `deal_assessments.deal_memo` column |
| Per-agent `manager_insight` | Agents 1-9 findings dict | `ManagerActionsPanel` (nested collapsibles) | `agent_analyses.findings` JSON |
| `health_score` + breakdown | Agent 10 | Header strip + `HealthBreakdown` | DB columns |
| `momentum_direction` + trend | Agent 10 | Header strip | DB columns |
| `forecast_category` + rationale | Agent 10 | Header strip + `ForecastRationale` card | DB columns |
| `top_risks` | Agent 10 | `SignalsList` card | DB JSON column |
| `top_positive_signals` | Agent 10 | `SignalsList` card | DB JSON column |
| `recommended_actions` | Agent 10 | `ActionsList` card | DB JSON column |
| `contradiction_map` | Agent 10 | `SignalsList` card | DB JSON column |
| `key_unknowns` | Agent 10 | Standalone card | DB JSON column |
| `sf_gap_analysis` | Agent 10 | `SFGapCard` | DB columns |
| Assessment deltas | Computed | `WhatChangedCard` / `DeltaBadge` | Computed at query time |

### 4.2 Mapping: Data to VP View

| VP Widget | Primary Data | Secondary Data | Why Here |
|-----------|-------------|---------------|---------|
| VP Brief (hero) | `manager_brief` | None | This IS the VP's answer. Purpose-built for them by Agent 10. |
| What Changed | Assessment deltas (health, stage, forecast, momentum) | None | VP scans 30 deals -- needs to spot movers |
| Key Metrics Row: Top Risk | `top_risks[0]` (highest severity) | `top_risks[0].mitigation` | One risk to know, not eight |
| Key Metrics Row: Top Action | `recommended_actions` filtered to `priority: P0` | `owner` field | What should happen THIS WEEK |
| Key Metrics Row: Key Unknown | `key_unknowns[0]` | None | What could invalidate the forecast |
| Full Deal Memo (collapsed) | `deal_memo` | None | Available on demand for VP who wants depth |
| Health Breakdown (collapsed) | `health_breakdown` | Component scores | Available on demand |
| Agent Analyses (collapsed) | All agent cards | Per-agent findings | Rarely used by VP |

### 4.3 Mapping: Data to TL View

| TL Widget | Primary Data | Secondary Data | Why Here |
|-----------|-------------|---------------|---------|
| Deal Narrative (hero) | `deal_memo` (full, section-parsed) | `health_breakdown` component scores (for section-level health indicators) | The TL needs the full story to coach effectively |
| Key Findings | Per-agent `manager_insight` (by dimension) | Agent names for attribution | Practical sales process findings -- what you need to know to win |
| What Changed | Assessment deltas | Previous run values | Context for "is this getting better or worse?" |
| Rep Action Plan | `recommended_actions` sorted by priority, grouped by owner | `rationale` field | Directly actionable in rep 1:1 |
| Health Breakdown | `health_breakdown` | Component rationales | Shows WHERE the deal is weak |
| Risks & Signals | `top_risks` + `top_positive_signals` | Severity, supporting agents | Full picture for coaching depth |
| SF Gap Analysis | SF gap fields | Agent 10 interpretation | Shows if rep's SF data matches reality |
| Agent Deep Dives (collapsed) | Per-agent full findings | Evidence, data gaps | Reference material |

---

## 5. New Component Architecture

### 5.1 Components to CREATE

| Component | Purpose | Props |
|-----------|---------|-------|
| `VPBrief` | Hero card for VP view. Renders `manager_brief` with attention flag. | `{ brief: string; attentionLevel: 'none' | 'watch' | 'act' }` |
| `KeyMetricsRow` | Three scannable cards: top risk, top action, key unknown. | `{ topRisk: RiskEntry; topAction: RecommendedAction; keyUnknown: string }` |
| `DealNarrative` | Hero component for TL view. Parses deal_memo into sections with health indicators. | `{ memo: string; sections: DealMemoSection[] }` |
| `KeyFindings` | Per-agent key findings presented as practical sales process findings by dimension. Flat list with agent badges — no nested collapsibles. | `{ agents: AgentAnalysis[] }` |
| `RepActionPlan` | Priority-sorted, owner-grouped actions. | `{ actions: RecommendedAction[] }` |
| `RoleAwareDealIntelligence` | Orchestrator that reads user role and renders VP or TL layout. | `{ role: Role; assessment: Assessment; agents: AgentAnalysis[] }` |

### 5.2 Components to MODIFY

| Component | Change |
|-----------|--------|
| `DealMemo` | **Deprecate.** Replace with `VPBrief` (VP) and `DealNarrative` (TL). The tab-based design is removed. |
| `ManagerActionsPanel` | **Deprecate.** Replace with `KeyFindings` (TL) and extract into `KeyMetricsRow` (VP). The nested collapsibles are too many clicks. |
| `ActionsList` | **Modify.** Add owner-based grouping and priority sorting. Repackage as `RepActionPlan` for TL view. |
| Deal detail page (`/deals/[id]/page.tsx`) | **Major refactor.** The `renderWidget` switch statement becomes role-aware. VP and TL get different widget lists with different default states. |

### 5.3 Components UNCHANGED

`HealthBreakdown`, `AgentCard`, `SFGapCard`, `WhatChangedCard`, `DealTimeline`, `CallTimeline`, `DeltaBadge`, status strip in header.

---

## 6. Deal Memo Parsing Strategy

Agent 10 outputs the deal memo as a single string with paragraph breaks. The paragraphs follow a defined structure (per the system prompt): Bottom Line, Deal Situation, People & Power, Commercial & Competitive, Why Now, Momentum, Technical, Red Flags, (Expansion Dynamics).

**For the TL's `DealNarrative` component**, we need to parse this into sections. Two approaches:

### Option A: Parse the string (fragile, no prompt change)
Split on double-newline and map paragraphs positionally: paragraph 1 = Bottom Line, paragraph 2 = Deal Situation, etc. Problem: Agent 10 occasionally merges or reorders paragraphs. Positional parsing will break.

### Option B: Structured output from Agent 10 (robust, requires prompt change) -- RECOMMENDED
Change Agent 10's output schema to return `deal_memo_sections` as a structured array alongside the flat `deal_memo` string. Each section has a `title`, `content`, and `health_signal` (green/amber/red). The flat string remains for backward compatibility.

**Recommendation**: Option B. The cost is one prompt change and one schema field addition. The benefit is reliable section-level rendering and health-per-section indicators that are impossible to compute client-side.

---

## 7. Agent 10 Prompt Change Requirements

These are changes needed in `sis/agents/synthesis.py` (both `SYSTEM_PROMPT` and `SynthesisOutput` Pydantic model) to support the redesigned UI.

### 7.1 Add `deal_memo_sections` structured output

**New Pydantic model:**

```python
class DealMemoSection(BaseModel):
    """One section of the structured deal memo."""
    section_id: str = Field(description="Stable ID: bottom_line, deal_situation, people_power, commercial_competitive, why_now, momentum, technical, red_flags, expansion_dynamics")
    title: str = Field(description="Section display title")
    content: str = Field(description="The section content (1-2 paragraphs)")
    health_signal: str = Field(description="green (strength), amber (watch), red (concern) -- based on related health score components")
    related_components: list[str] = Field(description="Health breakdown component names this section relates to")
```

**Add to `SynthesisOutput`:**
```python
deal_memo_sections: list[DealMemoSection] = Field(
    description="Structured deal memo broken into labeled sections with health signals. "
    "Must cover: bottom_line, deal_situation, people_power, commercial_competitive, "
    "why_now, momentum, technical, red_flags. Add expansion_dynamics for expansion deals."
)
```

**Prompt addition to Step 2:**
```
In addition to the flat deal_memo string, populate deal_memo_sections with each paragraph as a separate section object. For each section, assign a health_signal:
- "green" if the related health components score >= 70% of their max
- "amber" if 45-69%
- "red" if < 45%
Map sections to components: people_power -> champion_strength + multithreading, commercial_competitive -> buyer_validated_pain + competitive_position, etc.
```

### 7.2 `coaching_themes` — REMOVED

~~Coaching themes have been removed from the design.~~ The user decided that TLs don't want coaching — they want practical information to win the deal. The TL view instead shows **Key Findings by Dimension**: per-agent `manager_insight` fields presented as direct, practical sales process findings grouped by agent dimension (Relationship, Commercial, Momentum, etc.). This requires NO new Agent 10 output — the data already exists in per-agent findings. The frontend simply presents it better (no nested collapsibles, flat list with dimension badges).

### 7.3 Rewrite `manager_brief` prompt — Blunt Advisor Tone

The `manager_brief` must NOT rehash health scores, forecast categories, or dashboard metrics. Those are already visible in the status strip. Instead, it should read like a **trusted outsider sales executive** who sat in on every call and is giving you the real talk.

**Replace the existing Step 2b prompt instruction with:**
```
### Step 2b: MANAGER BRIEF
Write the manager_brief as if you are a trusted, experienced sales executive who has listened to every call on this deal and is now briefing the VP/TL in the hallway. Your tone is direct, practical, and blunt.

Rules:
- DO NOT mention health scores, forecast categories, momentum labels, or any metric the dashboard already shows
- DO focus on: real sales process risks, oversights, delays, silences, and positive signals
- Call out specific people, specific meetings, specific timelines — be concrete
- Include at least one positive signal or bright spot if it exists
- Write 3-5 sentences maximum
- Use the present tense and address the reader directly

Example tone: "Champion went dark after the pricing call two weeks ago — that's your biggest risk right now. The EB hasn't been on a call since discovery, and nobody's pushing for that meeting. If you don't force the EB conversation this week, this deal slides into Q3. Bright spot: procurement joined the last call unprompted — someone internally is moving this forward even if your champion isn't."
```

### 7.4 Add `attention_level` field

Add a field so the VP Brief component can render an appropriate visual signal.

**Add to `SynthesisOutput`:**
```python
attention_level: str = Field(
    default="none",
    description="VP attention signal: 'act' (deal requires VP intervention this week), "
    "'watch' (emerging risk, monitor), 'none' (tracking to forecast, no VP action needed)"
)
```

**Prompt addition (append to Step 2b):**
```
Also set attention_level based on the sales process reality you just described:
- "act": Deal requires VP intervention this week — something is broken, stuck, or at risk of dying
- "watch": Emerging concern that doesn't need VP action yet but could escalate
- "none": Deal is progressing, no intervention needed
```

### 7.5 Summary of Prompt Changes

| Change | Impact on Token Budget | Risk |
|--------|----------------------|------|
| `deal_memo_sections` (structured version of existing memo) | ~200 extra output tokens (section metadata) | Low -- same content, just structured |
| `manager_brief` rewrite (blunt advisor tone) | ~0 extra tokens (same length, better quality) | Low -- tone change only |
| `attention_level` (single string) | ~5 tokens | None |
| Total additional output | ~200 tokens on 12,000 budget | Comfortable within budget |

---

## 8. Database Schema Changes

`manager_brief` is generated by Agent 10 but never persisted. The following columns need to be added to `deal_assessments`:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `manager_brief` | Text | Yes | VP-targeted blunt advisor brief from Agent 10 |
| `attention_level` | Text | Yes | "act" / "watch" / "none" |
| `deal_memo_sections` | Text (JSON) | Yes | Structured sections with health signals |

**Migration**: Add columns as nullable. Backfill from existing `deal_memo` and per-agent `manager_insight` data is possible but lower priority -- new runs will populate automatically.

**API change**: The `AccountDetail` response schema must include these new fields in the assessment object.

---

## 9. Attention Flag Logic

The `attention_level` field from Agent 10 drives the VP Brief's visual signal. Fallback logic (when `attention_level` is null -- pre-migration data):

```
if (forecast === 'At Risk') -> act
else if (momentum === 'Declining' || divergence_flag) -> watch
else -> none
```

Visual treatment:

| Level | Color | Icon | Border |
|-------|-------|------|--------|
| `act` | Red | AlertTriangle | `border-red-500` with subtle red background |
| `watch` | Amber | Eye | `border-amber-400` with subtle amber background |
| `none` | Default | None | Standard card border |

---

## 10. Interaction Model

### 10.1 VP Flow

1. **VP arrives at deal page** (from pipeline table click)
2. **Eyes land on VP Brief** -- 3-5 sentences with attention flag color immediately visible
3. **Scans What Changed** -- did health/stage/forecast move?
4. **Scans Key Metrics Row** -- one risk, one action, one unknown
5. **Decision point**: "Do I need to go deeper?"
   - NO: back to pipeline (Back to Pipeline link)
   - YES: expand deal memo OR click into specific section

**Time to decision: 15-30 seconds** (3 sections above the fold, all pre-rendered)

### 10.2 TL Flow

1. **TL arrives at deal page** (from pipeline or bookmarked)
2. **Reads Bottom Line** (visually distinct first paragraph of deal narrative)
3. **Reads full narrative** -- scanning section health indicators (green/amber/red margin)
4. **Reads Key Findings** -- per-agent practical sales insights by dimension
5. **Checks What Changed** -- context for the 1:1 conversation
6. **Reviews Rep Action Plan** -- what to assign in the 1:1
7. **Optionally**: dives into health breakdown, risks, agent deep dives

**Time to prepare for 1:1: 2-3 minutes** (narrative + coaching brief + action plan)

---

## 11. Progressive Disclosure Layers

| Layer | VP Default | TL Default | Content |
|-------|-----------|-----------|---------|
| L1: The Answer | **Visible** | *Visible (Bottom Line)* | VP Brief / Bottom Line paragraph |
| L2: The Context | **Visible** | **Visible** | What Changed + Key Metrics (VP) / Full narrative + Coaching Brief (TL) |
| L3: The Detail | **Collapsed** | **Expanded** | Health Breakdown, Actions/Risks, SF Gap |
| L4: The Evidence | **Collapsed** | **Collapsed** | Per-agent analyses, evidence quotes, data gaps |

---

## 12. Cross-Deal Portfolio Connection

This brief does NOT redesign the pipeline page. But the deal-level design must connect cleanly:

### 12.1 Pipeline Table Enhancement (future)
- Add `attention_level` as a column/icon in the pipeline DataTable so VPs can sort/filter by "needs attention"
- Add `manager_brief` first sentence as a hover tooltip on account name in the pipeline table

### 12.2 Data Contract
- The `attention_level` field should be queryable at the API level (filter parameter on `/api/accounts`)
- The pipeline page should be able to request a lightweight summary (brief + attention_level + deltas) without fetching full assessment data

### 12.3 Navigation Pattern
- VP clicks row in pipeline table -> deal page opens with VP Brief already answered
- VP uses keyboard nav (j/k or arrow keys) to move between deals in the pipeline (future enhancement -- requires deal-level URL navigation)

---

## 13. Edge Cases

| Edge Case | Handling |
|-----------|---------|
| `manager_brief` is empty (pre-migration runs) | Fall back to `truncateToSummary(deal_memo)` with a subtle "Generated summary -- re-run analysis for full VP brief" note |
| Per-agent `manager_insight` is empty | KeyFindings renders empty state, no findings shown |
| `deal_memo_sections` is empty | Render `deal_memo` as unsectioned text (current behavior) |
| User is IC role | Show TL layout (ICs preparing for their own deals see the same depth) |
| User is Admin/GM role | Show VP layout (admin/GM are operating at portfolio level) |
| No assessment at all | Existing `NoAssessmentState` component, unchanged |
| Only 1-2 agents returned data | KeyFindings shows only those agents' insights. Sparse but still useful. |

---

## 14. Implementation Phases

### Phase 1: Data Pipeline (Backend, ~2 days)
1. Add `manager_brief`, `attention_level`, `deal_memo_sections` columns to `deal_assessments` (Alembic migration)
2. Update `analysis_service.py` to persist these fields from Agent 10 output
3. Update API response schema to include new fields
4. Update Agent 10 prompt with changes from Section 7

### Phase 2: VP Brief Component (Frontend, ~1 day)
1. Create `VPBrief` component
2. Create `KeyMetricsRow` component
3. Wire up attention flag with fallback logic

### Phase 3: TL Narrative Components (Frontend, ~2 days)
1. Create `DealNarrative` with section parsing and health indicators
2. Create `KeyFindings` -- flat list of per-agent manager_insights with dimension badges
3. Create `RepActionPlan` with owner/priority sorting

### Phase 4: Role-Aware Layout (Frontend, ~1 day)
1. Create `RoleAwareDealIntelligence` orchestrator
2. Refactor deal detail page to use role-based widget ordering
3. Update default collapsed/expanded states per role

### Phase 5: Validation & Polish (~1 day)
1. Test with real deal data across both roles
2. Verify fallback behavior for pre-migration data
3. Tune Agent 10 prompt based on output quality
4. Desktop + tablet responsive check

**Total estimated effort: 7 days**

---

## 15. Open Questions for User Decision

Before proceeding to implementation, I need decisions on the following:

### Q1: Role Toggle Override
Should users be able to toggle between VP and TL views? For example, a VP who wants TL depth could click a toggle to see the full TL layout. Or do we trust progressive disclosure (expanding collapsed sections) to handle this?

**My recommendation**: No toggle. Progressive disclosure handles it. A VP who wants the deal memo just expands it. Adding a toggle introduces UI complexity and suggests the views are "different pages" when they should feel like the same page with different defaults.

### Q2: TL Key Findings Presentation — DECIDED
**Decision**: Per-agent `manager_insight` fields presented as a flat list of practical sales findings by dimension, with agent badges. No coaching framing, no nested collapsibles. The user decided: "no need for coaching at all. let's focus on the information needed to win this deal." This requires no new Agent 10 output — the data already exists in per-agent findings.

### Q3: Backfill Strategy
Should we re-run all 14 existing analyses to populate the new fields? Or accept that old runs show fallback behavior and only new runs get the full experience?

**My recommendation**: Accept fallback for now. Re-running 14 analyses costs real money (Opus model) and delays launch. The fallback UX is functional -- it just lacks the polish of purpose-built fields.

### Q4: Attention Level in Pipeline Table
Should Phase 1 include adding `attention_level` as a column in the pipeline DataTable? This creates immediate value for the VP even before they click into a deal.

**My recommendation**: Yes, include it. It is low-effort (one column addition to the DataTable) and high-impact (VP can sort by "needs attention" without clicking into each deal).

### Q5: Agent 10 Token Budget
The additional structured outputs (deal_memo_sections, coaching_themes, attention_level) add ~500 tokens to Agent 10's output. Current budget is 8,000 tokens. Is this acceptable, or should we increase the budget?

**My recommendation**: 8,000 is sufficient. The additions are ~6% of the budget. Monitor first runs and increase only if truncation occurs.

---

## 16. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|---------------|
| VP time to deal decision | Unknown (no tracking) | < 30 seconds | Time from page load to next navigation (back to pipeline or expand action) |
| TL 1:1 prep completeness | Anecdotal | TL reads brief + coaching themes + action plan | Feature adoption tracking on section views |
| VP section expansion rate | N/A (no collapsed sections) | < 30% of visits result in expanding deal memo | Expansion click tracking |
| "Leadership Summary" tab usage | Low (it is a truncated copy) | N/A (tab eliminated) | Remove dead code |
| manager_brief render rate | 0% (not in UI) | 100% of new runs | Field presence check |

---

## 17. Files to Change

| File | Change Type | Notes |
|------|------------|-------|
| `/Users/roylevierez/Documents/Sales/SIS/sis/agents/synthesis.py` | Modify | Add Pydantic models + prompt changes (Section 7) |
| `/Users/roylevierez/Documents/Sales/SIS/sis/db/models.py` | Modify | Add 4 columns to `DealAssessment` |
| `/Users/roylevierez/Documents/Sales/SIS/sis/services/analysis_service.py` | Modify | Persist new fields |
| `/Users/roylevierez/Documents/Sales/SIS/sis/api/schemas/accounts.py` | Modify | Add fields to response schema |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/app/deals/[id]/page.tsx` | Major refactor | Role-aware layout, new widget orchestration |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/deal-memo.tsx` | Deprecate | Replaced by VPBrief + DealNarrative |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/manager-actions-panel.tsx` | Deprecate | Replaced by CoachingBrief |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/vp-brief.tsx` | Create | New VP hero component |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/key-metrics-row.tsx` | Create | New VP scannable metrics |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/deal-narrative.tsx` | Create | New TL hero component |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/key-findings.tsx` | Create | Per-agent insights by dimension (replaces coaching-brief) |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/rep-action-plan.tsx` | Create | New TL action plan |
| `/Users/roylevierez/Documents/Sales/SIS/frontend/src/components/role-aware-deal-intelligence.tsx` | Create | Layout orchestrator |
| Alembic migration | Create | New migration for 4 columns |

---

*This brief is ready for review. The five open questions in Section 15 need answers before implementation begins.*
