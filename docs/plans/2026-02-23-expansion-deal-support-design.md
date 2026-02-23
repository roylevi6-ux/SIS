# Design: Expansion Deal Support (Upsell / Cross-Sell)

**Date:** 2026-02-23
**Status:** Draft — Pending VP Sales approval
**Authors:** VP Sales + AI Agent Team (Data & AI Lead, Dev Lead)

---

## 1. Problem Statement

A significant share of Riskified's sales pipeline consists of expansion deals with existing customers — upsells, cross-sells, or both. The current SIS 10-agent pipeline is built exclusively for new-logo (new customer acquisition) analysis. Every agent prompt, stage model, health score component, calibration threshold, and guardrail assumes a greenfield sales cycle.

**Impact:** Expansion deals are systematically under-scored (~35-55/100) and misclassified as "At Risk" or "Pipeline" even when they are near-certain closes. Specific failure modes:

- **Stage misclassification:** An existing customer expanding to new markets gets staged as "SQL" (Stage 1) because the agent detects use-case discussion, when the deal should be in Commercial (Stage 3) or later.
- **Health score deflation:** Scores are penalized for missing "full buying committee" (fewer stakeholders needed for expansion), missing "EB engagement" (CFO already approved Riskified), missing "MSP" (expansion uses amendment), and missing "technical readiness" (already integrated).
- **Irrelevant risks surfaced:** Agents flag "integration complexity" (irrelevant for upsell), "no-decision risk" (customer already chose Riskified), and "unresolved commercial objections" (pricing predetermined by existing contract).
- **Missing account health context:** A client who is unhappy with Riskified's current performance will not expand, but this sentiment is invisible to agents built for new-logo evaluation. Cost pushback, discount demands, and performance complaints on existing product bleed into expansion calls but are not tracked.

---

## 2. Deal Type Taxonomy

Four deal types, tagged manually at account upload and validated by AI from transcript analysis:

| Deal Type | Code | Description |
|-----------|------|-------------|
| **New Logo** | `new_logo` | New customer acquisition. No prior Riskified relationship. |
| **Expansion — Upsell** | `expansion_upsell` | Existing customer, same product, more volume/markets/scope. Minimal or zero integration effort. |
| **Expansion — Cross-Sell** | `expansion_cross_sell` | Existing customer, new product line. May require additional API integration. |
| **Expansion — Both** | `expansion_both` | Existing customer, upsell + cross-sell in the same deal. Integration effort depends on cross-sell component. |

**Pipeline routing:** `new_logo` runs the existing pipeline. All three `expansion_*` types run the expansion pipeline (with Agent 0E). Cross-sell integration expectations are handled within agent prompts via the deal type context — Agents 5 (Technical), 6 (Integration), and 7 (Onboarding) adjust their analysis based on whether the deal includes a cross-sell component.

**Detection approach:**
1. **Manual tag at upload:** VP/TL selects deal type when creating an account. Required field.
2. **AI validation:** A lightweight pre-pipeline classifier (~200 tokens) reads the first transcript and infers deal type. If it disagrees with the manual tag, the deal is flagged with `deal_type_mismatch: true`. Manual tag takes precedence — AI validates, does not override.

---

## 3. Expansion Stage Model

Same 7-stage numbering as new-logo (preserves stage_relevance matrix, dashboard queries, health-score-by-stage weighting), but with different descriptions, expectations, and key players.

### New-Logo Stages (existing, unchanged)

| # | Stage | What Happens | Typical Duration | Key Players |
|---|-------|-------------|------------------|-------------|
| 1 | **SQL** | BD shaped use case, metrics provided, NDA signed → handoff to AE | Months to years (BD side) | BD + 1-2 prospect contacts |
| 2 | **Metrics Validation** | AE validates prospect's data (chargeback rates, fraud BPS, volumes) | 2-6 weeks | AE + prospect ops/risk |
| 3 | **Commercial Build & Present** | AE builds pricing/ROI model, presents to champion/influencer/DM | 4-12 weeks | AE + champion + DM |
| 4 | **Stakeholder Alignment** | AE + champion sell internally across departments, secure budget & approvals | 2-6 months | AE + champion + CFO, VP Risk, CTO, Procurement |
| 5 | **Legal** | MSA negotiation and execution | 4-12 weeks | Legal teams (both sides) |
| 6 | **Integration** | Technical integration of Riskified into merchant's stack | 4-12 weeks | AE + SE + merchant tech team |
| 7 | **Onboarding** | Model optimization iterations until performance targets met → Go-Live = Closed Won | 4-12 weeks | AE + data/ML team + merchant ops |

