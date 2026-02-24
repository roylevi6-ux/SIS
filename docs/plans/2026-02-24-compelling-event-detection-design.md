# Compelling Event & Urgency Detection Design

**Date**: 2026-02-24
**Status**: Approved
**Approach**: Distributed Enhancement (5 agents, no new agents, no architecture changes)

## Problem Statement

No single SIS agent owns "compelling events" as a primary focus. Coverage is fragmented:
- Agent 8 has `switching_catalyst` but scoped only to vendor-switch triggers
- Agent 4 mentions "buyer sharing timelines" as one bullet — no structured field
- Agent 7 captures go-live dates but never asks "why that date?"
- Agent 9 has "Market/Timing" discovery category — opportunistic only
- Agent 10 uses Agent 8's catalyst for "No Decision Risk" forecast — no urgency score

**Result**: Managers cannot answer "Why now?" for any deal without manually piecing together signals from 4+ agents.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Approach | Distributed across 5 agents | Each agent already listens in the right area — targeted additions, no architecture changes |
| Forecast guardrail | Hard: no compelling event = never Commit | Forces reps to find urgency or accept lower forecast |
| Seller-created urgency | Tracked but NOT penalized | Tracked for visibility, some manufactured urgency legitimately helps close |
| Consequence of inaction | Added to Agent 8 | Completes the "why now" picture — what happens if buyer does nothing |
| Health score | 10-point Urgency component (rebalanced from 100) | Competitive 10->8, Commitment 10->8, new Urgency 10. Sums to 100 |

---

## Agent 4: Momentum — Urgency Impact on Velocity

**Role**: Assess whether urgency is actually accelerating the deal — behavioral validation.

### Schema Addition

```python
class UrgencyImpact(BaseModel):
    """Behavioral validation of buyer-stated urgency."""
    urgency_detected: bool = Field(
        description="Did the buyer express any time pressure?"
    )
    urgency_behavioral_match: str = Field(
        description="Aligned (behavior matches stated urgency), "
        "Mismatched (says urgent, acts slow), or Ambiguous"
    )
    urgency_trend: str = Field(
        description="Increasing, Stable, Fading, or None"
    )
    urgency_evidence: str = Field(
        description="One sentence: the strongest behavioral signal "
        "supporting or contradicting urgency"
    )
```

In `MomentumFindings`:
```python
urgency_impact: Optional[UrgencyImpact] = Field(
    default=None,
    description="Urgency behavioral validation. Populate only when "
    "buyer expresses time pressure."
)
```

### Prompt Additions

```
## Urgency & Deal Velocity
When a buyer mentions timelines, deadlines, or business events:
- Assess whether their BEHAVIOR matches the stated urgency
- A buyer who says "urgent" but responds slowly, delays meetings,
  or won't pull in stakeholders = Mismatched urgency
- Track urgency trajectory across calls: is the time pressure increasing
  (approaching deadline) or fading (deadline passed or deprioritized)?
- Urgency that isn't backed by buyer behavior is a forecast risk
- A buyer who says "this is urgent" is stating intent, not proving urgency.
  Only their ACTIONS prove it.

## Urgency Trend Heuristics
- "Increasing": deadline mentioned with more specificity in recent calls
  than earlier ones, OR new stakeholders pulled in to meet timeline,
  OR buyer proactively compresses schedule
- "Fading": deadline mentioned in earlier calls but absent from recent ones,
  OR buyer language shifted from specific dates to "sometime in Q3",
  OR previously urgent items now described as "when we get to it"
- "Stable": same deadline referenced consistently across calls with no change
- "None": urgency was never mentioned, OR only mentioned once with no follow-through

If fewer than 3 transcripts are available, set urgency_trend to "None" --
a single call cannot establish a trajectory.
```

### Token Impact
~70-100 output tokens added. Agent 4 uses ~1,800 of 5,500 — safe.

---

## Agent 7: MSP/Timeline — Deadline Drivers

**Role**: Capture the "when" and "why" behind deadlines — what business event anchors the go-live date.

### Schema Additions

