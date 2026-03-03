# Buying Culture Profiles — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add regional buying culture profiles so Japan/China/Korea deals are scored with culturally appropriate weights (EB weight → 0, Champion +7, Multithreading +4). Also remove 3 scoring ceiling NEVER rules globally.

**Architecture:** New `buying_culture` column on `accounts` table drives profile-aware weight selection. Calibration config stores per-profile weight tables. Agent 6 gets a context injection for proxy deals. Agent 10 receives the matching weight table. NEVER rules engine drops 3 ceiling rules. Frontend adds dropdown on upload, badge on deal view, and new methodology section.

**Tech Stack:** SQLAlchemy/Alembic (migration), Python (agent prompts, pipeline, validation), Next.js/React (frontend), Tailwind CSS (styling)

---

## Task 1: Alembic Migration — Add `buying_culture` to accounts

**Files:**
- Create: `alembic/versions/b5c6d7e8f9a0_add_buying_culture_column.py`
- Reference: `sis/db/models.py:100-117` (Account model)

**Step 1: Create migration file**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
.venv/bin/alembic revision --autogenerate -m "add buying_culture column to accounts"
```

If autogenerate doesn't pick it up (model not updated yet), create manually:

```python
"""add buying_culture column to accounts

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b5c6d7e8f9a0"
down_revision = "a1b2c3d4e5f6"

def upgrade():
    op.add_column("accounts", sa.Column("buying_culture", sa.Text(), server_default="direct", nullable=False))

def downgrade():
    op.drop_column("accounts", "buying_culture")
```

**Step 2: Update Account model**

In `sis/db/models.py`, add after line 114 (`sf_close_quarter`):

```python
    buying_culture  = Column(Text, nullable=False, default="direct")  # "direct" | "proxy_delegated"
```

**Step 3: Run migration**

```bash
.venv/bin/alembic upgrade head
```

Expected: Migration applies, `buying_culture` column added with default `"direct"` for all existing rows.

**Step 4: Verify**

```bash
.venv/bin/python -c "
from sis.db.session import get_session
from sis.db.models import Account
with get_session() as s:
    accts = s.query(Account).all()
    for a in accts:
        print(f'{a.account_name}: {a.buying_culture}')
"
```

Expected: All accounts show `buying_culture: direct`.

**Step 5: Commit**

```bash
git add sis/db/models.py alembic/versions/b5c6d7e8f9a0_add_buying_culture_column.py
git commit -m "feat: add buying_culture column to accounts table"
```

---

## Task 2: Update Calibration Config with Profile-Specific Weights

**Files:**
- Modify: `sis/prompts/calibration/config.yaml`

**Step 1: Restructure health_score_weights under profiles**

Replace the existing `synthesis_agent_10.health_score_weights` block with a new `buying_culture_profiles` section. Keep the old top-level weights as `direct` profile for backwards compatibility.

Replace lines 14-28 of `sis/prompts/calibration/config.yaml` with:

```yaml
synthesis_agent_10:
  champion_absence_health_ceiling: 65  # DEPRECATED — ceiling rules being removed
  forecast_commit_minimum_health: 75
  forecast_at_risk_maximum_health: 45
  forecast_categories:
    - Commit
    - Realistic
    - Upside
    - At Risk

buying_culture_profiles:
  direct:
    label: "Direct"
    description: "EB expected on calls by Stage 4 (US, UK, Israel, Australia, Western Europe)"
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
    label: "Proxy-Delegated (APAC)"
    description: "EB delegates to trusted proxy, rarely appears on calls (Japan, China, Korea)"
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

**Step 2: Remove deprecated EB ceiling config**

Delete lines 10-12 (the old `agent_6_economic_buyer` section):

```yaml
# DELETE THIS:
agent_6_economic_buyer:
  eb_absence_health_ceiling: 70
  secondhand_mention_counts_as_engaged: false
```

**Step 3: Commit**

```bash
git add sis/prompts/calibration/config.yaml
git commit -m "feat: add buying culture profiles to calibration config"
```

---

## Task 3: Remove 3 Scoring Ceiling NEVER Rules

**Files:**
- Modify: `sis/validation/never_rules.py`
- Modify: `tests/test_never_rules.py`
- Modify: `sis/agents/synthesis.py` (prompt text)

### Step 1: Remove code-enforced ceiling rules from `never_rules.py`

Delete these 3 functions entirely:
- `check_health_score_without_eb` (lines 24-69)
- `check_health_score_without_champion` (lines 72-114)
- `check_expansion_account_health_cap` (lines 358-385)

Remove them from the rule checker lists:

In `_NEW_LOGO_RULE_CHECKERS` (line 428), remove `check_health_score_without_eb` and `check_health_score_without_champion`. Should become:

```python
_NEW_LOGO_RULE_CHECKERS = [
    check_commit_without_commitments,
]
```

In `_EXPANSION_RULE_CHECKERS` (line 434), remove all three. Should become:

```python
_EXPANSION_RULE_CHECKERS = [
    check_commit_without_commitments,
    check_expansion_commit_relationship,
]
```

### Step 2: Remove prompt-level ceiling rules from Agent 10

In `sis/agents/synthesis.py`, remove these lines from the NEVER Rules section (lines 437-439):

```
- NEVER produce health score >80 when NO direct or champion-relayed Economic Buyer engagement AND deal is Stage 4 or later.
- NEVER produce health score >75 when NO champion identified (Agent 2 champion.identified=false) AND deal is Stage 3 or later.
```

And from the expansion section (line 404-405, 408), remove:

```
Cap health at 60 for Strained/Critical.
```

And remove line 408:
```
- NEVER produce health > 60 if Agent 0E account_relationship_health is "Strained" or "Critical"
```

### Step 3: Update tests

In `tests/test_never_rules.py`:

- Delete `TestHealthScoreWithoutEB` class entirely (lines 19-77)
- Delete `TestHealthScoreWithoutChampion` class entirely (lines 79-144)
- Delete `TestExpansionAccountHealthCap` class entirely (lines 425-450)
- Remove imports: `check_health_score_without_eb`, `check_health_score_without_champion`, `check_expansion_account_health_cap`
- Update `TestCheckAllNeverRules.test_multiple_violations`: remove assertions for `NEVER_HEALTH_WITHOUT_EB` and `NEVER_HEALTH_WITHOUT_CHAMPION`. Adjust the `assert len(violations) >= 4` count downward.
- Update `TestCheckAllExpansionRules.test_expansion_includes_expansion_rules`: remove assertion for `NEVER_EXPANSION_HEALTH_CAP`.

### Step 4: Run tests

```bash
cd /Users/roylevierez/Documents/Sales/SIS
.venv/bin/python -m pytest tests/test_never_rules.py -v
```

Expected: All remaining tests pass. 3 test classes removed.

### Step 5: Commit

```bash
git add sis/validation/never_rules.py sis/agents/synthesis.py tests/test_never_rules.py
git commit -m "feat: remove 3 scoring ceiling NEVER rules (EB, champion, expansion health cap)"
```

---

## Task 4: Pipe `buying_culture` into Pipeline Context

**Files:**
- Modify: `sis/services/analysis_service.py:61-116` (`_prepare_analysis_context`)
- Modify: `sis/orchestrator/pipeline.py:140-200` (pipeline signatures)

### Step 1: Add `buying_culture` to `deal_context`

In `sis/services/analysis_service.py`, in `_prepare_analysis_context`, after line 84 (`prior_contract_value = account.prior_contract_value`), add:

```python
        buying_culture = account.buying_culture or "direct"
```

Then in the `deal_context` dict (line 111-115), add the field:

```python
    deal_context = {
        "deal_type": deal_type,
        "prior_contract_value": prior_contract_value,
        "most_recent_transcript_age_days": transcript_age_days,
        "buying_culture": buying_culture,
    }
```

No changes needed to the pipeline signatures — `deal_context` is already a `dict | None` that flows through. The new key will be available in `deal_context["buying_culture"]` wherever `deal_context` is accessed.

### Step 2: Verify `deal_context` reaches Agent 6

Check that `deal_context` reaches Agent 6's `build_call`. Currently (pipeline.py line 337), agents 2-8 receive `(transcript_texts, stage_context, timeline_entries)` — they do NOT receive `deal_context`. We need to pass it to Agent 6.

In `pipeline.py`, modify the parallel agent build section (around line 330-337):

```python
for agent_id, builder in agent_builders:
    build_start = time.time()
    if agent_id == "agent_0e":
        call_kwargs = builder(
            transcript_texts, timeline_entries, deal_context, stage_context,
        )
    elif agent_id == "agent_6":
        call_kwargs = builder(transcript_texts, stage_context, timeline_entries, deal_context)
    else:
        call_kwargs = builder(transcript_texts, stage_context, timeline_entries)
    build_times[agent_id] = time.time() - build_start
```

### Step 3: Pass `deal_context` to Agent 10

Agent 10's `synthesis_build_call` (pipeline.py line 471) needs `buying_culture`. Add `deal_context` to the call:

Current: `synthesis_build_call(result.agent_outputs, stage_context, sf_data)`
Change to: `synthesis_build_call(result.agent_outputs, stage_context, sf_data, deal_context)`

### Step 4: Commit

```bash
git add sis/services/analysis_service.py sis/orchestrator/pipeline.py
git commit -m "feat: pipe buying_culture through deal_context to agents 6 and 10"
```

---

## Task 5: Agent 6 — Proxy-Delegated Context Injection

**Files:**
- Modify: `sis/agents/economic_buyer.py:139-153` (build_call function)

### Step 1: Update `build_call` signature and prompt construction

Change the `build_call` function to accept `deal_context` and inject proxy context:

```python
def build_call(
    transcript_texts: list[str],
    stage_context: dict,
    timeline_entries: list[str] | None = None,
    deal_context: dict | None = None,
) -> dict:
    """Build kwargs dict for run_agent / run_agent_async."""
    system = SYSTEM_PROMPT

    # Inject proxy-delegated context
    buying_culture = (deal_context or {}).get("buying_culture", "direct")
    if buying_culture == "proxy_delegated":
        system += """

