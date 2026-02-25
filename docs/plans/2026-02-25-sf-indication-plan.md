# SF Indication Fields — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add SF indication fields (stage, forecast, close quarter, CP estimate) at upload time, snapshot them per analysis run, feed them to Agent 10 for gap analysis, and display the gap on deal detail + pipeline dashboard.

**Architecture:** SF fields live on Account (editable by user), get snapshotted to DealAssessment at analysis time. Agent 10 sees SF data only in Step 5 (after independent synthesis). Deterministic gap computation runs in code after Agent 10. Pipeline dashboard gets a gap indicator column; deal detail page gets a gap card.

**Tech Stack:** SQLAlchemy 2.0 + SQLite, FastAPI + Pydantic, Next.js 16 + React 19 + Tailwind CSS 4, shadcn/ui

**Design Doc:** `docs/plans/2026-02-25-sf-indication-design.md`

---

## Task 1: DB Schema — Account Model Changes

Rename `mrr_estimate` → `cp_estimate` on Account. Add 3 new SF columns.

**Files:**
- Modify: `sis/db/models.py:82-105`

**Step 1: Rename mrr_estimate column and add SF columns**

In `sis/db/models.py`, update the Account class:

```python
# Line 87: rename
cp_estimate = Column(Float, nullable=True)  # Contribution Profit estimate ($)

# After line 93 (after prior_contract_value), add:
sf_stage = Column(Integer, nullable=True)  # SF stage number (1-7)
sf_forecast_category = Column(Text, nullable=True)  # "Commit" / "Realistic" / "Upside" / "At Risk"
sf_close_quarter = Column(Text, nullable=True)  # Expected close quarter, e.g. "Q2 2026"
```

**Step 2: Run to verify no import errors**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.db.models import Account; print('OK')"
```

**Step 3: Commit**

```bash
git add sis/db/models.py
git commit -m "feat(db): rename mrr_estimate→cp_estimate, add SF columns to Account"
```

---

## Task 2: DB Schema — DealAssessment Snapshot + Gap Columns

Add 8 new columns to DealAssessment for SF snapshots and gap tracking.

**Files:**
- Modify: `sis/db/models.py:207-262`

**Step 1: Add snapshot and gap columns to DealAssessment**

After the `divergence_explanation` column (line 250), before `created_at`, add:

```python
    # SF indication snapshot (values at time of analysis run)
    sf_stage_at_run = Column(Integer, nullable=True)
    sf_forecast_at_run = Column(Text, nullable=True)
    sf_close_quarter_at_run = Column(Text, nullable=True)
    cp_estimate_at_run = Column(Float, nullable=True)

    # Gap analysis (computed post-pipeline)
    stage_gap_direction = Column(Text, nullable=True)  # "Aligned" / "SF-ahead" / "SIS-ahead"
    stage_gap_magnitude = Column(Integer, nullable=True)  # Absolute stage difference (0-6)
    forecast_gap_direction = Column(Text, nullable=True)  # "Aligned" / "SF-more-optimistic" / "SIS-more-optimistic"
    sf_gap_interpretation = Column(Text, nullable=True)  # Agent 10's natural language gap analysis
```

**Step 2: Verify import**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.db.models import DealAssessment; print([c.name for c in DealAssessment.__table__.columns if 'sf_' in c.name or 'gap' in c.name])"
```

**Step 3: Commit**

```bash
git add sis/db/models.py
git commit -m "feat(db): add SF snapshot + gap columns to DealAssessment"
```

---

## Task 3: Backend Schemas — Pydantic Models

Update all Pydantic schemas for the rename + new fields.

**Files:**
- Modify: `sis/api/schemas/accounts.py` (full file)
- Modify: `sis/api/schemas/analyses.py:94-102`
- Modify: `sis/api/schemas/dashboard.py` (grep for mrr_estimate)

**Step 1: Update accounts.py schemas**

In `AccountCreate` (line 26): rename `mrr_estimate` → `cp_estimate`, add SF fields:

```python
class AccountCreate(BaseModel):
    name: str
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    deal_type: str = "new_logo"
    prior_contract_value: Optional[float] = None
    owner_id: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
```

In `AccountUpdate` (line 35): same rename + add SF fields:

```python
class AccountUpdate(BaseModel):
    name: Optional[str] = None
    cp_estimate: Optional[float] = None
    team_lead: Optional[str] = None
    ae_owner: Optional[str] = None
    team_name: Optional[str] = None
    deal_type: Optional[str] = None
    prior_contract_value: Optional[float] = None
    owner_id: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
```

In `AccountSummary` (line 98): rename + add SF fields:

```python
    cp_estimate: Optional[float] = None
    # ... existing fields ...
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
```

In `AccountDetail` (line 121): rename + add SF fields:

```python
    cp_estimate: Optional[float] = None
    # ... existing fields ...
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
```

In `AssessmentDetail` (line 62): add gap fields:

```python
    # After divergence_explanation (line 87), add:
    sf_stage_at_run: Optional[int] = None
    sf_forecast_at_run: Optional[str] = None
    sf_close_quarter_at_run: Optional[str] = None
    cp_estimate_at_run: Optional[float] = None
    stage_gap_direction: Optional[str] = None
    stage_gap_magnitude: Optional[int] = None
    forecast_gap_direction: Optional[str] = None
    sf_gap_interpretation: Optional[str] = None
```