### Expansion Stages (new)

| # | Stage | What Happens | Differs from New-Logo | Typical Duration | Key Players |
|---|-------|-------------|----------------------|------------------|-------------|
| 1 | **SQL** | Account Manager identifies expansion opportunity, shapes use case with existing customer | AM-driven (not BDR). Customer already known. Opportunity may emerge from QBRs, usage patterns, or customer requests. | Weeks to months | AM + existing customer contacts |
| 2 | **Discovery & Validation** | Validate expansion metrics. For cross-sell: technical discovery — which PSPs they use, policy issues, current solution architecture. | Broader than new-logo — includes technical landscape assessment for cross-sell. Existing product baseline data already known. | 2-4 weeks | AM/AE + customer ops/risk/tech |
| 3 | **Commercial Build & Present** | Build expansion pricing/ROI. May be tied to renewal — AM handles existing product cost pushback, discount requests alongside expansion pitch. | Renewal-bundled dynamics. AM on call alongside AE. Pricing may be incremental (upsell) or net-new value prop (cross-sell). | 2-8 weeks | AE + AM + champion + DM |
| 4 | **Stakeholder Alignment** | Internal alignment and budget approvals for expansion scope. | Typically fewer new stakeholders needed. Existing champion may drive internally. Budget may be an extension of existing line item. | 2-8 weeks | AE + AM + existing champion + budget owner |
| 5 | **Legal** | Amendment or addendum to existing MSA. | Much shorter than full MSA negotiation. Delta-only terms. | 1-4 weeks | Legal (lighter touch) |
| 6 | **Integration** | Upsell: one endpoint (trivial) or none. Cross-sell: may require additional API integration. | Ranges from zero effort (upsell) to moderate (cross-sell new product). | 0-4 weeks | AE + SE (if cross-sell needs it) |
| 7 | **Onboarding** | Cross-sell: complicated, involves multiple Riskified teams. Upsell: usually easy, operational activation. | Cross-sell = heavy onboarding with multiple teams. Upsell = light, may be revenue-immediate. | 1-8 weeks (varies by type) | Varies by deal sub-type |

---

## 4. New Agent: Agent 0E — Account Health & Sentiment

### Purpose

The "account manager ear" — tracks client sentiment, existing product satisfaction, and renewal dynamics that color the entire expansion deal. A client who is unhappy with Riskified's current performance will not expand, regardless of how positive the upsell call itself sounds.

### Execution Position

Runs in **Step 1 in parallel with Agents 1-8**. Feeds output **only to Agents 9 (Adversarial) and 10 (Synthesis)**. Does not feed Agents 2-8 — this preserves parallel execution and avoids making 0E a sequential dependency.

```
Step 1: Agents 0E + 1-8 all run in parallel (9 agents, expansion only)
Step 2: Agent 9 reads all outputs including 0E
Step 3: Agent 10 synthesizes all outputs including 0E
```

For new-logo deals, Agent 0E does not run. Pipeline is unchanged: Agents 1-8 → 9 → 10.

### Output Schema

Follows the standardized agent output envelope (Section 7.4 of PRD). Agent-specific findings:

```python
class AccountHealthFindings(BaseModel):
    existing_product_sentiment: str       # Positive / Mixed / Negative / Not Discussed
    product_complaints: list[str]         # Verbatim complaints, max 5
    discount_pressure: bool
    discount_evidence: list[str]          # Max 3
    renewal_risk_signals: list[str]       # Max 5
    renewal_bundled: bool                 # Is expansion tied to renewal negotiation?
    renewal_bundled_evidence: str | None
    upsell_leverage_detected: bool        # Is expansion being used as leverage?
    account_relationship_health: str      # Strong / Adequate / Strained / Critical / Not Assessed
    relationship_health_rationale: str
    cross_sell_vs_upsell_inferred: str    # cross_sell / upsell / both / unclear
    existing_product_usage_signals: list[str]  # Max 3
```