## BUYING CULTURE: PROXY-DELEGATED
This account uses a proxy-delegated buying culture (common in Japan, China, Korea). The economic buyer typically does NOT appear on vendor calls — this is expected behavior, not a risk signal. Adjust your analysis:
- Focus on whether the champion has credible authority signals (proxy for EB authority)
- Evaluate budget language quality — proxy authority indicators like "I have approval" or "my VP has signed off" count as Indirect engagement
- Score eb_engagement as "Indirect" when champion relays credible EB context with specifics
- If EB never appears, this is CULTURALLY EXPECTED — frame the narrative accordingly, not as a gap
- If EB does appear on a call, this is an exceptionally strong positive signal"""

    return {
        "agent_name": "Agent 6: Economic Buyer",
        "system_prompt": system,
        "user_prompt": build_analysis_prompt(
            transcript_texts, stage_context, timeline_entries,
            "Based on the above, assess the economic buyer presence and budget authority.",
        ),
        "output_model": EconomicBuyerOutput,
    }
```

### Step 2: Commit

```bash
git add sis/agents/economic_buyer.py
git commit -m "feat: inject proxy-delegated culture context into Agent 6 prompt"
```

---

## Task 6: Agent 10 — Profile-Aware Weight Table

**Files:**
- Modify: `sis/agents/synthesis.py:287-300` (weight table in prompt)
- Modify: `sis/agents/synthesis.py:476-540` (build_call function)

### Step 1: Update `build_call` to accept `deal_context` and inject culture-aware weights

Change the `build_call` signature (line 476):

```python
def build_call(
    upstream_outputs: dict[str, dict],
    stage_context: dict,
    sf_data: dict | None = None,
    deal_context: dict | None = None,
) -> dict:
```

### Step 2: Build dynamic weight table injection

After the existing `parts` list is built (around line 540, before the return), inject a buying culture override block. The cleanest approach: build the system prompt dynamically based on culture.

Add this logic before the return statement in `build_call`:

```python
    # Inject buying culture weight override
    buying_culture = (deal_context or {}).get("buying_culture", "direct")
    system = SYSTEM_PROMPT
    if buying_culture == "proxy_delegated":
        # Replace the default weight table with proxy-delegated weights
        system = system.replace(
            "| Champion strength | 12 | Agent 2 |",
            "| Champion strength | 19 | Agent 2 |",
        ).replace(
            "| Economic buyer engagement | 11 | Agent 6 |",
            "| Economic buyer engagement | 0 | Agent 6 |",
        ).replace(
            "| Multi-threading & stakeholder coverage | 7 | Agent 2 |",
            "| Multi-threading & stakeholder coverage | 11 | Agent 2 |",
        )
        # Add culture context note
        system += """