**Step 2: Update BatchItemRequest in analyses.py**

In `sis/api/schemas/analyses.py`, line 100: rename + add SF fields:

```python
class BatchItemRequest(BaseModel):
    """Single account in a batch analysis request."""
    account_name: str
    drive_path: str
    max_calls: int = 5
    deal_type: Optional[str] = None
    cp_estimate: Optional[float] = None
    owner_id: Optional[str] = None
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
```

**Step 3: Update dashboard schemas (grep for mrr_estimate)**

Check `sis/api/schemas/dashboard.py` and rename any `mrr_estimate` references to `cp_estimate`.

**Step 4: Verify schemas load**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.api.schemas.accounts import AccountCreate, AccountSummary, AssessmentDetail; print('OK')"
```

**Step 5: Commit**

```bash
git add sis/api/schemas/
git commit -m "feat(schemas): rename mrr→cp, add SF + gap fields to all Pydantic schemas"
```

---

## Task 4: Account Service — CRUD Updates

Update `create_account`, `update_account`, `list_accounts`, and `get_account_detail` for the rename + new fields.

**Files:**
- Modify: `sis/services/account_service.py`

**Step 1: Update UPDATABLE_FIELDS whitelist (line 19)**

```python
UPDATABLE_FIELDS = {"account_name", "cp_estimate", "ic_forecast_category", "team_lead", "ae_owner", "team_name", "deal_type", "prior_contract_value", "owner_id", "sf_stage", "sf_forecast_category", "sf_close_quarter"}
```

**Step 2: Update SORTABLE_FIELDS (line 22)**

```python
SORTABLE_FIELDS = {"account_name", "cp_estimate", "team_name", "created_at", "updated_at"}
```

**Step 3: Update create_account signature (line 25)**

```python
def create_account(
    name: str,
    cp_estimate: Optional[float] = None,
    team_lead: Optional[str] = None,
    ae_owner: Optional[str] = None,
    team: Optional[str] = None,
    deal_type: str = "new_logo",
    prior_contract_value: Optional[float] = None,
    owner_id: Optional[str] = None,
    sf_stage: Optional[int] = None,
    sf_forecast_category: Optional[str] = None,
    sf_close_quarter: Optional[str] = None,
) -> Account:
```

And in the Account constructor (line 55):

```python
        account = Account(
            account_name=name,
            cp_estimate=cp_estimate,
            team_lead=team_lead,
            ae_owner=ae_owner,
            team_name=team,
            deal_type=deal_type,
            prior_contract_value=prior_contract_value,
            owner_id=owner_id,
            sf_stage=sf_stage,
            sf_forecast_category=sf_forecast_category,
            sf_close_quarter=sf_close_quarter,
        )
```

**Step 4: Update list_accounts summary dict (line 174)**

```python
                "cp_estimate": acct.cp_estimate,
                # ... and add:
                "sf_stage": acct.sf_stage,
                "sf_forecast_category": acct.sf_forecast_category,
                "sf_close_quarter": acct.sf_close_quarter,
```

**Step 5: Update get_account_detail (line 306)**

```python
            "cp_estimate": account.cp_estimate,
            # ... and add:
            "sf_stage": account.sf_stage,
            "sf_forecast_category": account.sf_forecast_category,
            "sf_close_quarter": account.sf_close_quarter,
```

Also add SF gap fields to the assessment dict in get_account_detail (after line 335):

```python
                "sf_stage_at_run": latest_assessment.sf_stage_at_run,
                "sf_forecast_at_run": latest_assessment.sf_forecast_at_run,
                "sf_close_quarter_at_run": latest_assessment.sf_close_quarter_at_run,
                "cp_estimate_at_run": latest_assessment.cp_estimate_at_run,
                "stage_gap_direction": latest_assessment.stage_gap_direction,
                "stage_gap_magnitude": latest_assessment.stage_gap_magnitude,
                "forecast_gap_direction": latest_assessment.forecast_gap_direction,
                "sf_gap_interpretation": latest_assessment.sf_gap_interpretation,
```

**Step 6: Update accounts route create/update endpoints**

Check `sis/api/routes/accounts.py` for the create endpoint — it calls `create_account(name=..., mrr=...)`. Rename the `mrr` kwarg to `cp_estimate` and add SF field kwargs.

**Step 7: Verify**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.services.account_service import create_account; print('OK')"
```

**Step 8: Commit**

```bash
git add sis/services/account_service.py sis/api/routes/accounts.py
git commit -m "feat(service): update account CRUD for cp_estimate rename + SF fields"
```

---

## Task 5: Synthesis Agent — SFGapAnalysis Model + Step 5 Prompt

Add the SFGapAnalysis sub-model, optional field on SynthesisOutput, and sf_data parameter to build_call.

**Files:**
- Modify: `sis/agents/synthesis.py`

**Step 1: Add SFGapAnalysis model after SynthesisConfidence (line 88)**

```python
class SFGapAnalysis(BaseModel):
    """Agent 10's interpretation of SIS vs SF gaps (Step 5)."""
    stage_gap_direction: str = Field(description="'Aligned' / 'SF-ahead' / 'SIS-ahead'")
    stage_gap_interpretation: str = Field(description="1-2 sentences on stage gap")
    forecast_gap_direction: str = Field(description="'Aligned' / 'SF-more-optimistic' / 'SIS-more-optimistic'")
    forecast_gap_interpretation: str = Field(description="1-2 sentences on forecast gap")
    overall_gap_assessment: str = Field(description="2-3 sentences for the VP Sales")
```