```python
class CompellingDeadline(BaseModel):
    """A firm business deadline anchoring the deal timeline."""
    event_type: str = Field(
        description="Contract Expiry | Regulatory/Compliance | Fiscal Year/Budget | "
        "Executive Mandate | Seasonal/Business Cycle | Integration Dependency | Other"
    )
    description: str = Field(
        description="One sentence: what is the deadline and why it matters"
    )
    date_if_stated: Optional[str] = Field(
        default=None,
        description="The actual date/quarter if buyer stated one"
    )
    firmness: str = Field(
        description="Hard (external, immovable) | Firm (internal, committed) | "
        "Soft (aspirational)"
    )
    source: str = Field(
        description="Buyer-stated (buyer said date + reason) | "
        "Inferred from context"
    )
    stability: str = Field(
        description="Stable (consistent across calls) | Shifted (moved once) | "
        "Repeatedly Moved (red flag) | New (latest call only)"
    )
```

In `MSPNextStepsFindings`:
```python
compelling_deadline: Optional[CompellingDeadline] = Field(
    default=None,
    description="Populate only when a firm business deadline exists. "
    "Null if no deadline identified."
)
```

In `NextStep`:
```python
supports_deadline: bool = Field(
    default=False,
    description="True if this action is on the critical path "
    "to the compelling deadline"
)
```

### Prompt Additions

```
## Deadline Drivers
When a go-live date or timeline is mentioned:
- Identify WHAT business event anchors it (contract expiry, regulatory deadline,
  fiscal year, board mandate, seasonal peak, integration dependency)
- Assess firmness: Hard = externally imposed, immovable (regulatory, contract).
  Firm = internally committed, has consequences if missed.
  Soft = aspirational, movable without consequence.
- "Hard" deadlines anchored to external events are the strongest signals
- If NO business event anchors any stated timeline, set compelling_deadline to null.
  Do NOT fabricate deadline drivers from generic "let's aim for Q3" language.

## Scope Boundary: Catalyst vs. Deadline
Agent 8 handles WHY the buyer is considering change (the switching catalyst).
Your job is different: you handle WHEN the buyer must act and what makes the
timeline stick. A "platform migration" is a catalyst (Agent 8's domain).
A "platform migration completing Q3 2026 that requires a new fraud vendor
integrated before launch" is a deadline driver (YOUR domain).
Focus on the DATE ANCHOR, not the motivation.

## Firmness Examples (Riskified-specific)
- Hard: "We need fraud prevention live before Black Friday" (seasonal, immovable)
- Hard: "Our Forter contract ends March 31" (contractual, external)
- Firm: "Our board approved the fraud initiative for H2 and it's in the 2026 plan"
- Soft: "We'd like to have something in place by end of year" (aspirational)

## Source Calibration
"Buyer-stated" = buyer explicitly said a date AND a reason.
"Inferred from context" = date stated but reason assembled from multiple signals.
NEVER infer a compelling deadline from seller-stated timelines alone.
```

### Token Impact
~170 output tokens, ~375 system prompt tokens. Well within budget.

---

## Agent 8: Competitive — Expanded Catalyst + Consequence

**Role**: Complete the "why now" answer — what happens if the buyer does nothing, how soon, and whose urgency.

### Schema Additions

In `CompetitiveFindings`:
```python
consequence_of_inaction: Optional[str] = Field(
    default=None,
    description="What happens if the buyer does nothing? "
    "Severe (business viability at risk), "
    "Moderate (measurable ongoing cost), "
    "Mild (growth limited but no immediate pain), or "
    "None (buyer can delay indefinitely)"
)

catalyst_time_horizon: Optional[str] = Field(
    default=None,
    description="When must the buyer act? "
    "Immediate (days-weeks) | Near-term (1-3 months) | "
    "Medium-term (3-6 months) | Long-term (6+ months) | No Timeline"
)

urgency_source: str = Field(
    default="None Identified",
    description="Customer-initiated | Seller-created | Market/External | None Identified. "
    "Choose the PRIMARY source if multiple exist."
)
```

### Prompt Additions