### Guardrails (NEVER Rules for Agent 0E)

1. **Silence is not satisfaction:** If no existing product discussion appears in transcripts, set `account_relationship_health` to `"Not Assessed"` — never to `"Strong"` or `"Positive"`. Absence of complaints is NOT evidence of satisfaction.
2. **Leverage detection:** NEVER interpret bundled negotiation language as expansion enthusiasm. "We want to expand but need better renewal terms" is a negotiation tactic, not a buying signal.
3. **No hallucinated complaints:** NEVER infer product complaints from ambiguous language. Only cite explicit negative statements with verbatim evidence.

### Anti-Sycophancy Instruction

> "You are analyzing an existing customer relationship, not advocating for the expansion. If the buyer is dissatisfied with the current product, say so clearly — even if the expansion conversation sounds positive. Enthusiasm about a new product does not erase frustration with the existing one."

---

## 5. Pipeline Architecture Changes

### Approach: Dual-Mode Pipeline

Same pipeline code, same agent Python files. Deal type determines:
- Which agents run (0E included for expansion)
- Which prompt sections are active (Jinja2 conditionals)
- Which calibration config profile is loaded
- Which NEVER rules apply

### Pipeline Signature Change

```python
async def run_async(
    self,
    account_id: str,
    transcript_texts: list[str],
    timeline_entries: list[str] | None = None,
    deal_context: dict | None = None,  # NEW
) -> PipelineResult:
```

`deal_context` contains:
```python
{
    "deal_type": "expansion_upsell",         # from Account model
    "deal_type_ai_inferred": "expansion_upsell",  # from pre-pipeline classifier
    "deal_type_mismatch": False,
    "prior_contract_value": 50000.0,          # optional
}
```

### Context Injection (Not Prompt Duplication)

**Critical design decision:** Do NOT create separate prompt files per deal type. Use Jinja2 conditionals within existing prompts for the ~10% that differs. The 90% core analysis logic is identical for new-logo and expansion.

For agents needing significant deal-type variation (Agent 1 stage definitions, Agent 10 synthesis weights), use Jinja2 `{% if %}` blocks to swap sections.

For agents needing light variation (Agents 2-4, 6-8), inject deal context via `build_analysis_prompt()` in runner.py:

```python
# In runner.py build_analysis_prompt()
if deal_context and deal_context["deal_type"].startswith("expansion"):
    parts.append("## DEAL CONTEXT")
    parts.append("This is an EXPANSION deal with an existing Riskified customer.")
    parts.append(f"Deal type: {deal_context['deal_type']}")
    if deal_context.get("prior_contract_value"):
        parts.append(f"Prior contract value: ${deal_context['prior_contract_value']:,.0f}")
    parts.append("Adjust your analysis for expansion dynamics.\n")
```

### Prerequisite: Resolve Prompt Source of Truth

Agents currently have hardcoded `SYSTEM_PROMPT` strings in Python AND unused YAML files in `prompts/`. Before adding deal-type branching, migrate all agents to load prompts via `prompt_loader.load_prompt()`. This is a prerequisite — not part of the expansion feature itself, but must be done first.

---

## 6. Data Model Changes

### Account Model (2 new columns)

```python
deal_type = Column(Text, default="new_logo")
# Values: "new_logo" | "expansion_upsell" | "expansion_cross_sell" | "expansion_both"

prior_contract_value = Column(Float, nullable=True)
# Existing MRR if applicable. Optional, manually entered.
```

### AnalysisRun Model (1 new column)

```python
deal_type_at_run = Column(Text, nullable=True)
# Snapshots which pipeline mode was used. Immutable after creation.
```

### DealAssessment Model (2 new columns)

