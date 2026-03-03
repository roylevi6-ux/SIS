# Regional Buying Culture Profiles — Design Document

**Date:** 2026-03-03
**Status:** Approved
**Author:** Claude + Roy

## Problem

SIS evaluates all deals against US/Western buying patterns where the Economic Buyer (EB) is expected to appear on sales calls by Stage 4. In markets like Japan, China, and Korea, the actual budget holder/C-level may never appear on recorded calls — this is normal behavior, not a risk signal. The current system penalizes these deals unfairly:

- Agent 6 scores EB engagement as 0/11 when EB never appears
- Health score ceiling rules cap scores at 70-80 without EB engagement
- Forecast rules block Commit without EB engagement signals

A perfectly healthy Japan deal where the section chief (_kacho_) handles all vendor interactions — and the department head (_bucho_) only appears at contract signing — gets flagged as high-risk.

## Decision Summary

1. **Two buying culture profiles**: Direct (default) and Proxy-Delegated (Japan/China/Korea)
2. **Remove all scoring ceiling NEVER rules** globally (3 rules) — let the weighted scoring system do its job
3. **Profile-specific health score weights** in calibration config
4. **Manual field on upload page** for POC; Salesforce auto-mapping for production
5. **Keep all 36 other NEVER rules** unchanged (anti-hallucination + logical constraints)

## Buying Culture Profiles

### Direct (Default)

Applies to: US, UK, Israel, Australia, Western Europe, and all accounts not explicitly tagged.

EB is expected to appear on calls or be referenced by champion with specifics by Stage 4. This is the current system behavior — no changes.

### Proxy-Delegated

Applies to: Japan, China, Korea (set manually per account).

EB delegates entirely to a trusted proxy (champion or senior stakeholder). EB may never appear on a recorded call. The champion's authority signals and relationship breadth replace EB direct engagement as key indicators.

## Health Score Weight Redistribution

| Component | Direct | Proxy-Delegated | Delta |
|-----------|--------|-----------------|-------|
| Buyer-Validated Pain & Commercial Clarity | 14 | 14 | — |
| Momentum Quality | 13 | 13 | — |
| Champion Strength | 12 | **19** | +7 |
| Commitment Quality | 11 | 11 | — |
| Economic Buyer Engagement | 11 | **0** | -11 |
| Urgency / Compelling Event | 10 | 10 | — |
| Stage Appropriateness | 9 | 9 | — |
| Multithreading / Stakeholder Coverage | 7 | **11** | +4 |
| Competitive Position | 7 | 7 | — |
| Technical Path Clarity | 6 | 6 | — |
| **Total** | **100** | **100** | |

**Rationale:**
- Champion gets +7 because in proxy cultures the champion carries the EB's authority — they ARE the deal
- Multithreading gets +4 because breadth of relationships signals organizational buy-in when the decision-maker is invisible
- EB goes to 0 because the budget holder will almost never appear on Gong-recorded calls

## NEVER Rules Changes

### Remove (3 scoring ceiling rules)

These are removed **globally** (all profiles), not just for proxy deals. The weighted scoring system handles these constraints through weights — ceiling rules double-penalize and prevent flexibility.

| Rule ID | Description | Why Remove |
|---------|-------------|------------|
| `NEVER_HEALTH_WITHOUT_EB` | Health > 80 forbidden without EB at Stage 4+ | Redundant with EB weight scoring. Cultural blind spot. |
| `NEVER_HEALTH_WITHOUT_CHAMPION` | Health > 75 forbidden without champion at Stage 3+ | Redundant with champion weight scoring. |
| `NEVER_EXPANSION_HEALTH_CAP` | Health > 60 forbidden when relationship Strained/Critical | Redundant with expansion relationship weight scoring. |

