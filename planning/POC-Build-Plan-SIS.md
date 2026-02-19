# POC Build Plan: Riskified Sales Intelligence System (SIS)

**Version:** 1.1
**Date:** February 19, 2026
**Author:** Product Manager (AI-assisted)
**PRD Reference:** PRD v1.5 — Sections 6-12, Data Model
**Status:** Approved by VP Sales — Ready for Implementation

---

## Consolidated Product Decisions

### Architecture & Stack Decisions

| Decision | Answer |
|----------|--------|
| LLM Provider | Anthropic (Claude) |
| Forecast categories | All 6 from day one |
| Dashboard vs. Chat | Both, best version, from day one |
| POC accounts | 15-20 accounts |
| Cold start data | 8-10 historical closed deals (partial) |
| Sample transcripts | Available this week |
| IC forecast entry | VP enters manually for all deals |
| Tech stack | Python, Streamlit, SQLite -> PostgreSQL |
| Call types | External calls only for now |
| Access model | TLs see own deals, VP sees all |

### Feature Deep-Dive Decisions (Q&A Session — 15 decisions)

| # | Feature Area | Decision |
|---|---|---|
| 1 | Deal Brief format | Build all 3 formats (structured, narrative, inspection questions). Select after seeing output quality. |
| 2 | Chat query patterns | All three equally: deal-specific, cross-pipeline filtering, forecast/comparison |
| 3 | Divergence handling | All modes: group review, private 1:1, data-driven, pattern tracking over time |
| 4 | Deal detail UX | Synthesis-first with expandable per-agent detail |
| 5 | Health score UX | Component breakdown visual + one-line reason sentence |
| 6 | Agent 9 focus | All four signal types: external/market, relationship, stall-as-progress, technical risk |
| 7 | Feedback categories | 5 options (add "recent change not captured") + free text per each category |
| 8 | Default dashboard view | Grouped by TL/team, then by forecast category (two-level) |
| 9 | Recommended actions | Carried into next analysis + exportable to Salesforce |
| 10 | Transcript cap behavior | Archive old transcripts, make them available to conversational AI |
| 11 | L&D / Rep profiles | **Upgraded to P0** — basic rep scorecard, critical for CRO buy-in |
| 12 | Alerts | **Upgraded to P0** — daily email digest + Slack alerts for critical changes |
| 13 | Deal memo style | Both versions (TL insider + leadership briefing) in POC. Adaptive auto-detect post-POC. |
| 14 | Missing feature | **Meeting prep mode** — pre-call brief (new P0-24) |
| 15 | Data load approach | Paste one transcript at a time. Keep the UI fast and simple. |

---

## 1. 8-Week Build Sequence

### Week 1-2: Foundation & First Agent

**Goal**: Infrastructure running. First agent (Stage Classifier) producing output. Data model deployed. Prompt system working.

| Deliverable | PRD Reqs | Details |
|---|---|---|
| **Data model (SQLite + SQLAlchemy)** | Sec 8 | All 10 tables from PRD data model. Accounts, Transcripts, AgentAnalyses, DealAssessments, ScoreFeedback, CalibrationLog, etc. Migration-ready schema. |
| **Transcript preprocessor** | P0-1 | Speaker normalization, filler removal, 8K token cap per transcript. Handles Gong export format (format TBD pending OQ1 resolution). |
| **Agent execution framework** | P0-2, Sec 7.2 | Orchestrator: sequential-parallel flow (Agent 1 -> 2-8 parallel -> 9 -> 10). asyncio-based. LiteLLM abstraction for Anthropic Claude. Output passes standardized JSON schema validation (Sec 7.4). |
| **Agent 1: Stage Classifier** | P0-8a, Sec 7.3 | First agent deployed and tested. Blind stage inference from transcript alone (no CRM data). Output: inferred stage + evidence + confidence. |
| **Prompt template system** | Sec 7.9, 7.10 | Jinja2 templates with `[AGENT-SPECIFIC]` extension points. Calibration config (YAML) separated from prompt logic. Git-versioned. |