**Step 2: Add optional field on SynthesisOutput (after sparse_data_agents, line 145)**

```python
    # 5. SF Gap Analysis (only when SF data provided)
    sf_gap_analysis: Optional[SFGapAnalysis] = Field(
        default=None,
        description="Gap analysis between SIS independent assessment and Salesforce values. Only present when SF data was provided.",
    )
```

Add `from typing import Optional` to imports if not already there (it's already imported on line 17).

**Step 3: Add Step 5 section to SYSTEM_PROMPT (before "## Output Format" on line 344)**

```
### Step 5: SALESFORCE GAP ANALYSIS (conditional)
If SF indication data is provided after the agent outputs, compare your independent assessment from Steps 1-4 against the Salesforce values. Do NOT revise your deal memo, health score, forecast, or any Step 1-4 output. Analyze the gaps only.

Produce an `sf_gap_analysis` object with:
- stage_gap_direction: "Aligned" if stages match, "SF-ahead" if SF stage > your inferred stage, "SIS-ahead" if your inferred stage > SF stage
- stage_gap_interpretation: 1-2 sentences explaining what the gap means
- forecast_gap_direction: "Aligned" if forecast categories match, "SF-more-optimistic" if SF is more optimistic, "SIS-more-optimistic" if SIS is more optimistic
- forecast_gap_interpretation: 1-2 sentences explaining the forecast gap
- overall_gap_assessment: 2-3 sentences for the VP Sales summarizing the SIS-vs-SF picture

If no SF data is provided, omit sf_gap_analysis entirely.
```

**Step 4: Update build_call signature (line 348) to accept sf_data**

```python
def build_call(
    upstream_outputs: dict[str, dict],
    stage_context: dict,
    sf_data: dict | None = None,
) -> dict:
```

Update the docstring accordingly.

**Step 5: Append SF data section to user_prompt (after line 402, before the final instruction)**

Before the final `parts.append("Based on all 9 agent outputs above...")` block, add:

```python
    # Append SF indication data for Step 5 gap analysis (if provided)
    if sf_data:
        parts.append("\n## SALESFORCE INDICATION DATA (for Step 5 only)")
        parts.append("Compare your independent assessment from Steps 1-4 against these Salesforce")
        parts.append("values provided by the rep. Do NOT revise your deal memo, health score, or")
        parts.append("forecast. Analyze the gaps only.\n")
        if sf_data.get("sf_stage") is not None:
            stage_names = {1: "Qualify", 2: "Discover", 3: "Scope", 4: "Validate", 5: "Negotiate", 6: "Prove", 7: "Close"}
            sf_stage_name = stage_names.get(sf_data["sf_stage"], f"Stage {sf_data['sf_stage']}")
            parts.append(f"SF Stage: {sf_stage_name} ({sf_data['sf_stage']})")
        if sf_data.get("sf_forecast_category"):
            parts.append(f"SF Forecast Category: {sf_data['sf_forecast_category']}")
        if sf_data.get("sf_close_quarter"):
            parts.append(f"SF Close Quarter: {sf_data['sf_close_quarter']}")
        if sf_data.get("cp_estimate") is not None:
            parts.append(f"CP Estimate: ${sf_data['cp_estimate']:,.0f}")
        parts.append("")
```

**Step 6: Update run_synthesis to pass sf_data (line 423)**

```python
def run_synthesis(
    upstream_outputs: dict[str, dict],
    stage_context: dict,
    sf_data: dict | None = None,
) -> AgentResult[SynthesisOutput]:
    """Run Agent 10: Synthesis."""
    return run_agent(**build_call(upstream_outputs, stage_context, sf_data))
```

**Step 7: Verify**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.agents.synthesis import build_call, SFGapAnalysis; print('OK')"
```

**Step 8: Commit**

```bash
git add sis/agents/synthesis.py
git commit -m "feat(agent10): add SFGapAnalysis model, Step 5 prompt, sf_data param"
```

---

## Task 6: Pipeline + Analysis Service — SF Data Flow + Gap Computation

Pass sf_data through the pipeline, snapshot SF fields to DealAssessment, compute deterministic gap.

**Files:**
- Modify: `sis/orchestrator/pipeline.py:137-153, 457`
- Modify: `sis/services/analysis_service.py:53-124, 190-297`

**Step 1: Add sf_data parameter to pipeline.run() and run_async()**

In `pipeline.py`, update both signatures:

```python
    def run(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
        deal_context: dict | None = None,
        sf_data: dict | None = None,
    ) -> PipelineResult:
        """Run the full pipeline synchronously (wraps async version)."""
        return asyncio.run(self.run_async(account_id, transcript_texts, timeline_entries, deal_context, sf_data))

    async def run_async(
        self,
        account_id: str,
        transcript_texts: list[str],
        timeline_entries: list[str] | None = None,
        deal_context: dict | None = None,
        sf_data: dict | None = None,
    ) -> PipelineResult:
```

**Step 2: Pass sf_data to synthesis build_call (line 457)**

Change:
```python
agent10_call = synthesis_build_call(result.agent_outputs, stage_context)
```
To:
```python
agent10_call = synthesis_build_call(result.agent_outputs, stage_context, sf_data)
```

**Step 3: Read SF fields in analysis_service.analyze_account (after line 80)**

Inside the `with get_session()` block in `analyze_account`, read SF fields:

```python
        # Read SF indication fields for gap analysis (Agent 10 Step 5 only)
        sf_data = None
        if any([account.sf_stage, account.sf_forecast_category, account.sf_close_quarter, account.cp_estimate]):
            sf_data = {
                "sf_stage": account.sf_stage,
                "sf_forecast_category": account.sf_forecast_category,
                "sf_close_quarter": account.sf_close_quarter,
                "cp_estimate": account.cp_estimate,
            }
```

**Step 4: Pass sf_data to pipeline.run (line 106)**

Change:
```python
    result = pipeline.run(account_id, transcript_texts, deal_context=deal_context)
```
To:
```python
    result = pipeline.run(account_id, transcript_texts, deal_context=deal_context, sf_data=sf_data)
```

Do the same for `analyze_account_async` (line 169):
```python
    result = await pipeline.run_async(account_id, transcript_texts, deal_context=deal_context, sf_data=sf_data)
```

**Step 5: Store sf_data on PipelineResult for persistence**

Add `sf_data: dict | None = None` to PipelineResult dataclass (line 81-98).

In pipeline.py run_async, store sf_data on result:
```python
result.sf_data = sf_data
```

**Step 6: Snapshot SF fields + compute gap in _persist_pipeline_result (after line 293)**

After creating the DealAssessment object but before `session.add(assessment)`, add snapshot fields:

```python
            # Snapshot SF indication fields at run time
            if result.sf_data:
                assessment.sf_stage_at_run = result.sf_data.get("sf_stage")
                assessment.sf_forecast_at_run = result.sf_data.get("sf_forecast_category")
                assessment.sf_close_quarter_at_run = result.sf_data.get("sf_close_quarter")
                assessment.cp_estimate_at_run = result.sf_data.get("cp_estimate")

            # Deterministic gap computation
            if result.sf_data and result.sf_data.get("sf_stage") is not None:
                sf_stage = result.sf_data["sf_stage"]
                sis_stage = syn.get("inferred_stage", 0)
                if sf_stage == sis_stage:
                    assessment.stage_gap_direction = "Aligned"
                elif sf_stage > sis_stage:
                    assessment.stage_gap_direction = "SF-ahead"
                else:
                    assessment.stage_gap_direction = "SIS-ahead"
                assessment.stage_gap_magnitude = abs(sf_stage - sis_stage)

            if result.sf_data and result.sf_data.get("sf_forecast_category"):
                forecast_rank = {"At Risk": 1, "Upside": 2, "Realistic": 3, "Commit": 4}
                sf_rank = forecast_rank.get(result.sf_data["sf_forecast_category"], 0)
                sis_rank = forecast_rank.get(syn.get("forecast_category", ""), 0)
                if sf_rank == sis_rank:
                    assessment.forecast_gap_direction = "Aligned"
                elif sf_rank > sis_rank:
                    assessment.forecast_gap_direction = "SF-more-optimistic"
                else:
                    assessment.forecast_gap_direction = "SIS-more-optimistic"

            # Store Agent 10's gap interpretation if present
            sf_gap = syn.get("sf_gap_analysis")
            if sf_gap:
                assessment.sf_gap_interpretation = sf_gap.get("overall_gap_assessment", "")
```

**Step 7: Also update sf_data reads in analyze_account_async (line 127-187)**

Mirror the sf_data reading logic from Step 3 into the async version.

**Step 8: Update resynthesize() to pass sf_data (line 678)**

In `resynthesize()`, read SF fields from the account and pass to synthesis:

```python
    # Read SF data for gap analysis
    with get_session() as session:
        acct = session.query(Account).filter_by(id=account_id).one_or_none()
        sf_data = None
        if acct and any([acct.sf_stage, acct.sf_forecast_category, acct.sf_close_quarter, acct.cp_estimate]):
            sf_data = {
                "sf_stage": acct.sf_stage,
                "sf_forecast_category": acct.sf_forecast_category,
                "sf_close_quarter": acct.sf_close_quarter,
                "cp_estimate": acct.cp_estimate,
            }

    call_kwargs = synthesis_build_call(agent_outputs, stage_context, sf_data)
```

**Step 9: Verify**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.services.analysis_service import analyze_account; print('OK')"
```

**Step 10: Commit**

```bash
git add sis/orchestrator/pipeline.py sis/services/analysis_service.py
git commit -m "feat(pipeline): pass sf_data to Agent 10, snapshot + compute gap on DealAssessment"
```

---

## Task 7: Batch Worker — Pass SF Fields Through

Update batch item processing to pass SF fields when creating accounts.

**Files:**
- Modify: `sis/api/routes/analyses.py:54-138`

**Step 1: Update _run_batch_item to pass SF fields (line 86-93)**

Change the `create_account` call:

```python
            acct_obj = create_account(
                name=item_data["account_name"],
                deal_type=normalize_deal_type(item_data.get("deal_type")),
                cp_estimate=item_data.get("cp_estimate"),
                owner_id=item_data.get("owner_id"),
                sf_stage=item_data.get("sf_stage"),
                sf_forecast_category=item_data.get("sf_forecast_category"),
                sf_close_quarter=item_data.get("sf_close_quarter"),
            )
```

Also, if the account already exists, update its SF fields:

```python
        if account_id:
            # Update existing account's SF fields if provided
            from sis.services.account_service import update_account
            sf_updates = {}
            for field in ["sf_stage", "sf_forecast_category", "sf_close_quarter", "cp_estimate"]:
                if item_data.get(field) is not None:
                    sf_updates[field] = item_data[field]
            if sf_updates:
                update_account(account_id, **sf_updates)
```

**Step 2: Verify**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.api.routes.analyses import router; print('OK')"
```

**Step 3: Commit**

```bash
git add sis/api/routes/analyses.py
git commit -m "feat(batch): pass SF fields through batch item processing"
```

---

## Task 8: Backend Remaining — mrr_estimate Rename in Services

Rename all remaining `mrr_estimate` references in backend services.

**Files:**
- Modify: `sis/services/dashboard_service.py` (grep for mrr_estimate)
- Modify: `sis/services/export_service.py` (grep for mrr_estimate)
- Modify: `sis/services/query_service.py` (grep for mrr_estimate)
- Modify: `sis/services/forecast_data_service.py` (grep for mrr_estimate)
- Modify: `sis/api/routes/gdrive.py` (grep for mrr_estimate)
- Modify: `scripts/seed_db.py` (grep for mrr_estimate)
- Modify: `sis/api/schemas/dashboard.py` (grep for mrr_estimate)

**Step 1: Grep and rename all mrr_estimate → cp_estimate in backend Python files**

For each file returned by `grep -rn "mrr_estimate" sis/ scripts/`:
- Replace `mrr_estimate` with `cp_estimate`
- Replace `mrr=` parameter names with `cp_estimate=` where applicable
- Leave `docs/` and `planning/` files unchanged (historical reference)
- Leave `alembic/` unchanged (reflects old schema)

**Step 2: Verify backend loads**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -c "from sis.services import dashboard_service, export_service; print('OK')"
```

**Step 3: Commit**

```bash
git add sis/ scripts/
git commit -m "refactor(backend): complete mrr_estimate→cp_estimate rename across all services"
```

---

## Task 9: Frontend Types — api-types.ts + api.ts Updates

Update TypeScript types for the rename + new SF fields.

**Files:**
- Modify: `frontend/src/lib/api-types.ts`
- Modify: `frontend/src/lib/api.ts` (if needed)
- Modify: `frontend/src/lib/pipeline-types.ts`
- Modify: `frontend/src/lib/types.ts`

**Step 1: Update api-types.ts**

In `Account` interface (line 22): `mrr_estimate` → `cp_estimate`, add SF fields:

```typescript
export interface Account {
  id: string;
  account_name: string;
  cp_estimate: number | null;
  // ... existing fields ...
  sf_stage: number | null;
  sf_forecast_category: string | null;
  sf_close_quarter: string | null;
  [key: string]: unknown;
}
```

In `AccountCreate` (line 38): rename + add SF fields:

```typescript
export interface AccountCreate {
  account_name: string;
  cp_estimate?: number;
  team_lead?: string;
  ae_owner?: string;
  sf_stage?: number;
  sf_forecast_category?: string;
  sf_close_quarter?: string;
}
```

In `DivergenceItem` (line 143): rename `mrr_estimate` → `cp_estimate`

In `PipelineInsight` (line 160): rename `mrr_estimate` → `cp_estimate`

In `ForecastData` (line 313): rename `mrr_estimate` → `cp_estimate`

In `TeamRollupHierarchyDeal` (line 380): rename `mrr_estimate` → `cp_estimate`

In `BatchItemRequest` (line 436): rename + add SF fields:

```typescript
export interface BatchItemRequest {
  account_name: string;
  drive_path: string;
  max_calls: number;
  deal_type?: string;
  cp_estimate?: number;
  owner_id?: string;
  sf_stage?: number;
  sf_forecast_category?: string;
  sf_close_quarter?: string;
}
```

**Step 2: Update pipeline-types.ts and types.ts**

Rename all `mrr_estimate` → `cp_estimate` in these files.

**Step 3: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && git add src/lib/
git commit -m "feat(types): rename mrr→cp, add SF + gap types to frontend"
```

---

## Task 10: Frontend — mrr_estimate → cp_estimate Rename Across Pages

Rename all `mrr_estimate` references to `cp_estimate` across frontend components and pages. Update display labels from "MRR" to "CP Estimate".

**Files (from grep results):**
- Modify: `frontend/src/components/data-table.tsx`
- Modify: `frontend/src/components/attention-strip.tsx`
- Modify: `frontend/src/components/team-forecast-grid.tsx`
- Modify: `frontend/src/app/forecast/page.tsx`
- Modify: `frontend/src/app/team-rollup/page.tsx`
- Modify: `frontend/src/app/deals/[id]/page.tsx`
- Modify: `frontend/src/app/divergence/page.tsx`
- Modify: `frontend/src/app/meeting-prep/page.tsx`
- Modify: `frontend/src/__tests__/mocks/handlers.ts`
- Modify: `frontend/src/__tests__/pipeline-overview.test.tsx`

**Step 1: Global search-replace in each file**

For each file:
- Replace `mrr_estimate` with `cp_estimate` (property access)
- Replace display text "MRR" with "CP Est." or "CP Estimate" as appropriate
- Replace `$XXK` formatting patterns to keep the same dollar formatting

**Key display label changes:**
- Column headers: "MRR" → "CP Est."
- Detail views: "MRR Estimate" → "CP Estimate"
- Formatting logic stays the same (just the field name changes)

**Step 2: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | head -30
```

**Step 3: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && git add src/
git commit -m "refactor(frontend): rename mrr_estimate→cp_estimate across all pages"
```

---

## Task 11: Upload UX — SF Fields on Single Upload

Add SF Indication section to the single upload (paste/local folder) flow.

**Files:**
- Modify: `frontend/src/app/upload/page.tsx`

**Step 1: Add SF state variables**

Near the existing deal configuration state (around line 100-120), add:

```typescript
const [sfStage, setSfStage] = useState<number | undefined>();
const [sfForecast, setSfForecast] = useState<string | undefined>();
const [sfCloseQuarter, setSfCloseQuarter] = useState<string | undefined>();
```

**Step 2: Add SF Indication section in the Local Folder tab**

After the existing Deal Configuration section (around line 788), add a new section:

```tsx
{/* SF Indication */}
<div className="space-y-3">
  <div>
    <h4 className="text-sm font-medium">SF Indication</h4>
    <p className="text-xs text-muted-foreground">Salesforce indication at day of last analysis</p>
  </div>
  <div className="grid grid-cols-2 gap-3">
    <div className="space-y-1">
      <Label className="text-xs">SF Stage</Label>
      <Select value={sfStage?.toString() ?? ""} onValueChange={(v) => setSfStage(v ? parseInt(v) : undefined)}>
        <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select stage" /></SelectTrigger>
        <SelectContent>
          {[
            { value: "1", label: "Qualify" },
            { value: "2", label: "Discover" },
            { value: "3", label: "Scope" },
            { value: "4", label: "Validate" },
            { value: "5", label: "Negotiate" },
            { value: "6", label: "Prove" },
            { value: "7", label: "Close" },
          ].map((s) => (
            <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
    <div className="space-y-1">
      <Label className="text-xs">SF Forecast</Label>
      <Select value={sfForecast ?? ""} onValueChange={(v) => setSfForecast(v || undefined)}>
        <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select forecast" /></SelectTrigger>
        <SelectContent>
          {["Commit", "Realistic", "Upside", "At Risk"].map((f) => (
            <SelectItem key={f} value={f}>{f}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
    <div className="space-y-1">
      <Label className="text-xs">Close Quarter</Label>
      <Select value={sfCloseQuarter ?? ""} onValueChange={(v) => setSfCloseQuarter(v || undefined)}>
        <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select quarter" /></SelectTrigger>
        <SelectContent>
          {generateCloseQuarters().map((q) => (
            <SelectItem key={q} value={q}>{q}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
    <div className="space-y-1">
      <Label className="text-xs">CP Estimate ($)</Label>
      <Input
        type="number"
        className="h-8 text-xs"
        placeholder="e.g. 350000"
        value={cpEstimate ?? ""}
        onChange={(e) => setCpEstimate(e.target.value ? parseFloat(e.target.value) : undefined)}
      />
    </div>
  </div>
</div>
```

**Step 3: Add quarter generator helper**

```typescript
function generateCloseQuarters(): string[] {
  const now = new Date();
  const currentQ = Math.ceil((now.getMonth() + 1) / 3);
  const currentY = now.getFullYear();
  const quarters: string[] = [];
  for (let i = 0; i < 5; i++) {
    const q = ((currentQ - 1 + i) % 4) + 1;
    const y = currentY + Math.floor((currentQ - 1 + i) / 4);
    quarters.push(`Q${q} ${y}`);
  }
  return quarters;
}
```

**Step 4: Pass SF fields to API when creating account**

In the account create call, include the SF fields:

```typescript
sf_stage: sfStage,
sf_forecast_category: sfForecast,
sf_close_quarter: sfCloseQuarter,
```

**Step 5: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | head -30
```

**Step 6: Commit**

```bash
git add frontend/src/app/upload/page.tsx
git commit -m "feat(upload): add SF indication fields to single upload flow"
```

---

## Task 12: Upload UX — SF Fields on Batch Upload Table

Add 4 new per-row columns to the batch upload table for SF indication.

**Files:**
- Modify: `frontend/src/app/upload/page.tsx`

**Step 1: Update BatchRow interface (line 133)**

Add SF fields:

```typescript
interface BatchRow {
  // ... existing fields ...
  sfStage?: number;
  sfForecast?: string;
  sfCloseQuarter?: string;
  cpEstimate?: number;
}
```

**Step 2: Add columns to batch table header**

After the existing columns (Deal Type, IC), add:

```tsx
<TableHead className="text-xs w-16">Stg</TableHead>
<TableHead className="text-xs w-20">Fct</TableHead>
<TableHead className="text-xs w-20">Q</TableHead>
<TableHead className="text-xs w-20">$</TableHead>
```

**Step 3: Add per-row inputs for checked rows**

For each checked row, add inline dropdowns/inputs (compact):

```tsx
{/* SF Stage */}
<TableCell className="p-1">
  {row.checked ? (
    <Select value={row.sfStage?.toString() ?? ""} onValueChange={(v) => updateBatchRow(i, { sfStage: v ? parseInt(v) : undefined })}>
      <SelectTrigger className="h-7 text-xs w-16"><SelectValue placeholder="—" /></SelectTrigger>
      <SelectContent>
        {[{v:"1",l:"Qual"},{v:"2",l:"Disc"},{v:"3",l:"Scope"},{v:"4",l:"Val"},{v:"5",l:"Neg"},{v:"6",l:"Prove"},{v:"7",l:"Close"}].map(s => (
          <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  ) : null}
</TableCell>

{/* SF Forecast */}
<TableCell className="p-1">
  {row.checked ? (
    <Select value={row.sfForecast ?? ""} onValueChange={(v) => updateBatchRow(i, { sfForecast: v || undefined })}>
      <SelectTrigger className="h-7 text-xs w-20"><SelectValue placeholder="—" /></SelectTrigger>
      <SelectContent>
        {["Commit","Realistic","Upside","At Risk"].map(f => (
          <SelectItem key={f} value={f}>{f}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  ) : null}
</TableCell>

{/* Close Quarter */}
<TableCell className="p-1">
  {row.checked ? (
    <Select value={row.sfCloseQuarter ?? ""} onValueChange={(v) => updateBatchRow(i, { sfCloseQuarter: v || undefined })}>
      <SelectTrigger className="h-7 text-xs w-20"><SelectValue placeholder="—" /></SelectTrigger>
      <SelectContent>
        {generateCloseQuarters().map(q => (
          <SelectItem key={q} value={q}>{q}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  ) : null}
</TableCell>

{/* CP Estimate */}
<TableCell className="p-1">
  {row.checked ? (
    <Input
      type="number"
      className="h-7 text-xs w-20"
      placeholder="$"
      value={row.cpEstimate ?? ""}
      onChange={(e) => updateBatchRow(i, { cpEstimate: e.target.value ? parseFloat(e.target.value) : undefined })}
    />
  ) : null}
</TableCell>
```

**Step 4: Pass SF fields in handleBatchSubmit (line 244)**

In the items mapping, include SF fields:

```typescript
sf_stage: row.sfStage,
sf_forecast_category: row.sfForecast,
sf_close_quarter: row.sfCloseQuarter,
cp_estimate: row.cpEstimate,
```

**Step 5: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | head -30
```

**Step 6: Commit**

```bash
git add frontend/src/app/upload/page.tsx
git commit -m "feat(upload): add SF indication columns to batch upload table"
```

---

## Task 13: Deal Detail Page — SF Gap Card

Add a new card below the assessment card on the deal detail page showing the SF vs SIS gap analysis.

**Files:**
- Modify: `frontend/src/app/deals/[id]/page.tsx`

**Step 1: Create SFGapCard component (inline or separate)**

Add a component that displays when gap data exists on the assessment:

```tsx
function SFGapCard({ assessment, account }: { assessment: any; account: any }) {
  if (!assessment?.sf_stage_at_run && !assessment?.sf_forecast_at_run) return null;

  const stageNames: Record<number, string> = {1:"Qualify",2:"Discover",3:"Scope",4:"Validate",5:"Negotiate",6:"Prove",7:"Close"};

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Salesforce Gap Analysis</CardTitle>
        <p className="text-xs text-muted-foreground">SF indication at day of last analysis</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Stage gap row */}
        {assessment.sf_stage_at_run != null && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Stage</span>
            <div className="flex items-center gap-2">
              <span>SIS: {stageNames[assessment.inferred_stage] ?? assessment.inferred_stage} ({assessment.inferred_stage})</span>
              <span className="text-muted-foreground">vs</span>
              <span>SF: {stageNames[assessment.sf_stage_at_run] ?? assessment.sf_stage_at_run} ({assessment.sf_stage_at_run})</span>
              {assessment.stage_gap_direction && assessment.stage_gap_direction !== "Aligned" && (
                <span className="font-medium">
                  {assessment.stage_gap_direction === "SF-ahead"
                    ? `SF +${assessment.stage_gap_magnitude}`
                    : `SIS +${assessment.stage_gap_magnitude}`}
                </span>
              )}
              {assessment.stage_gap_direction === "Aligned" && <span>=</span>}
            </div>
          </div>
        )}

        {/* Forecast gap row */}
        {assessment.sf_forecast_at_run && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Forecast</span>
            <div className="flex items-center gap-2">
              <span>AI: {assessment.ai_forecast_category}</span>
              <span className="text-muted-foreground">vs</span>
              <span>SF: {assessment.sf_forecast_at_run}</span>
              {assessment.forecast_gap_direction && assessment.forecast_gap_direction !== "Aligned" && (
                <span className="font-medium">
                  {assessment.forecast_gap_direction === "SF-more-optimistic" ? "SF > AI" : "AI > SF"}
                </span>
              )}
              {assessment.forecast_gap_direction === "Aligned" && <span>=</span>}
            </div>
          </div>
        )}

        {/* Close quarter + CP estimate */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {assessment.sf_close_quarter_at_run && <span>Close Q: {assessment.sf_close_quarter_at_run}</span>}
          {assessment.cp_estimate_at_run != null && (
            <span>CP Est: ${assessment.cp_estimate_at_run >= 1000 ? `${(assessment.cp_estimate_at_run / 1000).toFixed(0)}K` : assessment.cp_estimate_at_run.toLocaleString()}</span>
          )}
        </div>

        {/* Agent 10's interpretation */}
        {assessment.sf_gap_interpretation && (
          <p className="text-sm italic border-l-2 border-muted pl-3 mt-2">
            {assessment.sf_gap_interpretation}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

**Step 2: Add SFGapCard to the deal detail page layout**

After the existing assessment card, add:

```tsx
<SFGapCard assessment={account.assessment} account={account} />
```

**Step 3: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | head -30
```

**Step 4: Commit**

```bash
git add frontend/src/app/deals/[id]/page.tsx
git commit -m "feat(deal-detail): add SF Gap Analysis card"
```

---

## Task 14: Pipeline Dashboard — Gap Indicator Column

Add an "SF Gap" column to the pipeline dashboard table showing directional indicators.

**Files:**
- Modify: `frontend/src/app/pipeline/page.tsx`

**Step 1: Add SF Gap column header**

In the pipeline table headers, add after the existing columns:

```tsx
<TableHead className="text-xs">SF Gap</TableHead>
```

**Step 2: Add SF Gap cell renderer**

For each deal row, render a compact gap indicator:

```tsx
<TableCell className="text-xs whitespace-nowrap">
  {deal.stage_gap_direction ? (
    <span title={`Stage: ${deal.stage_gap_direction}${deal.stage_gap_magnitude ? ` (${deal.stage_gap_magnitude})` : ''}, Forecast: ${deal.forecast_gap_direction ?? 'N/A'}`}>
      {deal.stage_gap_direction === "Aligned" && deal.forecast_gap_direction === "Aligned" ? "=" : ""}
      {deal.stage_gap_direction === "SF-ahead" ? `SF +${deal.stage_gap_magnitude}` : ""}
      {deal.stage_gap_direction === "SIS-ahead" ? `SIS +${deal.stage_gap_magnitude}` : ""}
      {deal.stage_gap_direction === "Aligned" && deal.forecast_gap_direction !== "Aligned" ? (
        deal.forecast_gap_direction === "SF-more-optimistic" ? "SF > AI" : "AI > SF"
      ) : null}
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  )}
</TableCell>
```

**Note:** The pipeline dashboard data comes from `list_accounts()` which uses the latest DealAssessment. The gap fields need to be included in the summary response. Check that `list_accounts` in `account_service.py` (Task 4) includes the gap fields from the latest assessment.

**Step 3: Update list_accounts to include gap fields (if not done in Task 4)**

In `account_service.py` `list_accounts()`, add to the assessment summary:

```python
                    "stage_gap_direction": latest_assessment.stage_gap_direction,
                    "stage_gap_magnitude": latest_assessment.stage_gap_magnitude,
                    "forecast_gap_direction": latest_assessment.forecast_gap_direction,
```

**Step 4: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | head -30
```

**Step 5: Commit**

```bash
git add frontend/src/app/pipeline/page.tsx
git commit -m "feat(dashboard): add SF Gap indicator column to pipeline table"
```

---

## Task 15: DB Recreation + Smoke Test

Recreate the SQLite DB (POC can be recreated), run the backend, and verify everything loads.

**Files:**
- No new files

**Step 1: Recreate DB**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
rm -f sis.db  # POC DB can be recreated
python -c "from sis.db.session import engine; from sis.db.models import Base; Base.metadata.create_all(engine); print('DB recreated')"
```

**Step 2: Re-seed if needed**

```bash
python scripts/seed_db.py
```

**Step 3: Verify backend starts**

```bash
cd /Users/roylevierez/Documents/Sales/SIS && python -m uvicorn sis.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/api/accounts/ | python -m json.tool | head -5
kill %1
```

**Step 4: Verify frontend builds**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build
```

**Step 5: Commit any remaining fixes**

```bash
git add -A && git status
git commit -m "chore: DB recreation + smoke test pass"
```

---

## Task Dependencies

```
Task 1 (Account model) ─┐
Task 2 (Assessment model) ─┤
                           ├─► Task 3 (Schemas) ─► Task 4 (Account Service) ─► Task 7 (Batch Worker)
                           │                                                  ├─► Task 8 (Backend rename)
Task 5 (Synthesis Agent) ──┤
                           ├─► Task 6 (Pipeline + Analysis Service)
                           │
                           └─► Task 9 (Frontend types) ─► Task 10 (Frontend rename)
                                                        ├─► Task 11 (Single upload SF)
                                                        ├─► Task 12 (Batch upload SF)
                                                        ├─► Task 13 (Deal gap card)
                                                        └─► Task 14 (Pipeline gap column)

Task 15 (DB recreation + smoke test) runs after all tasks.
```

## Parallel Execution Opportunities

- Tasks 1+2 can run together (both modify models.py but different sections)
- Task 5 (Synthesis) is independent of Tasks 1-4
- Tasks 11+12 (upload SF fields) can run after Task 9
- Tasks 13+14 (gap display) can run after Task 9

## Estimated Scope

- **Backend:** ~15 files modified
- **Frontend:** ~15 files modified
- **New files:** 0 (all modifications to existing files)
- **Lines changed:** ~500 backend, ~400 frontend