```python
deal_type = Column(Text, nullable=True)
stage_model = Column(Text, nullable=True)  # "new_logo_7stage" | "expansion_7stage"
```

### What NOT to add

- `is_cross_sell` — derived from `deal_type` (redundant)
- `renewal_bundled` on Account — this is an Agent 0E analysis output, stored in agent findings JSON
- `deal_type_ai_inferred` on Account — stored in AnalysisRun or PipelineResult, not the account

### Migration

Alembic migration. All new columns are nullable with defaults — zero-downtime, no data backfill needed. Both the main codebase and the FastAPI rebuild need the same migration.

---

## 7. Calibration Config Changes

Nested by deal type. Expansion profile uses different health score weights and forecast thresholds.

```yaml
global:
  confidence_ceiling_sparse_data: 0.60
  sparse_data_threshold: 3
  stale_signal_days: 30

new_logo:
  agent_6_economic_buyer:
    eb_absence_health_ceiling: 70
    secondhand_mention_counts_as_engaged: false
  synthesis_agent_10:
    health_score_weights:
      economic_buyer_engagement: 20
      stage_appropriateness: 15
      momentum_quality: 15
      technical_path_clarity: 10
      competitive_position: 10
      stakeholder_completeness: 10
      commitment_quality: 10
      commercial_clarity: 10
    forecast_commit_minimum_health: 75
    forecast_at_risk_maximum_health: 45

expansion:
  agent_0e_account_health:
    relationship_health_weight_in_score: 15
  agent_6_economic_buyer:
    eb_absence_health_ceiling: 85      # Higher — EB may be known from existing contract
    secondhand_mention_counts_as_engaged: false
  synthesis_agent_10:
    health_score_weights:
      account_relationship_health: 15   # NEW: from Agent 0E
      economic_buyer_engagement: 15     # Reduced from 20
      stage_appropriateness: 10         # Reduced — expansion stages less standardized
      momentum_quality: 15
      technical_path_clarity: 10        # Same for cross-sell; lower for upsell
      competitive_position: 5           # Lower — already your customer
      stakeholder_completeness: 10
      commitment_quality: 10
      commercial_clarity: 10
    forecast_commit_minimum_health: 65  # Lower bar for expansion
    forecast_at_risk_maximum_health: 40
```

**Note:** Expansion health score includes a 9th component (`account_relationship_health: 15`) from Agent 0E. The 8 original components are reweighted to total 85, making the overall total 100.

---

## 8. NEVER Rules: Deal-Type-Specific

### Existing Rules — Behavior per Deal Type

| Rule | New-Logo | Expansion |
|------|----------|-----------|
| Health > 70 requires EB engagement | Enforced (ceiling: 70) | Relaxed (ceiling: 85) — EB may be known from prior contract |
| Commit requires MSP + High specificity | Enforced | Modified — amendment timeline + PO sufficient (no full MSP required) |
| Unresolved contradictions blocked | Same | Same |
| No inferred pricing | Same | Same |
| Adversarial challenges required | Same | Same |

### New Expansion-Specific Rules

1. **NEVER ignore account health:** If Agent 0E reports `account_relationship_health` as `"Strained"` or `"Critical"`, health score MUST NOT exceed 60 — regardless of how positive the expansion signals look. A dissatisfied customer is a churn risk masquerading as an expansion opportunity.

2. **NEVER allow Commit without adequate relationship:** Commit forecast for expansion requires `account_relationship_health` to be `"Strong"` or `"Adequate"`. Strained relationships cannot support Commit regardless of commercial signals.

3. **NEVER miss renewal-bundled flag:** If transcript evidence shows renewal and expansion being negotiated together but `renewal_bundled` is `false`, flag a validation warning. Catches incorrect manual tagging.

4. **NEVER run expansion pipeline without Agent 0E:** If `deal_type` starts with `expansion_` but Agent 0E did not run or produced an error, the analysis must be flagged as incomplete.

### Implementation

`check_all_never_rules()` signature gets a `deal_type` parameter (keyword arg with default for backward compatibility):