**Week 2 checkpoint**: Upload a single transcript for an account. Agent 1 runs. Structured output is stored in DB. Output passes schema validation. You can query the DB and see a stage inference with evidence.

### Week 3-4: Full Agent Pipeline

**Goal**: All 10 agents running. Multi-transcript support. Synthesis producing health scores and deal memos.

| Deliverable | PRD Reqs | Details |
|---|---|---|
| **Agents 2-8 (parallel set)** | P0-2, Sec 7.3 | Build all 7 specialized agents. Each agent gets its own prompt with embedded Riskified domain knowledge, NEVER rules, and anti-sycophancy instruction. All output to Section 7.4 schema. |
| **Agent 9: Open Discovery / Adversarial Validator** | P0-2, Sec 7.3 Agent 9 | Reads all 8 prior outputs. Catches gaps. Challenges most optimistic finding. |
| **Agent 10: Synthesis Agent** | P0-2, P0-5, P0-6, P0-7, Sec 7.3 Agent 10 | Contradiction mapping, dual deal memo (TL insider + leadership briefing versions), all structured fields: health score (0-100, 8-component breakdown + one-line reason), momentum, forecast category (6 categories), confidence interval, top signals, top risks, recommended actions with action_id for carry-forward tracking. |
| **Action carry-forward system** | P0-10, Sec 7.3 | When pipeline re-runs after new transcript, compare previous recommended actions against new analysis. Flag unfollowed actions. Actions exportable to Salesforce as tasks/notes. |
| **Multi-transcript support** | P0-3 | Up to 5 transcripts per account. Chronological ordering. Momentum computed across the arc. |
| **Agent-Stage Relevance weighting** | Sec 7.5 | Synthesis Agent applies stage-dependent weights from the relevance matrix when combining agent outputs. |
| **Calibration config (v1)** | Sec 7.9 | YAML config with health score weights, confidence ceilings, sparse data thresholds, forecast category thresholds. Loaded at runtime, not baked into prompts. |
| **Full output validation** | Sec 7.10 | All five validation rules running: evidence citation required, confidence-evidence alignment, no invented specifics, absent stakeholder tagging, prohibited language detection. |

**Week 4 checkpoint**: Upload 3-5 transcripts for a single account. Full 10-agent pipeline runs. Deal assessment produced with health score, momentum, forecast category, deal memo, risks, actions. Output validated. Total pipeline latency measured (target: under 3 minutes for 5 transcripts).

### Week 5-6: User-Facing Surfaces

**Goal**: TLs and VP can use the system. Dashboard, deal briefs, conversational interface, score feedback.