**Also remove corresponding prompt text from Agent 10:**
- "NEVER produce health score >80 when NO direct or champion-relayed EB engagement AND deal is Stage 4+"
- "NEVER produce health score >75 when NO champion identified AND deal is Stage 3+"
- "NEVER produce health > 60 if Agent 0E account_relationship_health is Strained or Critical"

### Keep (36 rules)

All anti-hallucination rules, logical constraint rules, and agent-specific analytical guardrails remain unchanged. See full inventory in brainstorming session notes.

## Data Model

### accounts table — new column

```sql
ALTER TABLE accounts ADD COLUMN buying_culture VARCHAR DEFAULT 'direct';
-- Valid values: 'direct', 'proxy_delegated'
```

### Calibration config — new structure

```yaml
buying_culture_profiles:
  direct:
    health_score_weights:
      buyer_validated_pain_commercial_clarity: 14
      momentum_quality: 13
      champion_strength: 12
      commitment_quality: 11
      economic_buyer_engagement: 11
      urgency_compelling_event: 10
      stage_appropriateness: 9
      multithreading_stakeholder_coverage: 7
      competitive_position: 7
      technical_path_clarity: 6

  proxy_delegated:
    health_score_weights:
      buyer_validated_pain_commercial_clarity: 14
      momentum_quality: 13
      champion_strength: 19
      commitment_quality: 11
      economic_buyer_engagement: 0
      urgency_compelling_event: 10
      stage_appropriateness: 9
      multithreading_stakeholder_coverage: 11
      competitive_position: 7
      technical_path_clarity: 6
```

## Agent Changes

### Agent 6 (Economic Buyer) — Context Injection for Proxy Deals

When `buying_culture == "proxy_delegated"`, inject into Agent 6 system prompt:

> "This account uses a proxy-delegated buying culture (common in Japan, China, Korea). The economic buyer typically does NOT appear on vendor calls — this is expected behavior, not a risk signal. Focus your analysis on: (1) whether the champion has credible authority signals, (2) budget language quality, (3) proxy authority indicators (champion saying 'I have approval' or 'my VP has signed off'). Score EB engagement as 'Indirect' when champion relays credible EB context."

Agent 6 still runs and produces all structured fields. If EB appears (rare), it's a strong positive. If EB is absent, the narrative explains this is culturally expected rather than flagging it as a gap.

### Agent 10 (Synthesis) — Profile-Aware Scoring

Agent 10 receives:
1. The `buying_culture` value in its context
2. The matching weight table from calibration config

Weight selection in prompt construction:
```python
culture = account.buying_culture or "direct"
weights = config["buying_culture_profiles"][culture]["health_score_weights"]
```

The weight table is injected directly into Agent 10's scoring rubric section.

## UI Changes

### Upload/Import Page

Add dropdown field:
- **Label:** "Buying Culture"
- **Options:** Direct (default) | Proxy-Delegated (APAC)
- **Persists to:** `accounts.buying_culture`
- **Position:** After account name, before file upload

### Methodology Page

Add new section "Buying Culture Profiles" showing:
- Side-by-side weight comparison table (Direct vs Proxy-Delegated)
- Which regions map to which profile
- Explanation of why EB scoring differs across cultures

### Deal Intelligence / Analysis View

Show the buying culture tag somewhere visible on the analysis output so managers understand why weights differ. Small badge or label — "Proxy-Delegated" next to the account name.

## Backfill Plan

For existing ~33 accounts in the database:
- Default all to "direct"
- Walk through each account with Roy to identify proxy-delegated accounts
- Update via a simple script or direct DB update

## Future: Salesforce Integration

When CRM integration is active:
- Map `BillingCountry` to buying culture automatically
- Japan, China, South Korea → `proxy_delegated`
- All others → `direct`
- Manual override always available

## Out of Scope (for now)

- Additional profiles (Consensus, Relationship-Gated) — can add later
- Auto-detection from transcript language/signals
- Per-deal culture override (it's account-level only)
- Agent 2 prompt changes (champion identification criteria stay the same — the weight change handles the scoring impact)