```python
def check_all_never_rules(
    agent_outputs: dict,
    synthesis_output: dict,
    deal_type: str = "new_logo",
) -> list[NeverRuleViolation]:
    checkers = list(_COMMON_RULE_CHECKERS)
    if deal_type == "new_logo":
        checkers.extend(_NEW_LOGO_RULE_CHECKERS)
    else:
        checkers.extend(_EXPANSION_RULE_CHECKERS)
    ...
```

---

## 9. Agent-Stage Relevance (Expansion)

Updated matrix for expansion deals. Key differences: Agent 0E is Critical/High across all stages; Agent 8 (Competitive) is Low/irrelevant (customer already chose Riskified); Agent 5 (Technical) is higher for cross-sell stages.

| Agent | SQL | Discov. | Commer. | Stakeh. | Legal | Integr. | Onboard. |
|-------|-----|---------|---------|---------|-------|---------|----------|
| 0E. Account Health | **Critical** | **High** | **Critical** | **High** | Medium | Medium | Medium |
| 1. Stage & Progress | **High** | **High** | **High** | **High** | **High** | **High** | **High** |
| 2. Relationship & Power | Medium | Medium | **High** | **High** | Medium | Medium | Low |
| 3. Commercial & Risk | Low | Low | **Critical** | **High** | Low | Low | Low |
| 4. Momentum & Engagement | Medium | **High** | **High** | **High** | Medium | **High** | **High** |
| 5. Technical Validation | Low | **High** (cross-sell) | Low | Low | Low | **Critical** (cross-sell) | **High** (cross-sell) |
| 6. Economic Buyer | — | Low | Medium | **High** | Low | — | — |
| 7. MSP & Next Steps | Low | Medium | **High** | **High** | Medium | **High** | **High** |
| 8. Competitive Displacement | Low | Low | Low | Low | — | — | — |
| 9. Open Discovery | Medium | Medium | Medium | Medium | Medium | Medium | Medium |

---

## 10. Evaluation Framework

### Expansion Golden Test Set (minimum 15-20 deals)

| Category | Count | Purpose |
|----------|-------|---------|
| Upsell — won | 4-5 | Correctly identifies healthy expansion |
| Upsell — lost/stalled | 3-4 | Correctly flags at-risk expansion |
| Cross-sell — won | 3-4 | Handles integration complexity correctly |
| Cross-sell — lost/stalled | 2-3 | Identifies cross-sell-specific risks |
| Renewal-bundled | 3-4 | Detects renewal dynamics, leverage, cost pushback |
| Strained relationship | 2-3 | Does not over-score despite positive expansion signals |

### Cross-Pipeline Regression

- Run expansion golden test cases through BOTH pipelines (new-logo and expansion)
- Verify expansion pipeline scores are meaningfully higher for won deals
- Verify expansion pipeline does NOT over-score for lost deals
- Run existing new-logo golden set through new pipeline — verify zero regression

### Key Metrics

| Metric | Target |
|--------|--------|
| Score accuracy (expansion won deals) | Health score >= 60 |
| Score accuracy (expansion lost deals) | Health score <= 50 |
| Forecast accuracy | Commit/Best Case for deals that closed within 30 days |
| Deal type detection accuracy | >= 90% agreement with manual tag |
| Account health hallucination rate | "Not Assessed" when no product discussion exists |
| Latency | Wall-clock increase <= 15% vs new-logo pipeline |

### Shadow Mode (first 8 weeks)

Log both pipelines' scores for every expansion deal. Show expansion pipeline scores to users; log new-logo scores silently. If expansion pipeline consistently produces scores >80 for deals that stall or lose, the weights are too lenient.

---

## 11. UI Changes

### Pipeline Overview

- **Deal type badge** on each deal row (e.g., "Expansion — Upsell" badge)
- **Filter by deal type** dropdown in pipeline overview
- Same view for all deal types — no separate tabs
- Forecast rollups can optionally break out by deal type

### Upload / Account Creation

- **Deal type selector** — required field when creating an account
- Options: New Logo, Expansion — Upsell, Expansion — Cross-Sell, Expansion — Both
- **Prior contract value** — optional field, shown when expansion type selected