| Deliverable | PRD Reqs | Details |
|---|---|---|
| **Pipeline overview dashboard** | P0-9 | Two-level default grouping: Team/TL then Forecast Category. Table/card view: deal name, MRR, AI-inferred stage, health score (component breakdown visual + one-line reason), momentum arrow, AI forecast category, IC category (if entered), days since last call. Sortable by any column. |
| **Deal detail drill-down** | P0-10 | Synthesis-first: shows deal memo (TL or leadership version toggle) + health score component breakdown + recommended actions (with unfollowed carry-forward flags). Per-agent analysis collapsed behind expand controls. Evidence quotes accessible on expand. |
| **Divergence view** | P0-11, P0-8, P0-8c | Deals where AI and IC forecasts differ. Sorted by divergence magnitude. Shows both categories and reasoning. IC category input UI -- entered separately from scoring pipeline. Framing follows Section 12 Condition 2 ("Forecast Alignment Check"). |
| **Team roll-up view** | P0-12 | Aggregate health metrics per team: weighted pipeline by health tier, team forecast comparison (AI vs IC). |
| **Deal brief (3 formats)** | P0-19 | 3 variant formats from same data: (1) Structured one-pager (fixed template), (2) Narrative memo (3-5 paragraphs + structured fields), (3) Inspection-question format (3-5 questions with evidence). User selects preferred format. All exportable/printable. |
| **Conversational interface (v1)** | P0-13, P0-14 | Natural language queries over pipeline data — three query patterns supported equally: deal-specific ("Tell me about Account X"), cross-pipeline filtering ("Which Commit deals are declining?"), and forecast/comparison ("Compare AI vs IC for Team A"). Context-maintaining follow-ups. Includes access to archived transcripts (beyond the 5 active). Structured query layer over stored data — NOT re-running the pipeline per query. |
| **Score feedback capture** | P0-15, P0-16 | On any deal health score: one-click flag + 5 structured reason categories (off-channel, stakeholder context, stage mismatch, deal stalled, recent change not captured) each with per-category free text field. Stored per Section 8 data model (ScoreFeedback). |
| **Meeting prep mode** | P0-24 | Pre-call brief for upcoming prospect meetings: key topics to raise, questions to ask (from risk flags), risks to probe, unresolved items from previous calls. Distinct from deal brief (P0-19). |
| **Rep performance scorecard** | P0-22 | Basic scorecard per rep: 3-4 behavioral dimensions (stakeholder engagement, objection handling, commercial progression, next-step setting). Surfaced at team level. CRO-critical. |
| **Account ingestion UI** | P0-4, P0-1 | Account creation, transcript upload (paste or file), association with account. Support for adding accounts incrementally. |
| **IC forecast entry UI** | P0-8c | Separate input for IC forecast category per deal. Entered after AI scoring. Clean separation from scoring pipeline. |

**Week 6 checkpoint**: A TL logs in, sees their pipeline, clicks into a deal, reads the brief, queries the system conversationally ("what are the risks on Account X?"), provides score feedback. VP sees team roll-up and divergence view. End-to-end user journey works.

### Week 7-8: Calibration, Polish & Validation

**Goal**: System is calibrated on real data, edge cases handled, POC success criteria measurable.

| Deliverable | PRD Reqs | Details |
|---|---|---|
| **Retrospective seeding** | Sec 7.11 Cold Start | Run pipeline on 15-20 historical closed deals (8+ won, 8+ lost, 4-5 stalled). Compare output against known outcomes. Baseline established. |
| **Golden test set** | Sec 7.11 | 20-25 deal snapshots, fixed and versioned. Regression gates running: health score delta >10, forecast flip, stage change, person recall drop >5%. |
| **Feedback review dashboard** | P0-17 | VP sees all TL feedback across deals. Filterable by TL, signal, direction. |
| **First calibration cycle** | P0-18, Sec 7.9 | Analyze accumulated feedback patterns. Adjust calibration config values (not prompt logic). Validate on holdout set. Log changes in CalibrationLog with before/after. |
| **Pipeline-level insights** | P0-20 | Auto-generated: stuck deals, improving deals, new risks since last review. Surfaced in dashboard. |
| **Forecast comparison report** | P0-21 | AI aggregate vs IC aggregate: total weighted pipe under both models, by team and org. |
| **Prompt version control** | Sec 8 | Git-like versioning with rollback. Calibration config history. |
| **Usage tracking instrumentation** | Sec 12 Condition 1 | Login frequency, feedback submissions, conversational queries, brief views -- for CRO success criteria measurement. |
| **Daily email digest + Slack alerts** | P0-23 | Daily morning email: deals that changed, new risks, significant score drops. Slack push alerts for critical moves: score dropped >15 points, forecast category flip, no call in 30+ days. Configurable thresholds per user. |
| **Transcript archive system** | P0-3 | When 6th transcript arrives, oldest moves to archive (is_active=false). Archived transcripts remain queryable via conversational AI. Pipeline continues analyzing only active 5. |
| **Edge case hardening** | -- | Single transcript accounts (sparse data handling), very long transcripts (truncation), Hebrew transcript support, deals with no recent calls. |

**Week 8 checkpoint**: System running on 10-15 real accounts with real transcripts. Golden test set passing. First calibration cycle completed. CRO success criteria measurable. VP and TLs have used the system for at least 2 pipeline review cycles.