```
## Catalyst vs. Consequence: How They Differ
The switching catalyst is the EVENT that might force a decision
(chargeback spike, platform migration).
Catalyst strength rates how compelling that event is.
Consequence of inaction rates what happens to the buyer's BUSINESS
if they ignore the catalyst.
These can diverge: a strong catalyst (platform migration) might have
only a mild consequence (the old platform still works, just costs more).

## Consequence of Inaction
Every deal has a "do nothing" option. Assess what happens if the buyer
stays with the status quo:
- Severe: business viability threatened (fraud losses accelerating,
  processor termination)
- Moderate: measurable ongoing cost (contract renewal at higher rate,
  manual review costs)
- Mild: growth limited, competitive disadvantage persists
- None: buyer can delay indefinitely with no pain
The strength of the consequence directly predicts whether the deal
will close on time or slip.

If no transcript evidence exists for consequence of inaction,
output "None" and note the gap in data_quality_notes.
Do NOT infer consequence from catalyst alone.

## Urgency Source
- Customer-initiated: the buyer raised the timeline due to their own
  business needs
- Seller-created: the sales team introduced urgency (end-of-quarter
  pricing, competitive framing)
- Market/External: external event driving timeline (regulatory change,
  industry shift)
Note: Seller-created urgency is tracked for visibility, not as a
negative signal. Choose the PRIMARY source if multiple exist.

If catalyst_strength is "None Identified", set catalyst_time_horizon
to "No Timeline".
urgency_source MUST be one of: "Customer-initiated", "Seller-created",
"Market/External", "None Identified". Do not use any other values.
```

### Token Impact
~30 output tokens, ~255 system prompt tokens. Agent 8 uses ~3,000 of 5,500 — safe.

---

## Agent 9: Open Discovery — Urgency Audit

**Role**: Cross-agent validation — is the urgency credible and consistent across agents?

### Schema Additions

```python
class UrgencyAudit(BaseModel):
    """Cross-agent urgency credibility assessment."""
    urgency_credibility: str = Field(
        description="Credible | Questionable | Insufficient Evidence"
    )
    assessment: str = Field(
        description="1-2 sentences: is the urgency real? Why or why not?"
    )
    cross_agent_consistency: str = Field(
        description="Consistent | Partially Consistent | Inconsistent | "
        "Insufficient Data"
    )
    consistency_detail: str = Field(
        description="1-2 sentences explaining consistency assessment"
    )
```

In `OpenDiscoveryFindings`:
```python
urgency_audit: UrgencyAudit = Field(
    description="Always populated. Cross-agent urgency credibility assessment. "
    "Use 'Insufficient Evidence' when no urgency signals exist."
)
```

**Note**: Always populated (not Optional) — "Insufficient Evidence" when no signals.

### Prompt Additions

```
## Urgency Audit
Cross-reference urgency signals from upstream agents:
- Agent 4 findings.urgency_impact: Is buyer BEHAVING urgently?
  (urgency_behavioral_match, urgency_trend)
- Agent 7 findings.compelling_deadline: Is there a HARD deadline
  with a business anchor? (firmness, stability)
- Agent 8 findings: Is there a real CATALYST with painful consequences?
  (catalyst_strength, consequence_of_inaction, urgency_source)

Flag inconsistencies:
- Agent 8 catalyst_strength "Existential" but Agent 4
  urgency_behavioral_match "Mismatched" = questionable
- Agent 7 firmness "Hard" but Agent 4 urgency_trend "Fading"
  = deadline may not stick
- Agent 8 urgency_source "Seller-created" without Agent 4
  urgency_behavioral_match "Aligned" = note for visibility
- All three agents show weak/no urgency signals = not a red flag,
  just note "no compelling event identified"

This is NOT a negative signal by default -- just a credibility
assessment for the manager.
```

### Token Impact
~80-120 output tokens. Well within 5,500 budget.

---

## Agent 10: Synthesis — "Why Now?" + Hard Guardrail

**Role**: Unified urgency picture — health score component, deal memo paragraph, forecast guardrail.

### Health Score Rebalancing

| Component | Before | After | Source |
|-----------|--------|-------|--------|
| Economic buyer engagement | 20 | 20 | Agent 6 |
| Stage appropriateness | 15 | 15 | Agent 1 |
| Momentum quality | 15 | 15 | Agent 4 |
| Technical path clarity | 10 | 10 | Agent 5 |
| Competitive position | 10 | **8** | Agent 8 |
| Stakeholder completeness | 10 | 10 | Agent 2 |
| Commitment quality | 10 | **8** | Agent 7 |
| Commercial clarity | 10 | 10 | Agent 3 |
| **Urgency & Compelling Event** | -- | **10** | **Agents 4, 7, 8, 9** |
| **Total** | **100** | **100** | |

### Urgency Scoring Rubric (10 points max)