## BUYING CULTURE: PROXY-DELEGATED
This deal uses a proxy-delegated buying culture (Japan, China, Korea). The weight table above has been adjusted:
- Economic Buyer engagement weight is 0 (EB absence is culturally expected, not a risk)
- Champion strength weight is 19 (the champion carries EB authority in proxy cultures)
- Multi-threading weight is 11 (relationship breadth signals organizational buy-in)
Score accordingly — do NOT penalize for EB absence."""
```

Then change the return to use `system` instead of `SYSTEM_PROMPT`:

```python
    return {
        "agent_name": "Agent 10: Synthesis",
        "system_prompt": system,
        "user_prompt": "\n".join(parts),
        "output_model": SynthesisOutput,
        "model": "opus",
    }
```

**Note:** Check if the return currently uses `SYSTEM_PROMPT` directly or a variable. Adjust accordingly.

### Step 3: Also update the neutral midpoint table

The neutral midpoint table (lines 419-433) references EB with a neutral score of 4. For proxy_delegated, EB neutral should be 0 (since weight is 0). Add a similar `.replace()`:

```python
        system = system.replace(
            "| Economic buyer engagement (11)               | 4             | S4+         |",
            "| Economic buyer engagement (0)                | 0             | N/A         |",
        )
```

### Step 4: Commit

```bash
git add sis/agents/synthesis.py
git commit -m "feat: Agent 10 uses culture-aware weight table for proxy-delegated deals"
```

---

## Task 7: Frontend — Upload Page Dropdown

**Files:**
- Modify: `frontend/src/app/upload/page.tsx`
- Modify: `frontend/src/lib/api.ts` (if needed for API call)

### Step 1: Add buying culture dropdown to DriveImportTab batch table

In `frontend/src/app/upload/page.tsx`, in the `DriveImportTab` component, add a "Culture" column to the batch configuration table (alongside Deal Type, AE Owner, etc.).

Find the batch row state management (around line 200-250) and add `buyingCulture: "direct"` to each row's initial state.

Add a `<Select>` component in the table columns (after the Deal Type column):

```tsx
<TableHead className="whitespace-normal">Culture</TableHead>
```

And in the row:

```tsx
<TableCell>
  <Select
    value={row.buyingCulture}
    onValueChange={(v) => updateRow(i, "buyingCulture", v)}
  >
    <SelectTrigger className="h-8 w-[130px]">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="direct">Direct</SelectItem>
      <SelectItem value="proxy_delegated">Proxy-Delegated</SelectItem>
    </SelectContent>
  </Select>
</TableCell>
```

### Step 2: Add to LocalFolderTab

Add the same dropdown to the local folder import tab's deal configuration section (around lines 843-888).

### Step 3: Pass through to API

Ensure `buyingCulture` is included in the submit payload. In the batch submit handler (line 266), include `buying_culture: row.buyingCulture` in the API payload.

### Step 4: Backend — Accept `buying_culture` in account creation

In `sis/api/routes/accounts.py`, add `buying_culture: str = "direct"` to the `AccountCreate` schema. In `sis/services/account_service.py`, pass it through to the Account model.

Also update the Gong import flow — in whatever service creates accounts during Drive/Local import, accept and store `buying_culture`.

### Step 5: Commit

```bash
git add frontend/src/app/upload/page.tsx sis/api/routes/accounts.py sis/services/account_service.py
git commit -m "feat: add buying culture dropdown to upload page"
```

---

## Task 8: Frontend — Methodology Page Update

**Files:**
- Modify: `frontend/src/app/methodology/page.tsx`

### Step 1: Add "Buying Culture Profiles" section

Add a new section after the Health Score section (id="health-score") and before Stages. Use the existing Table component pattern.

Section id: `buying-cultures`
Icon: `Globe` from lucide-react
Title: "Buying Culture Profiles"

Content: Side-by-side weight comparison table showing Direct vs Proxy-Delegated profiles, with an explanation paragraph.

```tsx
<section id="buying-cultures">
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center gap-2">
        <Globe className="h-5 w-5" />
        Buying Culture Profiles
      </CardTitle>
      <CardDescription>
        Health score weights adjust based on regional buying patterns.
        Proxy-delegated cultures (Japan, China, Korea) zero out Economic Buyer
        weight because the budget holder typically never appears on recorded calls.
      </CardDescription>
    </CardHeader>
    <CardContent>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="whitespace-normal">Component</TableHead>
            <TableHead className="text-center">Direct</TableHead>
            <TableHead className="text-center">Proxy-Delegated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* rows for each component with both weights */}
        </TableBody>
      </Table>
    </CardContent>
  </Card>
</section>
```

### Step 2: Update the NEVER Rules section

Remove the 3 deleted ceiling rules from the methodology display. They should no longer appear in the NEVER rules section.

### Step 3: Update the TOC

Add "Buying Culture Profiles" to the sticky right-rail table of contents.

### Step 4: Commit

```bash
git add frontend/src/app/methodology/page.tsx
git commit -m "feat: add buying culture profiles section to methodology page"
```

---

## Task 9: Frontend — Deal View Badge

**Files:**
- Modify: `frontend/src/app/deals/[id]/page.tsx` (deal detail page)
- Modify: `frontend/src/lib/pipeline-types.ts` (type definition)
- Modify: `frontend/src/components/data-table.tsx` (pipeline table, optional)

### Step 1: Add `buying_culture` to types

In `frontend/src/lib/pipeline-types.ts`, add to the `PipelineDeal` interface:

```typescript
buying_culture?: string | null;
```

And in the Assessment interface in `frontend/src/app/deals/[id]/page.tsx` (lines 57-95):

```typescript
buying_culture?: string | null;
```

### Step 2: Add badge to deal detail meta row

In the deal detail page's meta info row (around line 796), add a badge when culture is non-default:

```tsx
{assessment.buying_culture === "proxy_delegated" && (
  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
    Proxy-Delegated
  </Badge>
)}
```

### Step 3: Backend — Include `buying_culture` in API response

Ensure the API endpoint that returns deal/assessment data includes `buying_culture` from the associated Account row. Check the serializer/response schema for the deal detail endpoint.

### Step 4: Commit

```bash
git add frontend/src/app/deals/[id]/page.tsx frontend/src/lib/pipeline-types.ts
git commit -m "feat: show buying culture badge on deal detail page"
```

---

## Task 10: Backend — Wire `buying_culture` into NEVER Rules Engine

**Files:**
- Modify: `sis/orchestrator/pipeline.py` (where `check_all_never_rules` is called)

### Step 1: Verify NEVER rules still receive correct deal_type

The `check_all_never_rules` function already receives `deal_type`. After removing the 3 ceiling rules in Task 3, verify that the remaining rules still work correctly with no regressions.

```bash
cd /Users/roylevierez/Documents/Sales/SIS
.venv/bin/python -m pytest tests/test_never_rules.py -v
```

### Step 2: Run full test suite

```bash
.venv/bin/python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass. No regressions from the pipeline changes.

### Step 3: Commit (if any fixes needed)

```bash
git add -A
git commit -m "fix: resolve any test regressions from buying culture changes"
```

---

## Task 11: Backfill Existing Accounts

**Files:**
- Create: `scripts/backfill_buying_culture.py`

### Step 1: Write backfill script

```python
"""One-shot backfill: set buying_culture for existing accounts.