---

## 2. Critical User Flows

### Flow 1: TL Prepares for Pipeline Review (Primary value driver)

**Persona**: Team Lead, 24 hours before weekly pipeline review
**Trigger**: TL opens SIS to prepare for tomorrow's meeting

```
1. TL opens Dashboard -> Pipeline Overview (P0-9)
2. Filters to their team's deals
3. Scans health scores + momentum arrows -- identifies:
   - Critical/declining deals (red) -> will lead discussion
   - Divergence flags (P0-8, P0-11) -> inspection targets
4. Clicks into highest-priority deal -> Deal Detail (P0-10)
5. Reads deal memo, checks per-agent analysis for specific evidence
6. Opens Deal Brief (P0-19) -- one-pager with inspection questions
7. Repeats for 3-5 key deals
8. Optionally exports briefs for the meeting
```

**Maps to**: P0-9, P0-10, P0-11, P0-19, P0-5, P0-6, P0-7, P0-8
**Success measure**: Prep time drops from 2+ hours to <30 minutes (Sec 10)

### Flow 2: TL Reviews a Deal Brief in Detail

**Persona**: Team Lead, investigating a specific deal
**Trigger**: Health score seems surprising (too high or too low) or deal flagged as divergent

```
1. From Pipeline Overview, clicks deal name -> Deal Detail (P0-10)
2. Reads Synthesis Agent's deal memo (3-5 paragraphs)
3. Checks health score breakdown by 8 components (Section 7.11)
   - Identifies which components are dragging the score down
4. Expands per-agent analysis summaries
   - Reads Agent 6 (Economic Buyer) -> sees EB never appeared -> component score 5/20
   - Reads Agent 4 (Momentum) -> sees cadence declining
5. Clicks evidence quotes -> sees exact transcript passages
6. Reviews recommended actions (WHO does WHAT by WHEN and WHY)
7. Checks confidence interval -> understands data quality behind the score
8. Decision: either accepts the assessment or flags disagreement (Flow 3)
```

**Maps to**: P0-10, P0-5, P0-6, Sec 7.3 (Agent 10 output), Sec 7.4

### Flow 3: TL Provides Score Feedback

**Persona**: Team Lead who disagrees with an AI assessment
**Trigger**: Score feels wrong based on context the system cannot see

```
1. On Deal Detail view, clicks "Flag Score" button (P0-15)
2. Selects direction: "Score too high" or "Score too low"
3. Selects structured reason (P0-16):
   - "Off-channel activity not captured"
   - "Stakeholder context missing"
   - "Deal stage more advanced than transcripts show"
   - "Deal is stalled -- score too high"
   - "Recent change not captured" (budget cut, reorg, new champion, etc.)
   - "Other"
4. Adds per-category free text explaining the specific context
5. Adds general free-text reasoning (optional)
6. Optionally marks "Off-channel activity: Yes/No"
6. Submits -> feedback stored with timestamp, attribution, deal score at time
7. Feedback flows into calibration cycle (P0-18)
```

**Maps to**: P0-15, P0-16, P0-18, ScoreFeedback data model
**Success measure**: At least 20 feedback submissions during POC (Sec 12 Condition 3)

### Flow 4: VP Views Pipeline Roll-Up

**Persona**: VP Sales, weekly or before board prep
**Trigger**: Wants pulse on overall pipeline health across all teams

```
1. VP opens Dashboard -> Team Roll-Up View (P0-12)
2. Sees per-team aggregate: weighted pipeline by health tier,
   team-level AI vs IC forecast comparison
3. Identifies Team B has 3 Commit deals with Declining momentum
4. Clicks into Team B -> sees those 3 deals in Pipeline Overview (P0-9)
5. Opens Divergence View (P0-11) -> focuses on highest-value divergences
6. Opens Forecast Comparison Report (P0-21):
   - AI aggregate: $X weighted pipe
   - IC aggregate: $Y weighted pipe
   - Delta by category and team
7. Decides which TLs to probe in upcoming 1:1s
```