```
9-10: Hard deadline (Agent 7) + Existential/Structural catalyst (Agent 8)
      + Aligned urgency behavior (Agent 4) + Credible (Agent 9)
6-8:  Firm deadline OR strong catalyst, with consistent behavioral signals
3-5:  Soft deadline or weak catalyst, OR urgency signals inconsistent
0-2:  No compelling event identified, OR Agent 9 flags "Questionable"

Stage awareness: For Stage 1-3 deals, scoring 0-2 on urgency is expected
and should not be treated as a red flag.
```

### Deal Memo — New Paragraph 5: "Why Now?"

Insert as paragraph 5 (after Commercial/Competitive, before Momentum):

```
5. **Why Now?** -- What compelling event drives this deal? Is the urgency
   customer-initiated or seller-created? How firm is the deadline? What
   happens if the buyer does nothing? (Agents 4, 7, 8, 9)
```

Update deal memo description: "8-9 paragraphs, max 1200 words" (was 7-8, 1000).

### New NEVER Rule

```
- NEVER produce Commit forecast if Agent 8 consequence_of_inaction is "None"
  AND Agent 8 catalyst_strength is "None Identified". A deal with no pain
  of inaction and no catalyst is not committable.
```

Consolidate with existing No-Decision Risk Override into a single
"Forecast Override Rules" section.

### Cross-Agent Synthesis Guidance

```
When urgency_source (Agent 8) says "Seller-created" but meeting_initiation
(Agent 4) says "Buyer-initiated", the buyer may be engaged but the urgency
is artificial. Weight catalyst_strength and consequence_of_inaction more
heavily than urgency_source in this case.

Agent 7 compelling_deadline with firmness "Hard" and stability "Stable" is a
strong positive signal for commitment quality scoring (cap commitment quality
at 6/8 if no compelling deadline exists in stage 5+ deals).
```

### Calibration Config

Update `_default_calibration_config()` in `config.py` and `config/calibration/current.yml`:
- Add `urgency_compelling_event` weight for both `new_logo` and `expansion` deal types
- Expansion deals: urgency may deserve slightly different weighting (contract renewal = strong internal deadline)

### Token Impact
~125 system prompt tokens, ~500 input tokens (from upstream urgency fields), ~230 output tokens. Well within 12,000 budget.

---

## Cross-Agent Data Flow

```
Agents 4, 7, 8 (parallel, Sonnet, 5,500 tokens each)
  ├── Agent 4: urgency_impact (behavioral validation)
  ├── Agent 7: compelling_deadline (date anchor + firmness)
  └── Agent 8: consequence_of_inaction + catalyst_time_horizon + urgency_source
         │
         ▼
Agent 9 (sequential, Sonnet, 5,500 tokens)
  └── urgency_audit (cross-agent credibility check)
         │
         ▼
Agent 10 (sequential, Sonnet, 12,000 tokens)
  ├── Health score: Urgency component (10 points)
  ├── Deal memo: "Why Now?" paragraph
  ├── Forecast guardrail: No Commit without catalyst + consequence
  └── Cross-agent synthesis guidance
```

No changes to `strip_for_adversarial()` or `strip_for_synthesis()` needed — urgency fields are inside `findings`, which flows through both strip functions.

## Files to Modify

| File | Changes |
|------|---------|
| `sis/agents/momentum.py` | Add `UrgencyImpact` model, update `MomentumFindings`, add prompt sections |
| `sis/agents/msp_next_steps.py` | Add `CompellingDeadline` model, update `MSPNextStepsFindings`, update `NextStep`, add prompt sections |
| `sis/agents/competitive.py` | Add 3 fields to `CompetitiveFindings`, add prompt sections |
| `sis/agents/open_discovery.py` | Add `UrgencyAudit` model, update `OpenDiscoveryFindings`, add prompt section |
| `sis/agents/synthesis.py` | Add health score component, update deal memo, add NEVER rule, add scoring rubric, add cross-agent guidance |
| `sis/config.py` | Update calibration config with urgency weights |
| `config/calibration/current.yml` | Add urgency weights for new_logo and expansion |

## Testing

After implementation:
1. Run pipeline with a sparse-data deal (1-2 transcripts) — verify urgency fields default correctly
2. Run pipeline with a rich deal (5+ transcripts) — verify all urgency fields populate and Agent 9 cross-references correctly
3. Verify health score sums to 100
4. Verify Commit forecast is blocked when consequence_of_inaction = "None" AND catalyst_strength = "None Identified"
5. Check wall clock time stays under 130% of baseline (no new agents, just prompt expansion)