### Deal Detail

- **Agent 0E card** shown for expansion deals (between Agent list and Synthesis)
- Account relationship health prominently displayed
- Renewal-bundled flag shown as a badge if true
- Deal type mismatch warning if AI disagrees with manual tag

### Forecast Comparison

- Deal type included in comparison view
- Can filter to "show expansion deals only" or "show new-logo only"

---

## 12. Implementation Phases

| Phase | Scope | Prerequisite |
|-------|-------|-------------|
| **Phase 0** | Resolve prompt source of truth — migrate agents from hardcoded `SYSTEM_PROMPT` to YAML via `prompt_loader` | None |
| **Phase 1** | Data layer — add `deal_type`, `prior_contract_value` to Account; `deal_type_at_run` to AnalysisRun; Alembic migration; update API schemas | Phase 0 |
| **Phase 2** | Pipeline plumbing — add `deal_context` to `pipeline.run_async()`; inject deal context into `build_analysis_prompt()`; enrich `stage_context`; update `analysis_service` | Phase 1 |
| **Phase 3** | Agent 0E — build `sis/agents/account_health.py` with schema, prompt, `build_call`; add to pipeline conditionally; write golden tests | Phase 2 |
| **Phase 4** | Prompt tuning — add Jinja2 deal_type conditionals to Agent 1 (expansion stage model) and Agent 10 (expansion synthesis weights); lightweight context injection for Agents 2-8 | Phase 3 |
| **Phase 5** | Validation + calibration — expansion NEVER rules; nested calibration config; expansion stage_relevance matrix | Phase 4 |
| **Phase 6** | Frontend — DealTypeBadge component; deal type filter; Agent 0E card; upload page deal type selector; deal type mismatch warning | Phase 5 |
| **Phase 7** | Evaluation — build expansion golden test set; cross-pipeline regression; shadow mode logging | Phase 6 |

---

## 13. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Over-scoring expansion deals** | Medium | High | Shadow-run both pipelines for 8 weeks. Golden test set with lost/stalled expansion deals. Expansion-specific NEVER rules cap scores when relationship is strained. |
| **Account health hallucination** | Medium | High | "Silence is not satisfaction" guardrail. Agent 0E outputs "Not Assessed" when no product discussion exists. Evidence citation required for all sentiment claims. |
| **Prompt drift between deal-type variants** | Medium | Medium | Use Jinja2 conditionals (not separate files). Shared 90% of prompt logic in one place. Golden test regression catches drift. |
| **Renewal-bundled leverage misread** | Medium | Medium | NEVER rule: do not interpret bundled negotiation as expansion enthusiasm. Agent 0E has explicit leverage detection field. |
| **Deal type misclassification** | Low | Medium | Manual tag takes precedence. AI validates and flags mismatches. UI shows warning badge. Does not auto-correct. |
| **Increased maintenance burden** | Medium | Medium | Minimal code duplication (context injection, not prompt forking). One new agent module. Calibration config is additive, not forked. |

---

## 14. Open Questions

| # | Question | Owner | Priority |
|---|----------|-------|----------|
| 1 | What are the exact expansion health score weights? (Proposed weights in Section 7 need VP Sales calibration) | VP Sales | P0 |
| 2 | How many historical expansion deals are available for the golden test set? | VP Sales / Gong Admin | P0 |
| 3 | Should forecast comparison reports break out new-logo vs. expansion by default? | VP Sales | P1 |
| 4 | Does Agent 0E need external context (NPS, support tickets, usage metrics) in Phase 2? | VP Sales / CS Team | P2 |
| 5 | Should expansion deals have different "stale signal" thresholds (existing customers may have lower call cadence)? | VP Sales | P1 |

---

*This design was reviewed by the Data & AI Lead and Dev Lead agents. Key review findings are incorporated: Agent 0E feeds only Agents 9/10 (preserves parallelism), Jinja2 conditionals instead of prompt duplication, lightweight pre-pipeline deal type classifier, shadow-mode evaluation, and "silence is not satisfaction" guardrail.*