**Maps to**: P0-12, P0-11, P0-21, P0-9
**Success measure**: VP judges forecast comparison "materially useful" in 2+ cycles (Sec 12)

### Flow 5: VP Queries System Conversationally

**Persona**: VP Sales, ad-hoc question during the day
**Trigger**: Specific question about pipeline that would normally require calling a TL or pulling Salesforce reports

```
1. VP opens Conversational Interface (P0-13)
2. Types: "Which Commit deals have declining health scores?"
3. System returns list with deal names, scores, momentum, key risks
4. VP follows up: "Tell me more about Account X" (P0-14)
5. System responds with deal memo summary, latest assessment,
   top risks and signals -- with evidence
6. VP: "What did they say about timeline in the last call?"
7. System drills into Agent 7 (MSP & Next Steps) output for that account,
   returns specific evidence from most recent transcript
8. VP: "Compare my forecast to the AI forecast for Team A"
9. System returns forecast comparison for Team A
```

**Maps to**: P0-13, P0-14, P0-5, P0-7, P0-21
**Success measure**: <30 seconds to answer; TL uses 3+/week for 4 consecutive weeks (Sec 12)

### Flow 6: TL Ingests New Transcripts for an Account

**Persona**: Team Lead or VP, after a new call
**Trigger**: A new Gong call happened; TL wants the system updated

```
1. TL opens Account Ingestion UI (P0-4)
2. Selects existing account (or creates new with name, MRR estimate, AE owner)
3. Pastes or uploads transcript text (P0-1)
4. System preprocesses: speaker normalization, filler removal, 8K cap
5. System triggers full 10-agent pipeline (P0-2)
6. TL sees processing indicator (pipeline takes 2-3 minutes)
7. Pipeline completes -> deal assessment updated
8. TL navigates to Deal Detail to see updated health score,
   momentum shift, new risks/signals
9. If account now has >5 transcripts, oldest is archived (not deleted)
   -- archived transcripts remain queryable via conversational AI
```

**Maps to**: P0-1, P0-2, P0-3, P0-4, Sec 7.8 (Blind Scoring Protocol)

### Flow 7: VP Reviews TL Feedback Patterns (Calibration)

**Persona**: VP Sales, bi-weekly calibration review
**Trigger**: Enough feedback accumulated to identify patterns

```
1. VP opens Feedback Review Dashboard (P0-17)
2. Sees all TL feedback submissions, filterable by:
   - TL (who flagged), signal type, direction (too high/too low)
3. Identifies pattern: "Agent 6 (Economic Buyer) consistently penalizes
   deals where EB engagement happens off-channel"
4. Reviews specific feedback items with TL reasoning
5. Calibration action: adjusts `eb_absence_health_ceiling` in YAML config
   from 70 -> 65, or adjusts `secondhand_mention_counts_as_engaged` -> true
6. Runs golden test set to check for regressions (P0-18)
7. Changes logged in CalibrationLog with before/after values
```

**Maps to**: P0-17, P0-18, Sec 7.9, CalibrationLog data model

### Flow 8: AE/TL Prepares for Upcoming Prospect Call

**Persona**: Team Lead or AE (via TL), before a scheduled prospect call
**Trigger**: Call with prospect scheduled for tomorrow

```
1. TL opens Meeting Prep Mode (P0-24) for an account
2. System generates pre-call brief based on latest deal assessment:
   - Key topics to raise (informed by risk flags and gaps in analysis)
   - Questions to ask (from unresolved items across previous calls)
   - Risks to probe (from Agent 3, 6, 8 findings)
   - Unresolved items from previous calls (from Agent 7 MSP tracking)
3. TL reviews brief, optionally forwards to AE for call prep
4. After the call, new transcript is uploaded -> pipeline re-runs
5. System compares: did the recommended topics get addressed?
```

**Maps to**: P0-24, P0-10, Agent 7 (MSP & Next Steps)

### Flow 9: VP Morning Check-in via Email + Slack