Usage:
    .venv/bin/python -m scripts.backfill_buying_culture

Reads from a mapping dict and updates accounts in the database.
"""
from sis.db.session import get_session
from sis.db.models import Account

# Mapping: account_name (case-insensitive) -> buying_culture
# Default is "direct" — only list proxy_delegated accounts
PROXY_DELEGATED_ACCOUNTS = [
    # To be filled in by Roy during backfill session
    # Example: "Xtool", "Makeblock", etc.
]

def main():
    proxy_set = {name.lower() for name in PROXY_DELEGATED_ACCOUNTS}
    with get_session() as session:
        accounts = session.query(Account).all()
        updated = 0
        for account in accounts:
            if account.account_name.lower() in proxy_set:
                account.buying_culture = "proxy_delegated"
                updated += 1
                print(f"  → {account.account_name}: proxy_delegated")
            else:
                print(f"  . {account.account_name}: direct (unchanged)")
        session.commit()
        print(f"\nDone. Updated {updated} accounts to proxy_delegated.")

if __name__ == "__main__":
    main()
```

### Step 2: Run interactively with Roy

List all accounts and ask Roy which are proxy_delegated:

```bash
.venv/bin/python -c "
from sis.db.session import get_session
from sis.db.models import Account
with get_session() as s:
    for a in s.query(Account).order_by(Account.account_name).all():
        print(f'  {a.account_name}')
"
```

Then update the `PROXY_DELEGATED_ACCOUNTS` list and run:

```bash
.venv/bin/python -m scripts.backfill_buying_culture
```

### Step 3: Commit

```bash
git add scripts/backfill_buying_culture.py
git commit -m "feat: add backfill script for buying culture on existing accounts"
```

---

## Task 12: End-to-End Verification

### Step 1: Run analysis on a proxy_delegated account

Pick one of the backfilled proxy accounts and run a fresh analysis:

```bash
.venv/bin/python -c "
from sis.services.analysis_service import analyze_account
result = analyze_account('<proxy_account_id>')
print(f'Health: {result[\"health_score\"]}')
print(f'EB weight used: check Agent 10 prompt')
"
```

### Step 2: Verify Agent 6 narrative mentions cultural context

Check that Agent 6's output narrative for the proxy deal mentions "proxy-delegated" or "culturally expected" rather than flagging EB absence as a gap.

### Step 3: Verify Agent 10 used correct weights

Check that the synthesis output for a proxy deal with no EB engagement doesn't penalize heavily. Compare health score before/after the change.

### Step 4: Verify NEVER rules don't fire on proxy deals with high health + no EB

The old `NEVER_HEALTH_WITHOUT_EB` rule would have capped this — verify it no longer fires.

### Step 5: Verify direct deals are unchanged

Run analysis on a direct-culture account and verify scores match pre-change behavior.

### Step 6: Final commit

```bash
git add -A
git commit -m "feat: buying culture profiles — end-to-end verified"
```