**Persona**: VP Sales, starting the day
**Trigger**: Daily email digest arrives at 8 AM

```
1. VP scans morning email digest (P0-23):
   - Deals with significant score changes since yesterday
   - New risk flags across all teams
   - Deals with no call in 30+ days
2. If a critical Slack alert fired overnight:
   - Score dropped >15 points on a deal
   - Forecast category flipped (e.g., Commit -> At Risk)
3. VP opens dashboard to investigate flagged deals
4. Optionally queries conversational interface for quick answers
```

**Maps to**: P0-23, P0-9, P0-13

---

## 3. Feature Priority Matrix: P0 Requirements

Ranked by composite of implementation dependency, user value, and technical risk.

### Tier 1: Build First (Blocks Everything)

| Req | Feature | Dependency | User Value | Tech Risk | Notes |
|---|---|---|---|---|---|
| **P0-1** | Transcript ingestion | None -- entry point | Medium (enabler) | Low | Preprocessor is well-defined. Gong format is the one blocker. |
| **P0-2** | 10-agent analysis pipeline | P0-1 | Critical (core value) | **HIGH** | This is the product. Prompt engineering for 10 agents is the single largest effort and risk. |
| **P0-3** | Multi-transcript tracking (up to 5) | P0-1 | High | Low | Straightforward data model + ordering. |
| **P0-8a** | Blind stage inference (Agent 1) | P0-1 | High | Medium | Stage inference accuracy directly affects all downstream agents via the relevance matrix. |
| **P0-8b** | Blind scoring (no CRM data in pipeline) | Architectural decision | High (integrity) | Low | Architecture constraint, not a feature. Enforce at the pipeline boundary. |
| **P0-5** | Health score (0-100, 8-component) | P0-2 | Critical | **HIGH** | Score calibration is the hardest problem. |
| **P0-6** | Momentum direction | P0-3 | High | Medium | Requires comparing assessments across calls. Only meaningful with 2+ transcripts. |

### Tier 2: Core User-Facing (Enables Testing)

| Req | Feature | Dependency | User Value | Tech Risk | Notes |
|---|---|---|---|---|---|
| **P0-9** | Pipeline overview dashboard | P0-5, P0-6, P0-7 | Critical | Low | Standard table/card UI. Value is in the data. |
| **P0-10** | Deal detail drill-down | P0-2, P0-5 | Critical | Low | Rendering agent outputs with evidence. |
| **P0-19** | Deal brief (one-pager) | P0-10 (same data) | Critical | Low | Template over the same data. Most important for pipeline review. |
| **P0-4** | Account-by-account ingestion | P0-1 | High (usability) | Low | Account CRUD + transcript association. |
| **P0-7** | AI forecast categories | P0-5, P0-6 | High | Medium | 6-category expansion adds nuance + calibration burden. |
| **P0-8c** | IC forecast entered separately | P0-7 | High (integrity) | Low | Simple input UI, decoupled from pipeline. |

### Tier 3: Differentiation Features

| Req | Feature | Dependency | User Value | Tech Risk | Notes |
|---|---|---|---|---|---|
| **P0-8** | Divergence flagging | P0-7, P0-8c | **Very High** | Medium | Highest-value and highest-risk feature per CRO review. |
| **P0-11** | Divergence view | P0-8 | High | Low | Sorted list with both categories and reasoning. |
| **P0-13** | Conversational interface | P0-2, P0-9 | High (VP persona) | Medium | Structured query over stored assessments. |
| **P0-14** | Conversational drill-down | P0-13 | High | Medium | Follow-up context is the tricky part. |
| **P0-12** | Team roll-up view | P0-9 | High (VP persona) | Low | Aggregation queries over deal assessments. |
| **P0-21** | Forecast comparison report | P0-7, P0-8c | High (VP persona) | Low | AI vs IC by team and org. |

### Tier 4: Calibration & Feedback Loop

| Req | Feature | Dependency | User Value | Tech Risk | Notes |
|---|---|---|---|---|---|
| **P0-15** | Score feedback capture | P0-5, P0-10 | High (long-term) | Low | One-click + per-category text. |
| **P0-16** | Structured feedback (5 categories) | P0-15 | Medium | Low | 5 options + free text per each. |
| **P0-17** | Feedback review dashboard | P0-15 | Medium | Low | Aggregated view for VP. |
| **P0-18** | Calibration loop | P0-15, P0-17 | High (system learning) | Medium | VP reviews + developer adjusts. |
| **P0-20** | Pipeline-level insights | P0-9, P0-5 | Medium | Medium | Requires delta computation between runs. |

### Tier 5: New P0 Features (from Q&A Deep-Dive)

| Req | Feature | Dependency | User Value | Tech Risk | Notes |
|---|---|---|---|---|---|
| **P0-22** | Rep performance scorecard | P0-2 (agent outputs) | **High** (CRO) | Medium | 3-4 behavioral dimensions extracted from agent outputs. Upgraded from P1. |
| **P0-23** | Daily email digest + Slack alerts | P0-5, P0-9 | High | Low | Morning email + critical Slack push. Configurable thresholds. Upgraded from P1. |
| **P0-24** | Meeting prep mode | P0-10, P0-2 | High | Low | Pre-call brief: topics, questions, risks, unresolved items. New feature. |
| -- | Transcript archive + chat access | P0-3, P0-13 | Medium | Low | Archive old transcripts, make queryable via chat. |
| -- | Action carry-forward | P0-10 | High | Medium | Compare previous actions to new analysis. Flag unfollowed. |
| -- | Dual deal memo versions | P0-10, Agent 10 | Medium | Low | TL insider + leadership briefing. Same data, two writing styles. |
| -- | 3 deal brief formats | P0-19 | Medium | Low | Structured, narrative, inspection-question. Same data, three templates. |
| -- | SF action export | P0-10 | Medium | Low | Export recommended actions as Salesforce tasks/notes. |

---

## 4. MVP Cuts: If You Need to Hit 6 Weeks

### Safe Deferrals (cut these first, minimal value loss)

| Feature | PRD Req | Simplification | Rationale |
|---|---|---|---|
| Pipeline-level insights | P0-20 | Defer to Week 7-8 or post-POC | TLs can see this manually from pipeline overview. |
| Forecast comparison report | P0-21 | Defer to conversational query | VP can ask "compare my forecast to AI" conversationally. |
| Feedback review dashboard | P0-17 | Replace with simple export/spreadsheet view | VP can review feedback in a table. Fancy filtering can wait. |
| Calibration loop automation | P0-18 | Manual process (developer edits YAML + runs golden test set) | Still happens, just not self-service. |
| Team roll-up view | P0-12 | Simplify to a single aggregate row per team | With only 1-2 TLs, VP can filter by team. |

### Absolute Minimum First Demo (Week 4)

1. **One account with 3 transcripts uploaded**
2. **Full 10-agent pipeline runs** (non-negotiable -- this IS the product)
3. **Deal assessment visible**: health score, momentum, stage inference, deal memo, top risks, recommended actions
4. **Simple deal detail page** (can be unstyled, read-only)
5. **No dashboard, no chat, no feedback, no divergence** -- just the pipeline output rendered

This proves the core bet: "Can AI agents extract meaningful deal health signals from transcripts alone?"

---

## 5. Success Checkpoints

### Week 2: "The Pipeline Works"

| Checkpoint | Evidence |
|---|---|
| Transcript preprocessor handles real Gong exports | Run on 3 real transcripts, output is clean |
| Agent 1 (Stage) produces correct stage inference | Test on 5 deals where stage is known -- >70% accuracy |
| Orchestrator runs Agent 1 -> stores output -> passes validation | End-to-end flow, automated |
| Data model supports multi-transcript accounts | Upload 3 transcripts for one account, confirm chronological ordering |
| Prompt template system functional | Agent prompt can be modified without code deployment |

**Decision gate**: If Agent 1 stage accuracy is below 50%, STOP and recalibrate before building Agents 2-8.

### Week 4: "The Analysis Is Valuable"

| Checkpoint | Evidence |
|---|---|
| Full 10-agent pipeline completes for 3+ transcripts | End-to-end run, <3 minutes |
| Health scores are directionally correct on known deals | Won deals score higher than lost deals in >70% of cases |
| Deal memos are useful to a TL | VP rates 5 deal memos blind -- target: average >3.5/5 |
| Evidence citations are accurate | >95% of spot-checked quotes are real |
| Token costs are sustainable | Measure cost per analysis, project to 100 accounts -- must be under $500/month |

**Decision gate**: If deal memos are not useful (VP rating <3/5), fix the pipeline before building the dashboard.

### Week 6: "TLs Can Use It"

| Checkpoint | Evidence |
|---|---|
| TL can log in, see pipeline, drill into a deal, read the brief | Full user journey works |
| TL used the system to prep for at least 1 real pipeline review | Self-reported + login log |
| Conversational interface answers basic questions accurately | VP asks 10 questions, >80% get useful answers |
| Score feedback is being captured | At least 5 feedback submissions |
| Divergence flags correctly framed | Reviewed and approved by VP |

**Decision gate**: If TLs don't find deal briefs useful for pipeline review prep, the product has failed its core value proposition.

### Week 8: "POC Success Criteria Measurable"

| Checkpoint | Evidence | CRO Criterion |
|---|---|---|
| 80%+ of active POC deals have current AI health score | System metric | Condition 3, Row 1 |
| At least 1 TL using conversational interface 3+/week | System metric | Condition 3, Row 2 |
| Deal briefs used in at least 4 pipeline reviews | TL attestation | Condition 3, Row 3 |
| At least 20 score feedback submissions | System metric | Condition 3, Row 4 |
| VP judges forecast comparison "materially useful" | VP attestation | Condition 3, Row 5 |
| AI forecast matches deal trajectory in 60%+ of cases | Measured on deals with sufficient data | Condition 3, Row 6 |
| Golden test set running, first calibration cycle complete | Test results logged | Section 7.11 |

---

## 6. Risk Assessment

**Biggest technical risk**: The quality of the 10-agent pipeline output. Everything downstream (dashboard, briefs, chat, divergence, feedback) is presentation of pipeline output. If the pipeline produces mediocre assessments, no amount of UI polish will make the product valuable. Allocate 60% of engineering effort to the pipeline (Weeks 1-4) and 40% to the user-facing layer (Weeks 5-8).

**Biggest product risk**: The divergence flag. Simultaneously the highest-value and highest-risk feature. The dry-run requirement (VP reviews 5+ divergence outputs before any TL sees it) is non-negotiable. Build it, but gate its visibility behind VP approval.

**Biggest adoption risk**: Manual transcript ingestion. 5 transcripts per account for 15 accounts = 75 paste operations. Mitigation: (a) batch upload for multiple transcripts, (b) admin/ops person does initial data load, or (c) explore Gong API access.

**Cost projection**: ~$0.57/deal run, ~$328/month for 100 accounts weekly (per Technical Architecture estimate). Using Haiku for Agents 2-8 and Sonnet/Opus for Agent 10 is a pragmatic cost optimization.

**Scope expansion risk (v1.1)**: The Q&A deep-dive added 7 new P0-level features (rep scorecard, meeting prep, alerts, transcript archive, action carry-forward, SF export, dual memo). The original 8-week plan assumed a tighter scope. Mitigation: (a) Weeks 1-4 remain unchanged — pipeline quality is still the #1 priority. (b) New features mostly layer on top of existing pipeline output, not new agents. (c) Rep scorecard (P0-22) can use existing agent outputs without new LLM calls. (d) Alerts and meeting prep are presentation features, not pipeline changes. (e) If time-pressured, use the MVP Cuts table above — the new features are in Tier 5 and can be deferred to Week 7-8.
