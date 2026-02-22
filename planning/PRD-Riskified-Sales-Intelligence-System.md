# PRD: Riskified Sales Intelligence System (SIS)

**Version:** 1.4 — Multi-Agent Lenses Architecture + AI Team Enhancement Review
**Date:** February 18, 2026
**Author:** VP Sales + AI Agent Team (Product Manager, Business Analyst, UX Researcher, Data Analyst, Competitive Intelligence, Market Researcher, Sales Strategist, GTM Lead) + Data & AI Team (Agent Architect, Prompt Engineer, AI Eval Engineer, AI Safety Analyst)
**Status:** CRO Approved with Conditions — Pending VP Sales Sign-off

---

## 1. Problem Statement

Riskified's VP Sales manages ~100 active deals across a team of dozens of sales reps (100 people total in GTM), running strategic sales cycles that average 6-12+ months on the AE side and months-to-years on the BD side. Three critical problems are unsolvable with current tools:

1. **Pipeline opacity:** With 100 concurrent deals in long cycles, it is impossible for leadership to maintain a current, accurate picture of deal health, progression, and where attention is needed. Weekly pipeline reviews rely on rep narration — recency-biased, time-consuming, and incomplete.

2. **Forecast unreliability:** Forecasting is based on subjective IC input through Salesforce + Einstein. In long cycles where only reps have ground-truth context, subjective forecasts consistently miss. There is no objective counterbalance to rep optimism or sandbagging. The VP currently has no way to validate whether a "Commit" deal truly deserves that label.

3. **Coaching at scale is impossible:** Listening to calls takes hours. Aggregating performance data across dozens of reps is impossible manually. Feedback is delivered ad-hoc in 1:1s or as Gong comments, with no systematic way to track whether feedback is incorporated or measure rep improvement over time.

**Impact of not solving:** Continued forecast misses at the board level, deals slipping without early warning, inconsistent rep development, and leadership decisions made on incomplete or manipulated data.

---

## 2. Goals

| # | Goal | Metric | Target |
|---|------|--------|--------|
| G1 | Team leads and middle management have a clear, always-current grasp of pipeline health | % of deals with AI-generated health score | 100% of active deals |
| G2 | Reduce forecast misses through objective, data-driven forecasting | Forecast accuracy (actual vs. predicted within category) | <20% miss rate (from current ~40%+) |
| G3 | Enable one-click drill-down from pipeline overview to deal details | Time from "I have a question about a deal" to "I have the answer" | <30 seconds |
| G4 | Surface deal health signals automatically from call transcripts | Manual call listening hours per week for leadership | Reduce by 80% |
| G5 | Create a systematic L&D feedback loop with measurable progress tracking | % of reps with structured performance baseline and tracked progress | 100% within 90 days of launch |

---

## 3. Non-Goals

| # | Non-Goal | Rationale |
|---|----------|-----------|
| NG1 | Replace Salesforce as the CRM | This is an intelligence layer on top of SF, not a replacement. SF remains the system of record. |
| NG2 | Automate CRM data entry from transcripts (in POC) | POC is transcript-only. CRM write-back is Phase 2. |
| NG3 | Build a call recording/transcription tool | Gong handles this. We analyze Gong output, not replace it. |
| NG4 | Rep-facing self-service tool (in POC) | POC users are team leads and middle management. Rep-facing features are Phase 3. |
| NG5 | Integrate email/Outreach data (in POC) | POC uses Gong transcripts only. Email ingestion is Phase 2. |
| NG6 | Fully automated forecasting that replaces human judgment | The system provides an objective counterbalance, not a replacement. Team leads retain forecast ownership. |

---

## 4. User Personas

### Primary Persona: Team Lead / Middle Manager
- **Role:** Manages 5-15 AEs, responsible for team forecast and pipeline progression
- **Current pain:** Spends 3-5 hours/week in pipeline reviews, can't prep adequately for 15+ deals, relies on rep narration
- **Wants:** Pre-built deal briefs before pipeline reviews, objective deal health signals, flagged risks, divergence alerts
- **Technical comfort:** Moderate — uses Salesforce daily, comfortable with dashboards, not building reports from scratch

### Secondary Persona: VP Sales
- **Role:** Oversees all teams, owns the number to the board, manages team leads
- **Current pain:** Cannot independently verify forecast accuracy, no real-time pipeline pulse, call listening doesn't scale
- **Wants:** Roll-up view across all teams, forecast comparison (AI vs. IC), coaching insights at scale, board-ready views
- **Technical comfort:** High — expects to query the system conversationally and get instant answers

### Future Persona (Phase 3): Individual Contributor (AE/BD)
- **Role:** Owns deals, submits forecasts, runs calls
- **Future wants:** AI-generated call debriefs, deal preparation briefs, self-coaching insights
- **Note:** NOT in POC scope. Reps will be aware of the system but are not primary users initially.

---

## 5. User Stories

### Pillar 1: Pipeline Intelligence

**As a Team Lead, I want to:**
- See a health score for every deal in my pipeline so I can prioritize my attention on at-risk deals
- Get a pre-meeting deal brief before each pipeline review so I arrive informed rather than dependent on rep narration
- See which deals have progressed (positive signals) and which are stuck (no new signals or declining signals) since last review
- Drill down from any deal's health score to the specific transcript evidence that drives the score
- See a pipeline overview that groups deals by health status (healthy, at-risk, critical) not just forecast category
- Override or annotate AI scores with context the system can't see (off-channel activity, relationship context)

**As a VP Sales, I want to:**
- See a roll-up of pipeline health across all teams in one view
- Identify which teams have the healthiest/riskiest pipelines without sitting through every team's review
- Query the system conversationally (e.g., "Which Commit deals have declining health scores?" or "Show me all deals over 50K MRR that haven't had a call in 30 days")

### Pillar 2: Objective Forecasting

**As a Team Lead, I want to:**
- See an AI-generated forecast category (Commit/Realistic/Upside) for each deal based on transcript signals, independent of what the rep submitted
- See divergence flags where the AI forecast differs from the rep's submitted forecast, so I can investigate
- Understand WHY the AI scored a deal differently — with specific evidence from transcripts
- Track forecast accuracy over time (was the AI right? was the rep right?) to calibrate trust in the system

**As a VP Sales, I want to:**
- Compare the aggregate AI forecast to the aggregate IC forecast at team and org level
- See the total weighted pipeline value under both models (AI vs. IC)
- Identify systematic patterns (e.g., "Team A consistently over-forecasts by one category")

### Pillar 3: L&D / Rep Performance

**As a Team Lead, I want to:**
- See a performance profile for each rep across key selling behaviors (stakeholder engagement, objection handling, commercial progression, next-step setting)
- Track rep improvement over time — is a rep getting better at areas I've coached them on?
- Log coaching feedback in the system and have it linked to specific behaviors so I can review whether feedback was incorporated
- Get AI-suggested coaching focus areas for each rep based on transcript analysis

**As a VP Sales, I want to:**
- See aggregate team-level performance patterns (which teams are strong/weak at which behaviors)
- Identify top performers and understand what differentiates them from average performers
- Measure coaching effectiveness — does structured feedback lead to measurable behavior change?

---

## 6. Requirements

### P0 — Must-Have (POC)

#### 6.1 Transcript Ingestion & Analysis Engine

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-1 | Ingest Gong transcript (text format) manually provided per account | System accepts pasted or uploaded transcript text and associates it with an account |
| P0-2 | Analyze each transcript through multi-agent lenses | System runs 10-agent analysis pipeline (see Multi-Agent Framework below): 8 specialized agents + Open Discovery + Synthesis Agent producing deal memo and structured output |
| P0-3 | Track agent assessments across multiple transcripts per account (up to 5) | System maintains chronological analysis history and computes momentum direction across the call arc |
| P0-4 | Support account-by-account ingestion (manual, on-request) | VP/TL can add accounts incrementally; system handles 1-100 accounts |

#### 6.2 Deal Health Scoring

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-5 | Compute a 0-100 Deal Health Score per account using multi-agent synthesis | Score derived by Synthesis Agent from combined analysis of all agent outputs, weighted by stage relevance (see Agent-Stage Relevance matrix). Includes confidence interval (High/Medium/Low). |
| P0-6 | Compute Momentum Direction (Improving/Stable/Declining) across the transcript arc | Direction computed by comparing signal scores across chronological transcripts |
| P0-7 | Map deals to AI Forecast Categories (Commit/Realistic/Upside) based on score + momentum | Mapping follows defined thresholds (see Forecast Methodology below) |
| P0-8 | Flag divergence between AI category and IC-submitted category | Visual divergence indicator + one-sentence explanation of why. IC category entered separately by VP/TL after AI scores blind. |

#### 6.2a Stage Inference & Blind Scoring

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-8a | Infer deal stage from transcript content alone (no human input) | Stage & Progress Agent (Agent 1) outputs inferred stage (1-7) with confidence level and reasoning based on transcript analysis |
| P0-8b | Score deals blind — no deal stage, IC forecast, or CRM data provided to scoring engine | Scoring engine accepts only raw transcript text; all other metadata is excluded from the scoring pipeline |
| P0-8c | IC forecast entered separately post-scoring for comparison only | IC forecast input is decoupled from scoring; divergence computed as a post-hoc comparison layer |

#### 6.3 Pipeline Dashboard

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-9 | Pipeline overview: all deals grouped by health status with key metrics | Shows deal name, MRR, AI-inferred stage, health score, momentum, AI category, IC category (if entered), days since last call |
| P0-10 | Deal detail drill-down: one-click from overview to full deal brief | Shows AI-inferred stage, full deal memo from Synthesis Agent, per-agent analysis summaries with evidence quotes, agent trajectory across calls, risk flags, confidence interval, recommended actions |
| P0-11 | Divergence view: deals where AI and IC forecasts differ | Sorted by divergence magnitude; shows both categories and reasoning |
| P0-12 | Team roll-up view: aggregate health metrics per team | Weighted pipeline by health tier, team forecast comparison |

#### 6.4 Conversational Interface

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-13 | Natural language query interface for pipeline questions | User can ask "which deals need attention?" or "tell me about Account X" and get accurate, evidence-backed answers |
| P0-14 | Conversational drill-down into any deal, signal, or transcript | Follow-up questions maintain context (e.g., "what did they say about timeline?") |

#### 6.5 Score Feedback & Calibration Loop

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-15 | TL score feedback capture: "This score feels wrong — here's why" | On any deal health score, TL can flag disagreement with one-click and provide free-text reasoning. Feedback is timestamped, attributed, and stored. |
| P0-16 | Structured feedback categories: TL selects reason for disagreement | Predefined options: "Off-channel activity not captured", "Stakeholder context missing", "Deal stage more advanced than transcripts show", "Deal is stalled — score too high", "Other (free text)" |
| P0-17 | Feedback review dashboard: VP Sales can see all TL feedback across deals | Aggregated view of all score disagreements, filterable by TL, signal, and direction (AI too high vs. AI too low) |
| P0-18 | Calibration input: feedback directly informs agent prompt and weight adjustments | After each calibration cycle (target: bi-weekly in POC), feedback patterns are analyzed and agent prompts/stage-relevance weights/thresholds are adjusted. Changes are logged with before/after values. |

#### 6.6 Insights Layer

| Req | Description | Acceptance Criteria |
|-----|-------------|-------------------|
| P0-19 | Auto-generated deal brief per account (pre-meeting prep) | One-page brief: deal memo summary, score + confidence interval, momentum, top 3 positive signals, top 3 risks, recommended actions |
| P0-20 | Pipeline-level insights: stuck deals, improving deals, new risks since last review | Generated automatically, surfaced in dashboard + queryable |
| P0-21 | Forecast comparison report: AI aggregate vs. IC aggregate | Shows total weighted pipe under both models, by team and org-wide |

### P1 — Nice-to-Have (POC Enhancement)

| Req | Description |
|-----|-------------|
| P1-1 | Rep performance profiles: behavioral scoring across defined competencies from transcripts |
| P1-2 | Coaching log: TL can log feedback linked to specific behaviors, track incorporation |
| P1-3 | Trend analysis: how has pipeline health changed over the last 4 weeks? |
| P1-4 | Slack/email alerts: push notifications for critical deal health changes |

### P2 — Future (Post-POC)

| Req | Description |
|-----|-------------|
| P2-1 | Salesforce data integration: pull deal stages, amounts, close dates, activity logs |
| P2-2 | Outreach/email integration: analyze email engagement signals |
| P2-3 | Salesforce LWC deployment: move frontend from Next.js to Lightning Web Components embedded in Salesforce |
| P2-4 | Rep-facing features: self-coaching, deal prep briefs, call debriefs |
| P2-5 | Historical win/loss correlation: train model on closed deals to improve scoring |
| P2-6 | Automated CRM write-back: update deal fields from transcript insights |
| P2-7 | Board-ready forecast reports: auto-generated with confidence intervals |

---

## 7. Deal Stages & Multi-Agent Analysis Framework

### Design Principles

1. **Transcript-only, last 5 calls:** The system may never have access to a full call repository. It must be designed to operate permanently on the last 5 calls per account — this is not a POC limitation but a permanent architectural constraint.
2. **Blind scoring:** The AI receives NO human-provided deal stage or forecast category. It infers both independently from transcript content. IC forecast is provided separately after scoring for comparison only.
3. **Multi-agent lenses, not checklists:** Human sales interactions are too complex to reduce to a fixed set of scored signals. Instead, specialized agents analyze each transcript from distinct analytical perspectives, producing rich narrative assessments. A Synthesis Agent combines these into a coherent deal health picture.
4. **Structured output from unstructured analysis:** Each agent writes analytical prose — not checkbox scores. The Synthesis Agent then produces both a narrative deal memo and structured fields (health score, inferred stage, forecast category) derived from the combined analysis.

### 7.1 Riskified Deal Stages

The system must detect which stage a deal is in based on transcript content alone.

| # | Stage | What Happens | Typical Duration | Key Players |
|---|-------|-------------|------------------|-------------|
| 1 | **SQL** | BD shaped use case, metrics provided, NDA signed → handoff to AE | Months to years (BD side) | BD + 1-2 prospect contacts |
| 2 | **Metrics Validation** | AE validates the prospect's data (chargeback rates, fraud BPS, volumes) | 2-6 weeks | AE + prospect ops/risk |
| 3 | **Commercial Build & Present** | AE builds pricing/ROI model, presents to champion/influencer/DM | 4-12 weeks | AE + champion + DM |
| 4 | **Stakeholder Alignment** | AE + champion sell internally across departments, secure budget & approvals | 2-6 months | AE + champion + CFO, VP Risk, CTO, Procurement |
| 5 | **Legal** | MSA negotiation and execution | 4-12 weeks | Legal teams (both sides) |
| 6 | **Integration** | Technical integration of Riskified into merchant's stack | 4-12 weeks | AE + SE + merchant tech team |
| 7 | **Onboarding** | Model optimization iterations until performance targets met → **Go-Live = Closed Won** | 4-12 weeks | AE + data/ML team + merchant ops |

**Stage inference:** Stage is inferred by the Stage & Progress Agent (Agent 1) based on which topics dominate the transcript — legal/MSA discussion → Legal stage, metrics exchange → SQL/Validation, etc. The agent outputs its inferred stage with confidence level and reasoning.

### 7.2 Multi-Agent Lenses Architecture

Each call transcript passes through a **sequential-parallel pipeline**: Agent 1 (Stage) runs first to establish deal stage context, Agents 2-8 run in parallel with stage context, Agent 9 reads all prior outputs to catch gaps, and Agent 10 synthesizes everything.

```
┌──────────────────────────────────────────────────────────────────┐
│              Per-Account Analysis Pipeline (v1.4)                 │
│            (runs on last 5 preprocessed transcripts)              │
│                                                                   │
│  STEP 1 — Sequential (stage context feeds all downstream agents)  │
│  ┌────────────────────────────────────────────────────────┐       │
│  │  1. Stage & Progress Agent                              │       │
│  │  Infers deal stage + trajectory → passes to all agents  │       │
│  └──────────────────────┬─────────────────────────────────┘       │
│                          │ stage context                           │
│  STEP 2 — Parallel (7 agents run simultaneously)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │ 2. Relation- │ │ 3. Commer-   │ │ 4. Momentum  │              │
│  │    ship &    │ │    cial &    │ │    & Engage- │              │
│  │    Power Map │ │    Risk      │ │    ment      │              │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘              │
│  ┌──────┴───────┐ ┌──────┴───────┐ ┌──────┴───────┐              │
│  │ 5. Technical │ │ 6. Economic  │ │ 7. MSP &     │              │
│  │    Validation│ │    Buyer     │ │    Next Steps│              │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘              │
│  ┌──────┴───────┐        │                │                       │
│  │ 8. Competit- │        │                │                       │
│  │    ive Disp. │        │                │                       │
│  └──────┬───────┘        │                │                       │
│         └────────────────┼────────────────┘                       │
│                          │ all 8 agent outputs                    │
│  STEP 3 — Sequential (reads agents 1-8 to find gaps)             │
│  ┌────────────────────────────────────────────────────────┐       │
│  │  9. Open Discovery / Adversarial Validator              │       │
│  │  Catches what 1-8 missed + challenges most optimistic   │       │
│  │  finding from upstream agents                           │       │
│  └──────────────────────┬─────────────────────────────────┘       │
│                          │ all 9 agent outputs                    │
│  STEP 4 — Sequential (final synthesis)                            │
│  ┌────────────────────────────────────────────────────────┐       │
│  │  10. Synthesis Agent                                    │       │
│  │  Contradiction mapping → deal memo → structured output  │       │
│  │  Health score (0-100) + confidence interval + forecast   │       │
│  └────────────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────────┘
```

**Why sequential-parallel hybrid:** Agent 1's stage inference informs how every other agent weights its findings (stage-appropriate analysis). Agent 9 must see what others found to catch what they missed. This workflow adds ~15 seconds of latency vs. fully parallel, but produces significantly more coherent analysis.

### 7.3 Agent Specifications

Each agent receives the full set of available transcripts (up to 5) and produces an analytical narrative, not a numeric score. Agents have embedded domain knowledge specific to Riskified's enterprise fraud prevention sales motion.

#### Agent 1: Stage & Progress
- **Lens:** Where is this deal in its lifecycle, and is it advancing?
- **Analyzes:** Which topics dominate the conversation (metrics, pricing, legal, integration), progression markers between calls, stage-appropriate milestones achieved vs. expected
- **Embedded knowledge:** Riskified's 7 deal stages (Section 7.1), typical stage durations, what stage transitions look like in transcript language
- **Output:** Inferred deal stage + confidence level + reasoning, progression narrative, stage-appropriate milestone checklist
- **Key failure mode it catches:** Wrong stage in CRM / stage misclassification

#### Agent 2: Relationship & Power Map
- **Lens:** Who are the people in this deal and what is their influence?
- **Analyzes:** All stakeholders who have appeared on calls, their roles and seniority, department diversity, champion identification, blocker signals, decision-maker engagement depth
- **Embedded knowledge:** Riskified's typical buying committee (payments, fraud/risk, finance, legal, IT/engineering, procurement), what multithreading looks like at each stage
- **Output:** Stakeholder map with roles and engagement levels, champion assessment, multithreading depth, political risk flags
- **Key failure mode it catches:** Champion leaves or goes quiet, deal is single-threaded

#### Agent 3: Commercial & Risk
- **Lens:** What is the commercial state of this deal and what could go wrong?
- **Analyzes:** Pricing/budget/ROI discussions, contract terms, objection patterns, unresolved concerns, risk signals (vague commitments, pushback escalation, scope creep)
- **Embedded knowledge:** Riskified's MRR-based pricing model, typical commercial negotiation patterns, common objections in fraud prevention sales
- **Output:** Commercial readiness assessment, active risks with evidence, objection tracking (resolved vs. recurring), recommended risk mitigations
- **Key failure mode it catches:** Pricing objection surfaces late, recurring unresolved pushbacks

#### Agent 4: Momentum & Engagement
- **Lens:** Is the buying energy increasing, stable, or fading?
- **Analyzes:** Call cadence and regularity, who is initiating meetings, question volume and depth, energy/engagement levels, topic evolution across calls, whether the conversation is narrowing toward closure or expanding
- **Embedded knowledge:** Stage-appropriate cadence norms (weekly = healthy in active stages, monthly = stalling), customer-initiated vs. seller-initiated benchmarks
- **Output:** Momentum direction (Improving/Stable/Declining) with evidence, engagement trajectory narrative, leading indicators of stall or acceleration
- **Key failure mode it catches:** Call cadence collapses, deal is coasting on inertia

#### Agent 5: Technical Validation & Integration Complexity
- **Lens:** Is the deal technically feasible, and is the buyer's org ready to implement?
- **Analyzes:** Presence of technical stakeholders (SEs, architects, IT leads) on calls, integration complexity signals (legacy stack, custom checkout, existing fraud tools), POC scoping and progress, technical objections and resolution, technical champion identification
- **Embedded knowledge:** Riskified's integration requirements, common merchant technical architectures, typical integration blockers (legacy payment stacks, custom checkouts, existing fraud rules engines)
- **Output:** Integration readiness assessment (Low/Medium/High), technical champion presence, POC status, identified technical blockers, recommended SE actions
- **Key failure mode it catches:** Deal dies in Integration because technical complexity was never scoped

#### Agent 6: Economic Buyer Presence & Authority
- **Lens:** Does the person who controls the budget know about this deal and support it?
- **Analyzes:** Whether someone with budget authority (CFO, VP Finance, COO) has appeared on calls, quality of their engagement when present, language patterns around budget approval ("approved" vs. "need to present"), secondhand references to economic buyer sentiment, conspicuous absence patterns
- **Embedded knowledge:** Riskified's typical economic buyers by merchant size, budget authority patterns in e-commerce orgs, MEDDIC economic buyer verification
- **Output:** Economic buyer confirmed Y/N, last EB appearance, EB access risk level, language flags indicating undisclosed budget uncertainty, recommended executive sponsor escalation
- **Key failure mode it catches:** CFO kills deal at final approval — EB was never actually engaged

#### Agent 7: Mutual Success Plan & Next Step Commitment
- **Lens:** Is this deal structurally advancing, or just enthusiastically stalling?
- **Analyzes:** Specificity of forward commitments (dates + owners + deliverables vs. "let's reconnect"), buyer vs. seller initiation of next steps, committed action completion rates across calls, existence of a mutual success plan or joint timeline, whether a go-live date or buyer-owned deadline exists
- **Embedded knowledge:** Force Management's commitment discipline framework, what strong vs. weak next steps look like in enterprise sales, Riskified's typical MSP structure
- **Output:** MSP existence Y/N, next-step specificity assessment, buyer vs. seller initiation ratio, committed action slip rate, go-live date confirmed Y/N, recommended actions to establish forward commitment
- **Key failure mode it catches:** Deal is "always next quarter" — enthusiastic but structurally stalled

#### Agent 8: Competitive Displacement & Alternative Path
- **Lens:** What is the buyer replacing, how attached are they to it, and could they choose to do nothing?
- **Analyzes:** Status quo solution (Forter, Signifyd, in-house rules engine, manual review, hybrid), how embedded the incumbent is, switching catalyst strength (chargeback spike, growth, leadership change, platform migration), RFP vs. sole-source vs. replacement dynamics, buyer language about current vendor (defensive vs. critical), "no decision" risk
- **Embedded knowledge:** Competitive landscape (Forter, Signifyd, in-house), typical displacement barriers in fraud prevention, what catalysts force real decisions vs. casual evaluation
- **Output:** Status quo solution identified, displacement readiness (Low/Medium/High), catalyst strength (cosmetic/structural/existential), competitive dynamics classification, "no decision" risk flag, recommended catalyst-hardening actions
- **Key failure mode it catches:** Incumbent wins by default, or buyer simply decides to do nothing

#### Agent 9: Open Discovery / Adversarial Validator
- **Lens:** What is happening in this deal that none of the 8 specialized agents captured? And what is the most optimistic finding from agents 1-8 that deserves challenge?
- **Analyzes:** Unexpected dynamics, market/timing factors, cultural signals, opportunity angles, anything outside other agents' schemas. **Also:** reads all outputs from Agents 1-8 and explicitly challenges the most optimistic finding with counter-evidence or missing context.
- **Embedded knowledge:** Broad awareness of e-commerce industry dynamics, seasonal patterns, common external factors affecting fraud prevention buying decisions
- **Output:** Notable findings with evidence + adversarial challenge to the most bullish upstream agent claim. If nothing new is found, "No additional signals identified" is a valid output — never pads findings.
- **Key failure mode it catches:** Critical context missed by structured analysis (e.g., buyer's platform migration creates urgency window) + overconfident upstream agent outputs that Synthesis would otherwise inherit unchallenged

#### Agent 10: Synthesis Agent
- **Lens:** What is the complete picture, and what should leadership do?
- **Analyzes:** All 9 agent outputs, cross-referencing and reconciling their perspectives. **Step 1:** Maps contradictions between agents before writing anything — where agents agree (strengthening confidence) and where they contradict (requiring explicit resolution). **Step 2:** Weights agent findings by (agent_confidence × evidence_density), with sparse_data_flag agents at 0.8× weight.
- **Output produces:**
  1. **Contradiction Map** — For each dimension (stage, health, risk, stakeholders, momentum): which agents agree, which contradict, how the contradiction was resolved, resolution confidence. Unexplained contradictions are a quality failure.
  2. **Deal Memo** — Narrative assessment (3-5 paragraphs): deal situation and stage, stakeholder and relationship health, primary risks with evidence, momentum and next steps, unusual signals from Agent 9
  3. **Structured Fields:**
     - AI-inferred deal stage + confidence (0.0-1.0)
     - Deal health score (0-100, derived from 8-component weighted breakdown — Section 7.11)
     - Health score breakdown by component (economic buyer: /20, stage: /15, momentum: /15, technical: /10, competitive: /10, stakeholder: /10, commitment: /10, commercial: /10)
     - Momentum direction + trend
     - AI forecast category (Commit/Best Case/Pipeline/Upside/At Risk/No Decision Risk)
     - Top 5 positive signals with supporting agents and evidence
     - Top 5 risks with severity, supporting agents, and evidence
     - Recommended actions (up to 5 — WHO does WHAT by WHEN and WHY, with priority and owner)
  4. **Confidence Interval** — overall_confidence (0.0-1.0), rationale, key_unknowns[]. A score of 65 at 0.8 confidence (rich data across 5 calls) is a different signal than 65 at 0.3 confidence (sparse data). Health scores reported as ranges in narrative (e.g., "55-65 range, most likely 60").

### 7.4 Standardized Agent Output Schema

All 9 analysis agents (Agents 1-9) produce output in an identical JSON envelope. Agent-specific data goes in the `findings` field. This standardization enables the Synthesis Agent to reliably consume all outputs.

```json
{
  "agent_id": "agent_3_commercial",
  "deal_id": "{{deal_id}}",
  "analysis_date": "{{analysis_date}}",
  "transcript_count_analyzed": 4,
  "narrative": "2-4 paragraphs of analytical prose",
  "findings": {
    "/* agent-specific structured fields */"
  },
  "evidence": [
    {
      "claim_id": "eb_not_present",
      "transcript_index": 2,
      "speaker": "BUYER_SARAH_CHEN (MerchantCo — VP Payments)",
      "quote": "I'll need to run this by David in finance before we can move forward on pricing.",
      "interpretation": "Champion relaying pricing to unseen EB — direct budget authority has not appeared."
    }
  ],
  "confidence": {
    "overall": 0.65,
    "rationale": "Clear commercial signals but EB never appeared on calls.",
    "data_gaps": ["Economic buyer engagement unknown", "Competitor pricing not discussed"]
  },
  "sparse_data_flag": true
}
```

**Evidence citation rules:**
- `claim_id` uses snake_case, max 30 chars, matches a finding in the `findings` block
- `speaker` always includes company affiliation and role when known
- `quote` must be verbatim or marked with `[paraphrased]`
- `interpretation` is one sentence explaining causal relevance
- Every factual claim requires at least one evidence citation. Claims without citations must be flagged in `data_gaps`.

**Confidence calibration scale (shared across all agents):**

| Score | Meaning | Evidence Requirement |
|-------|---------|---------------------|
| 0.9-1.0 | Unambiguous | Multiple corroborating quotes, consistent across transcripts |
| 0.7-0.89 | Clear | 1-2 corroborating quotes, minor ambiguity |
| 0.5-0.69 | Some signal | Single data point or ambiguous language |
| 0.3-0.49 | Weak | Inference without direct evidence |
| 0.1-0.29 | Speculative | Minimal basis, flagging the question only |

**Automatic confidence penalties:**
- Only 1 transcript available: -0.15
- Key stakeholder for domain never appeared: -0.10
- Contradicting evidence exists: -0.10
- Most recent transcript >30 days ago: -0.05
- Sparse data flag = true: confidence ceiling 0.75 (must justify if exceeding)

### 7.5 Agent-Stage Relevance

Not every agent produces equally valuable output at every deal stage. The Synthesis Agent weights agent contributions based on the inferred stage:

| Agent | SQL | Valid. | Commer. | Stakeh. | Legal | Integr. | Onboard. |
|-------|-----|--------|---------|---------|-------|---------|----------|
| 1. Stage & Progress | **High** | **High** | **High** | **High** | **High** | **High** | **High** |
| 2. Relationship & Power | Medium | Medium | **High** | **Critical** | Medium | Medium | Low |
| 3. Commercial & Risk | Low | Low | **Critical** | **High** | Low | Low | Low |
| 4. Momentum & Engagement | Medium | **High** | **High** | **High** | Medium | **High** | **High** |
| 5. Technical Validation | Low | Medium | Low | Low | Low | **Critical** | **High** |
| 6. Economic Buyer | — | Low | Medium | **Critical** | Low | — | — |
| 7. MSP & Next Steps | Low | Medium | **High** | **High** | Medium | **High** | **High** |
| 8. Competitive Displacement | Medium | Medium | **High** | **High** | Low | — | — |
| 9. Open Discovery | Medium | Medium | Medium | Medium | Medium | Medium | Medium |

**Critical** = Agent output is heavily weighted. **High** = Significant weight. **Medium** = Moderate weight. **Low** = Minor weight. **—** = Typically not applicable at this stage.

### 7.6 What "Healthy" Looks Like Per Stage

| Stage | Healthy Pattern | Red Flags |
|-------|----------------|-----------|
| **SQL** | Prospect shares real metrics, NDA signed, clear use case articulated, multiple contacts emerging | Vague pain, no data shared, "we're just exploring," single contact only |
| **Validation** | AE confirms numbers hold up, prospect engaged weekly, data quality solid, use case validated | Metrics don't match claims, prospect goes dark, conflicting data |
| **Commercial** | Pricing/ROI discussion active, champion engaged, competitive position strong, specific timeline, customer initiating next steps | No budget discussion, only technical talk, competitor preferred, timeline vague |
| **Stakeholder Alignment** | Multiple departments on calls, champion driving internal meetings, budget conversations happening, approvals progressing, competitive position clear | Single-threaded, champion goes quiet, "still need to socialize" for months, no budget movement |
| **Legal** | Redlines moving, both legal teams engaged, MSA timeline clear, open items narrowing | Stalled for weeks, new legal issues appearing, scope creep in terms |
| **Integration** | Technical milestones progressing, data flowing, open items narrowing, merchant tech team responsive | Stuck on same issue, merchant tech team unresponsive, scope expanding |
| **Onboarding** | Model iterations converging, performance improving, go-live date set, fewer open items each cycle | Stuck in loops, data quality issues, frustration escalating, no convergence |

### 7.7 Momentum & Forecast Methodology

**Momentum Direction** — The Synthesis Agent derives momentum by comparing agent assessments across the available call arc (up to 5 calls):
- **Improving:** Multiple agents report positive trajectory — new stakeholders appearing, commercial discussions deepening, commitments being met, technical progress advancing
- **Stable:** Agent assessments show consistent patterns without significant change in either direction
- **Declining:** Multiple agents report concerning trends — cadence slowing, commitments slipping, new risks emerging, engagement quality dropping

**AI Forecast Category:**

| Category | Criteria |
|----------|----------|
| **Commit** | Health score 75+, Momentum Stable/Improving, Synthesis Agent finds strong evidence across stage-appropriate agents, high confidence interval, no unresolved critical risks |
| **Realistic** | Health score 50-74, or Improving momentum with partial stage-appropriate progress, at least one customer-initiated next step in last 2 calls, medium+ confidence interval |
| **Upside** | Score below 50, OR Declining momentum, OR critical agents for the inferred stage report significant gaps (e.g., no EB in Stakeholder Alignment, no technical validation in Integration, no catalyst in Competitive Displacement) |

### 7.8 Blind Scoring Protocol

The analysis pipeline operates in strict isolation:

1. **Input:** Raw transcript text preprocessed (speaker normalization, filler removal, 8K token/transcript cap). No deal stage, no IC forecast category, no CRM data.
2. **Step 1 — Stage Inference:** Agent 1 (Stage & Progress) processes all transcripts and outputs inferred stage + confidence. This runs first because stage context informs all downstream agents.
3. **Step 2 — Parallel Analysis:** Agents 2-8 receive preprocessed transcripts + Agent 1's stage context. All 7 run simultaneously, each producing standardized output (Section 7.4).
4. **Step 3 — Open Discovery:** Agent 9 receives all transcripts + outputs from Agents 1-8. Catches gaps and challenges the most optimistic finding from upstream agents.
5. **Step 4 — Synthesis:** Agent 10 reads all 9 outputs, maps contradictions, and produces the deal memo + structured fields (health score, stage, forecast category, risks, actions) + confidence interval.
6. **Step 5 — Output Validation:** Automated structural and content validation (Section 7.10) runs before output reaches any user interface.
7. **Comparison layer (separate):** IC forecast category is entered by VP/TL independently after the AI scoring pipeline completes. Divergence computed post-hoc.

### 7.9 Calibration System

Calibration values are separated from prompt logic — prompts define *what* to analyze, calibration config controls *how aggressively* to interpret signals. TLs can tune the system during bi-weekly calibration without prompt engineering expertise.

**Calibration configuration (excerpt — full config is a versioned YAML file):**

```yaml
## SIS CALIBRATION CONFIG v1.0
global:
  confidence_ceiling_sparse_data: 0.60
  sparse_data_threshold: 3          # transcripts below this = sparse flag
  stale_signal_days: 30

agent_6_economic_buyer:
  eb_absence_health_ceiling: 70     # max health score if EB never appeared
  secondhand_mention_counts_as_engaged: false

synthesis_agent_10:
  health_score_weights:
    stage_appropriateness: 15
    economic_buyer_engagement: 20   # highest weight
    momentum_quality: 15
    technical_path_clarity: 10
    competitive_position: 10
    stakeholder_completeness: 10
    commitment_quality: 10
    commercial_clarity: 10
  forecast_commit_minimum_health: 75
  forecast_at_risk_maximum_health: 45
```

**Calibration workflow (bi-weekly):**
1. Run SIS on 10-20 historical deals with known outcomes
2. Compare health scores and forecast categories against actuals
3. Adjust calibration config values (not prompt logic)
4. Validate on holdout set
5. Increment config version, document changes in CalibrationLog

### 7.10 Agent Guardrails & Safety Rules

Each agent has hard constraints ("NEVER rules") enforced at the prompt level and validated at the output layer.

**Per-Agent NEVER Rules (critical subset):**

| Agent | NEVER Rule |
|-------|-----------|
| 1. Stage & Progress | NEVER infer stage from labels spoken in conversation. Measure behaviors, not labels. |
| 2. Relationship & Power | NEVER call someone a "champion" based solely on friendliness or question-asking. Require advocacy behavior evidence. |
| 3. Commercial & Risk | NEVER output a specific pricing number derived from inference rather than explicit transcript statement. |
| 4. Momentum & Engagement | NEVER count seller-side engagement metrics as buyer momentum signals. Measure the buyer. |
| 5. Technical Validation | NEVER classify a technical topic as "validated" when it was raised but deferred to follow-up. |
| 6. Economic Buyer | NEVER count secondhand EB mentions as EB engagement. CFO mentioned ≠ CFO engaged. |
| 7. MSP & Next Steps | NEVER log a next step as "committed" unless the buyer explicitly confirmed it (not just the rep proposing it). |
| 8. Competitive Displacement | NEVER name a specific competitor's pricing or contract details inferred from context. Output "not discussed" when unknown. |
| 9. Open Discovery | NEVER pad findings when nothing new is found. "No additional signals identified" is a valid output. |
| 10. Synthesis | NEVER produce health score >70 if EB has never appeared. NEVER produce Commit forecast without Level 3+ commitments and MSP. |

**Anti-sycophancy instruction (injected into all agent prompts):**
> "You are analyzing transcripts, not supporting the AE. If the evidence is weak, say so clearly. Do not let the seller's enthusiasm influence your assessment of buyer behavior. Measure the buyer."

**Output validation rules (automated, runs before any user sees output):**

| Rule | Check | Failure Action |
|------|-------|----------------|
| Evidence citation required | Every conclusion cites ≥1 transcript passage | Flag as UNVERIFIED |
| Confidence-evidence alignment | HIGH confidence requires 3+ citations | Auto-downgrade if threshold not met |
| No invented specifics | Dollar amounts must appear verbatim in transcript | Reject and require re-generation |
| Absent stakeholder tagging | Stakeholders mentioned but never on calls tagged INFERRED | Auto-tag before sending to Synthesis |
| Prohibited language | "Clearly," "obviously," "strongly indicates" require citation | Auto-detect, require citation or rephrase |

**Divergence flag safety rules:**
1. Never display divergence flags to ICs — TL and VP Sales only
2. Label as "Forecast Alignment Check" — never "AI Disagrees"
3. Include ≥3 neutral explanations for divergence (AI may be wrong, rep has off-channel context, deal at transition point)
4. Never imply sandbagging or happy ears — TL interprets
5. Flags expire after defined review period; not used in annual performance reviews

**Data retention:**
- Raw transcripts: Follow existing Gong retention policy. SIS does not create additional copies.
- Agent outputs and deal briefs: 12 months from deal close or loss.
- Divergence flag history: 6 months. Not included in exports, reports, or board materials.
- Stakeholder maps: Anonymized within 30 days of deal loss.

### 7.11 Evaluation Framework

#### Per-Agent Evaluation Metrics

| Agent | Primary Metric | Target Threshold |
|-------|---------------|-----------------|
| 1. Stage & Progress | Stage accuracy vs. TL review | >70% exact match, >90% within ±1 stage |
| 2. Relationship & Power | Champion identification precision | >75% (TL agrees when champion flagged) |
| 3. Commercial & Risk | Price extraction accuracy | 100% — zero tolerance for price hallucination |
| 4. Momentum & Engagement | Momentum direction accuracy (TL agreement) | >75% |
| 5. Technical Validation | Technical concern recall | >90% |
| 6. Economic Buyer | EB presence/absence accuracy | >80% |
| 7. MSP & Next Steps | Next step recall | >95% |
| 8. Competitive Displacement | Competitor identification recall | >95% |
| 9. Open Discovery | Novel signal rate (not duplicating agents 1-8) | <30% duplication |
| 10. Synthesis | Health-to-outcome correlation | r > 0.6 (6-month lagging) |

**Synthesis Agent health score components (8 dimensions, total = 100):**

| Component | Max Points | What It Measures |
|-----------|-----------|-----------------|
| Economic buyer engagement | 20 | Is budget authority present and engaged? |
| Stage appropriateness | 15 | Is deal stage consistent with timeline and stakeholder engagement? |
| Momentum quality | 15 | Behavioral momentum, not stated enthusiasm |
| Technical path clarity | 10 | Integration complexity assessed, technical stakeholders present |
| Competitive position | 10 | Clear displacement catalyst, no-decision risk assessed |
| Stakeholder completeness | 10 | Key departments represented, champion identified |
| Commitment quality | 10 | MSP exists, high-quality next steps, completion rate |
| Commercial clarity | 10 | Pricing discussed with right people, ROI framing landed |

**Forecast categories (expanded from 3 to 6):**

| Category | Definition |
|----------|-----------|
| **Commit** | High confidence close in current quarter. EB engaged, commercial agreed, legal/procurement started, MSP in place. |
| **Best Case** | Likely but meaningful uncertainty. One of: EB not confirmed, commercial not landed, timeline risk. |
| **Pipeline** | Deal is real but close date uncertain. Multiple open workstreams. |
| **Upside** | Possible but requires significant movement on open issues. |
| **At Risk** | Active deal with stall, regression, or champion weakening signals. |
| **No Decision Risk** | Deal health looks good but status quo inertia, internal politics, or budget freeze elevates no-decision risk. |

#### Cold Start Strategy

| Phase | Timeline | Activities |
|-------|----------|-----------|
| **Phase 0: Retrospective Seeding** | Weeks -2 to 0 | Run SIS on 15-20 historical closed deals (8+ won, 8+ lost, 4-5 stalled). Compare output against known outcomes. Establishes baseline before production. |
| **Phase 1: Light-Touch Feedback** | Weeks 1-4 | TL reviews 3 random deal outputs/week (~20 min). Rates stage accuracy, forecast category, memo quality (1-5). Flags egregious errors. |
| **Phase 2: Calibration** | Weeks 5-8 | First bi-weekly calibration with accumulated TL feedback. Identify top 2-3 underperforming agents. Run before/after on prompt changes. |

#### Regression Detection

**Golden test set:** 20-25 deal snapshots, fixed and versioned.

| Category | Count | Purpose |
|----------|-------|---------|
| Closed-won (clear signals) | 5 | Correctly identifies healthy deals |
| Closed-lost (clear signals) | 5 | Correctly flags at-risk deals |
| Stalled/ambiguous | 5 | Doesn't over-commit on unclear deals |
| Multi-transcript (3+ calls) | 5 | Synthesis across multiple data points |
| Single transcript only | 5 | Performance under minimal data |

**Regression gates (run before any prompt change deploys):**
- Health score delta > 10 points → hold for review
- Any forecast category flip → hold for review
- Any stage assignment change → hold for review
- Person recall drop > 5% → hold for review
- Golden test set run: <5 min, <$5 in API costs

---

## 8. Architecture & Technical Considerations

### POC Architecture (Local)

```
┌──────────────────┐
│  Gong Transcript  │
│  (Manual Input)   │
└────────┬─────────┘
         │
         v
┌────────────────────┐
│  Transcript        │  Speaker normalization, filler removal,
│  Preprocessor      │  8K token/transcript cap, truncation markers
└────────┬───────────┘
         │
         v
┌──────────────────────────────────────────────────────────┐
│                    Orchestrator Service                     │
│  Manages execution order, retries, token budgets           │
│                                                            │
│  Agent 1 (Stage) → Agents 2-8 (parallel) → Agent 9 → 10  │
│                                                            │
│  Prompt Version Control: Git-like versioning + rollback    │
│  Calibration Config: YAML, separate from prompt logic      │
└────────┬─────────────────────────────────────────────────┘
         │
         v
┌────────────────────┐
│  Output Validator   │  Schema validation + content guardrails
│  (Automated)        │  before storage (Section 7.10)
└────────┬───────────┘
         │
         v
┌────────────────────┐
│    Data Store       │
│  (Local JSON/DB)    │
└────────┬───────────┘
         │
    ┌────┴────┐
    v         v
┌──────────┐  ┌──────────┐
│ Dashboard │  │ Chat     │
│ (Insights)│  │ (Query)  │
└──────────┘  └──────────┘
```

### Design-for-Migration Principles

The POC MUST be architected to migrate to **Salesforce Lightning Web Components (LWC)** as the production deployment platform, with **Next.js** as an intermediate frontend (Phase 2) that maps 1:1 to LWC components:

1. **Multi-agent architecture:** Each of the 10 agents is a separate, independently deployable unit that can be exposed via FastAPI endpoints and later called from Apex controllers in Salesforce. Sequential-parallel execution: Agent 1 → Agents 2-8 parallel → Agent 9 → Agent 10.
2. **Structured data model:** All agent outputs use standardized JSON schema (Section 7.4) that maps to Salesforce custom objects.
3. **Prompt-as-configuration:** Agent prompts use XML-structured templates with `[AGENT-SPECIFIC]` extension points. Calibration values (YAML config) are separated from prompt logic — TLs can tune thresholds without touching prompts.
4. **API-first:** All system functions accessible via API calls, not just UI.
5. **Last-5-calls architecture:** The system may never get full call repository access. All analysis must work permanently on up to 5 transcripts per account. This is a design constraint, not a POC limitation.
6. **Blind analysis pipeline:** The entire multi-agent pipeline operates in strict isolation — agents receive only preprocessed transcript text. Deal stage, IC forecast, and all other metadata are excluded from the analysis pipeline and handled in separate layers.
7. **Infrastructure services (new in v1.4):**
   - **Transcript Preprocessor:** Speaker normalization to `ROLE_NAME (Company)` format, filler removal, 8K token/transcript cap, total context budget 60K tokens
   - **Orchestrator:** Manages agent execution order (sequential-parallel), retries on failure, token budget enforcement
   - **Prompt Version Control:** Git-like versioning for prompts with rollback capability and calibration config history
   - **Output Validator:** Schema validation + content guardrails (Section 7.10) before storage
   - **Feedback Collector:** TL agree/disagree interface for continuous calibration (lightweight — Google Form or Notion during POC)

### Data Model (Extensible)

```
Account
├── account_id (maps to SF Account ID)
├── account_name
├── mrr_estimate
├── ic_forecast_category (Commit/Realistic/Upside) — entered separately by VP/TL, NOT provided to scoring engine
├── team_lead
├── ae_owner
│
├── Transcripts[] (up to 5 per account — permanent design constraint)
│   ├── transcript_id
│   ├── date
│   ├── participants[]
│   ├── duration_minutes
│   └── raw_text
│
├── AgentAnalyses[] (per-transcript, per-agent outputs — standardized schema, Section 7.4)
│   ├── transcript_id
│   ├── agent_id (1-9: Stage/Relationship/Commercial/Momentum/Technical/EB/MSP/Competitive/OpenDiscovery)
│   ├── agent_name
│   ├── narrative_output (analytical prose, 2-4 paragraphs)
│   ├── structured_findings{} (agent-specific structured data)
│   ├── evidence[] (claim_id, transcript_index, speaker, quote, interpretation)
│   ├── confidence{} (overall: 0.0-1.0, rationale, data_gaps[])
│   ├── sparse_data_flag (boolean — true if <3 transcripts)
│   └── created_at
│
├── DealAssessment (Synthesis Agent output — scored blind, no CRM data)
│   ├── deal_memo (narrative assessment, 3-5 paragraphs)
│   ├── contradiction_map[] (dimension, agents_in_agreement, agents_in_contradiction, resolution)
│   ├── inferred_stage (1-7: SQL/Validation/Commercial/Stakeholder/Legal/Integration/Onboarding)
│   ├── stage_confidence (0.0-1.0)
│   ├── stage_reasoning
│   ├── health_score (0-100, derived from 8-component weighted breakdown — Section 7.11)
│   ├── health_score_breakdown{} (stage_appropriateness, eb_engagement, momentum_quality, technical_path, competitive_position, stakeholder_completeness, commitment_quality, commercial_clarity)
│   ├── synthesis_reasoning (paragraph explaining score derivation with agent references)
│   ├── score_confidence_interval{} (overall_confidence: 0.0-1.0, rationale, key_unknowns[])
│   ├── momentum (Improving/Stable/Declining)
│   ├── momentum_trend (Improving/Stable/Declining/Unknown)
│   ├── ai_forecast_category (Commit/Best Case/Pipeline/Upside/At Risk/No Decision Risk)
│   ├── forecast_confidence (0.0-1.0)
│   ├── forecast_rationale (what would change the category up or down)
│   ├── top_positive_signals[] (up to 5, with supporting_agents[] and evidence_summary)
│   ├── top_risks[] (up to 5, with severity and supporting_agents[])
│   ├── recommended_actions[] (up to 5 — WHO does WHAT by WHEN and WHY, with priority and owner)
│   ├── divergence_flag (boolean — computed post-hoc after IC forecast entered)
│   ├── divergence_explanation
│   └── last_updated
│
├── ScoreFeedback[] (TL calibration input)  [P0]
│   ├── feedback_id
│   ├── author (TL name)
│   ├── date
│   ├── deal_health_score_at_time
│   ├── disagreement_direction (too_high / too_low)
│   ├── reason_category (off_channel / stakeholder_context / stage_mismatch / score_too_high / other)
│   ├── free_text_reasoning
│   ├── off_channel_activity (Y/N)
│   └── resolution (accepted / rejected / pending — updated after calibration cycle)
│
├── CalibrationLog[]  [P0]
│   ├── calibration_date
│   ├── config_version (incremented each cycle)
│   ├── feedback_items_reviewed (count)
│   ├── agent_prompt_changes{} (which agents updated, before/after summary)
│   ├── calibration_config_changes{} (YAML config diffs — thresholds, weights, penalties)
│   ├── stage_relevance_weight_changes{} (before/after per agent-stage pair)
│   ├── golden_test_set_results{} (pass/fail per test case, regressions detected)
│   ├── tl_agreement_rate_per_agent{} (rolling 2-week average)
│   └── approved_by
│
└── RepPerformance  [P1]
    ├── behavior_scores{}
    ├── coaching_log[]
    └── trend_over_time[]

--- Phase 2 extensions ---
├── SalesforceData{} (stages, dates, amounts, activities)
├── EmailSignals{} (cadence, responsiveness, stakeholder coverage)
└── HistoricalOutcome{} (won/lost, actual MRR, cycle length)
```

---

## 9. Pipeline Review Workflow (Improved)

### Current State
Screen-share, go Q-by-Q through forecast categories, team leads narrate updates. Rep-driven, recency-biased, time-inefficient.

### Future State with SIS

**Pre-Meeting (automated, 24 hours before review):**
1. System generates one-page deal brief per account in Commit and Realistic
2. Brief includes: Health Score, Momentum, top 3 positive signals, top 2 risks, 2 inspection questions
3. Briefs distributed to team lead — they arrive informed

**Meeting Structure (60 min, same cadence):**

| Segment | Time | Content |
|---------|------|---------|
| Commit Review | 20 min | Start with AI brief, rep responds to specific flags, TL asks pre-generated inspection questions |
| Realistic Review | 20 min | Same structure. Focus on momentum — improving deals get acceleration discussion, declining get root cause |
| Divergence Review | 10 min | Deals where AI and IC categories differ. Highest-value inspection targets. |
| Action Items | 10 min | What needs to happen in the next 2 calls to change the signal score? Tied to objective criteria. |

**Post-Meeting:**
AI brief updated with TL annotations. Creates audit trail.

---

## 10. Success Metrics

### Leading Indicators (change in weeks)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Pipeline review prep time | Reduced from 2+ hours to <30 min | Self-reported by TLs |
| % of deals with AI health score | 100% of active deals within 30 days | System metric |
| Time to answer "how is deal X?" | <30 seconds via conversational interface | Measured in system |
| TL satisfaction with deal briefs | >4/5 rating | Weekly survey |

### Lagging Indicators (change in months)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Forecast accuracy | <20% miss rate (current est. 40%+) | Compare AI vs. IC vs. actual at quarter close |
| Deal slippage without early warning | Reduce by 50% | Deals that move from Commit/Realistic to lost without prior AI risk flag |
| Call listening hours for leadership | Reduce by 80% | Self-reported |
| Time from "deal at risk" to "intervention" | Reduce from days to same-day | System flag timestamp vs. TL action timestamp |

---

## 11. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Reps perceive system as surveillance** | High | High | Position output exclusively for TLs/pipeline review, not rep scorecards. Frame as "better prep = more efficient reviews." Agent outputs never reference rep behavior — grounded in buyer signals only. |
| **False negatives on large strategic deals** | Medium | High | Build override/annotation layer. Large enterprise buyers are guarded on calls — system states confidence level, doesn't claim certainty. |
| **Transcripts miss off-channel activity** | High | Medium | Add "off-channel activity" indicator (manual Y/N) to deal brief. Acknowledge data limitation explicitly. |
| **Agent prompts need calibration** | High | Medium | Calibration config separated from prompt logic (Section 7.9). TLs tune YAML thresholds bi-weekly. Golden test set (25 deals) prevents regression. Target 2 calibration cycles in first 60 days. |
| **POC data too limited for meaningful forecast** | Medium | High | Cold start strategy: retrospective seeding with 15-20 historical closed deals before production launch. POC proves "transcript signals are directionally useful." |
| **Adoption resistance from middle management** | Medium | Medium | Start with 1-2 champion TLs, prove value, expand. Don't mandate org-wide on day one. |
| **Stakeholder/champion confabulation** | High | High | Agent 2 hard rule: NEVER call someone "champion" based on friendliness alone. Mandatory evidence citations. Output validation layer catches unverified claims. (Section 7.10) |
| **Sycophantic scoring (AI absorbs seller optimism)** | Medium | High | Anti-sycophancy instruction in all prompts: "Measure the buyer, not the seller." Behavioral evidence always outweighs stated enthusiasm. |
| **Divergence flag weaponized in rep meetings** | Medium | Critical | Divergence safety rules: TL-only visibility, labeled "Forecast Alignment Check," includes neutral explanations, expires after review period. (Section 7.10) |
| **Cultural/linguistic bias on non-US deals** | Medium | High | Hebrew/multilingual test cases in golden test set. Agents reduce confidence (not change interpretation) when cultural communication style may affect signal interpretation. |
| **Accumulated small errors cascade to wrong forecast** | Medium | High | Every agent output includes evidence_count field. Synthesis weights conclusions by evidence density, not just directional score. Contradiction mapping required. |
| **Prospect PII/competitive intel exposure** | Low | Critical | Data retention policy: stakeholder maps anonymized 30 days after deal loss. Agent 8 never logs specific competitor pricing inferred from context. Access tiers enforced. (Section 7.10) |

---

## 12. CRO Review — Conditions for Approval

**Review status:** Approved with conditions
**Reviewer:** GTM Lead (CRO-level)

### Condition 1: Adoption Protocol (Must complete before development)

Before a single line of code is written:

| Item | Detail | Owner | Deadline |
|------|--------|-------|----------|
| Name POC team leads | Select 2 champion TLs. Recommend volunteers, not assigned. | VP Sales | Before POC kickoff |
| Commitment agreement | Each TL commits to minimum weekly engagement: use the system in at least 1 pipeline review per week, provide score feedback on at least 5 deals per week | VP Sales + TLs | Before POC kickoff |
| Usage tracking | Define how usage compliance will be monitored (system login frequency, feedback submissions, conversational queries) | CRM/AI Team | Week 1 of POC |
| VP reinforcement plan | VP Sales commits to reviewing system output in 1:1s with POC TLs weekly, reinforcing adoption through leadership behavior | VP Sales | Ongoing during POC |

### Condition 2: Divergence Flag Handling Protocol (Must complete before development)

The AI-vs-IC forecast divergence flag is the highest-value and highest-risk feature in this PRD. Mishandled, it creates political incidents.

| Decision | Specification |
|----------|---------------|
| **Who sees divergence flags?** | Team Leads and VP Sales only. NOT visible to ICs in any phase. |
| **In what context?** | Divergence flags appear in: (1) the pre-meeting deal brief (async, private to TL), (2) the divergence review segment of the pipeline review meeting, (3) the VP-level forecast comparison report. They do NOT appear in any rep-facing surface. |
| **Escalation protocol** | When AI flags a deal differently from the IC: TL reviews evidence in deal brief → discusses with rep in pipeline review using inspection questions (not "the AI says you're wrong") → TL makes final call on forecast category → TL logs reasoning in score feedback system. |
| **Framing language** | The system never says "the rep is wrong." It says "the transcript signals suggest [X] — here are the specific signals and evidence." The TL interprets. |
| **Dry-run requirement** | VP Sales must review 5+ divergence flag outputs in a dry run before any TL sees the feature. Adjust framing/presentation based on VP feedback. |

### Condition 3: Binary POC Success Criteria (Must define before development)

Phase 2 investment is approved if and only if ALL of the following are met at POC Week 8:

| Criterion | Threshold | Measurement |
|-----------|-----------|-------------|
| Deal coverage | 80%+ of active POC deals have AI health score updated within prior 2 weeks | System metric |
| TL engagement | At least 1 TL uses conversational interface 3+ times/week for 4 consecutive weeks | System metric |
| Pipeline review adoption | System deal briefs used in at least 4 pipeline review meetings during POC | Self-reported by TLs |
| Score feedback loop active | At least 20 score feedback submissions from TLs during POC (proves calibration loop is working) | System metric |
| VP judgment | VP Sales judges forecast comparison "materially useful" in at least 2 pipeline review cycles | VP Sales attestation |
| Forecast directional accuracy | AI category matches actual deal trajectory in 60%+ of cases where sufficient transcript data exists | Measured at POC close |

### Additional CRO Requirements

**Baseline measurement (before POC starts):**
- Document current forecast miss rate formally. Pull the last 4 quarters of forecast-vs-actual data from Salesforce. This becomes the benchmark against which the system is measured.

**Change management narrative (before first TL login):**
- VP Sales sends a brief communication to the GTM org positioning the system as: "A tool that helps leadership prepare better for pipeline reviews and reduces the time burden on team leads and reps during review meetings." Explicitly NOT framed as "AI that checks your forecast."

**Rep awareness posture:**
- Reps will be informed that Gong transcripts are being analyzed to generate deal health insights for pipeline reviews. Framing: "This helps your TL come to reviews better prepared so the meeting is more efficient and focused." No rep performance data is surfaced in Phase 1.

---

## 13. Competitive Landscape & Build Justification

### Why Build Custom vs. Buy Off-the-Shelf

The revenue intelligence market (~$5B, growing 15-22% CAGR) is designed for the **wrong customer segment**:

| Gap | Detail |
|-----|--------|
| **Volume assumptions** | Gong/Clari ML requires hundreds-to-thousands of deals. Riskified has ~100. Statistical methods break down. |
| **Cycle length mismatch** | Tools optimized for 30-90 day cycles. A 12-month deal needs longitudinal analysis across 20+ touchpoints — no platform does this well. |
| **MRR complexity** | Standard tools assume fixed ACV. Riskified's MRR model (GMV-dependent) requires probabilistic forecasting no vendor supports natively. |
| **Buying committee depth** | Riskified deals involve 5-7 stakeholders (CFO, VP Risk, CTO, Legal, Procurement). No tool tracks multi-stakeholder health scoring at this granularity. |
| **Custom qualification** | Riskified's BD-to-AE SQL criteria (NDA, metrics, DM, timeline, use case) don't map to standard MEDDIC fields in any tool. |
| **Coaching calibration** | AI coaching tools evaluate transactional selling behaviors. Strategic enterprise fraud-prevention selling requires different rubrics. |
| **Cost** | Gong at scale: $50K platform + $1,600/user/year. Custom intelligence layer: significantly lower 3-year TCO. |

### What to Learn From Existing Tools
- **From Gong:** Call tagging taxonomy, talk-ratio metrics, deal board UX patterns
- **From Clari:** Forecast rollup visualization, confidence scoring presentation
- **From People.ai:** Activity-based engagement scoring (apply to transcript data)
- **From 6sense:** Buying group signal aggregation for multi-stakeholder deals

---

## 14. Phasing

| Phase | Scope | Data Sources | Users | Timeline |
|-------|-------|-------------|-------|----------|
| **Phase 1: POC** | Pipeline Intelligence + Objective Forecasting via 10-agent sequential-parallel pipeline (transcript-only, blind scoring, AI stage inference). Includes: preprocessor, orchestrator, output validator, calibration config, golden test set (25 deals), cold start retrospective seeding. | Gong transcripts (last 5/account, manual). Last-5-calls constraint is permanent, not POC-only. | 1-2 champion TLs + VP | 6-8 weeks |
| **Phase 2: Expand** | Add SF data, email signals as supplementary agent inputs. Full TL rollout. L&D pillar (rep performance agents). Stage inference validated against SF opportunity stage. | Gong (last 5/account) + Salesforce + Outreach | All TLs + middle mgmt | 3-4 months |
| **Phase 2.5: Next.js + FastAPI** | Rebuild frontend in Next.js with FastAPI REST layer. Component architecture designed for 1:1 LWC migration. PostgreSQL migration. Production deployment. | Gong (last 5/account) + Salesforce + Outreach | All TLs + middle mgmt | Included in Phase 2 |
| **Phase 3: Scale** | Salesforce Lightning Web Component deployment, rep-facing features, historical training, dynamic agent ontology (agents evolve based on accumulated deal patterns) | Full data stack | Entire GTM org | 3-6 months |

---

## 15. Open Questions

| # | Question | Owner | Priority |
|---|----------|-------|----------|
| OQ1 | What is the exact format of Gong transcript exports? (Plain text? JSON? What metadata is included?) | VP Sales / Gong Admin | P0 — blocks POC build |
| OQ2 | How many accounts should we target for POC? (Recommend 10-15 for meaningful signal calibration) | VP Sales | P0 |
| OQ3 | Does the CRM and AI team have capacity to own post-launch maintenance and calibration? | CRM/AI Team Lead | P0 |
| OQ4 | What is Riskified's current Salesforce license/tier? Does it support Lightning Web Components and Connected Apps for external API access? | Salesforce Admin | P1 — informs Phase 3 |
| OQ5 | Legal/HR: What are the requirements for informing reps that call transcripts are being analyzed for performance scoring? | Legal / HR | P1 — before L&D pillar |
| OQ6 | Should the system track BD pipeline separately from AE pipeline, given different cycle dynamics? | VP Sales | P1 |
| OQ7 | What is the desired calibration cadence post-POC? Weekly? Bi-weekly? | VP Sales + TLs | P1 |
| OQ8 | How do Salesforce opportunity stages map to the 7 Riskified deal stages defined in this PRD? (For Phase 2 stage inference validation) | Salesforce Admin / RevOps | P1 — informs Phase 2 |
| OQ9 | What is the maximum lookback window for Gong transcripts per account? Will it always be limited to 5, or could it expand to 10? | VP Sales / Gong Admin | P1 |

---

## 16. Consumption Interfaces

Per VP request, the system should be consumable in multiple ways:

| Interface | Description | Priority |
|-----------|-------------|----------|
| **Dashboard** | Insights-rich pipeline view with health scores, divergence flags, team rollups, drill-down. Not just data display — proactive insights and recommendations. | P0 |
| **Conversational AI** | Natural language query interface. "Tell me about Account X." "Which deals need attention?" "Compare my forecast to the AI forecast." | P0 |
| **Deal Brief (Report)** | Auto-generated one-pager per deal, designed for pipeline review prep. Exportable/printable. | P0 |
| **Forecast Comparison Report** | AI vs. IC forecast at team and org level. Board-presentable format. | P0 |
| **Alerts/Push Notifications** | Slack or email alerts for critical changes (deal health drops, new risk flag, divergence detected). | P1 |

---

*This PRD was generated collaboratively by 12 AI agents: 8 product agents (Product Manager, Business Analyst, UX Researcher, Data Analyst, Sales Strategist, Competitive Intelligence, Market Researcher, GTM Lead/CRO) + 4 Data & AI agents (Agent Architect, Prompt Engineer, AI Eval Engineer, AI Safety Analyst) based on requirements gathering with the VP Sales.*

*v1.3: CRO review complete, architecture updated to multi-agent lenses.*
*v1.4: AI team enhancement review complete — added sequential-parallel workflow, standardized output schema, calibration system, agent guardrails & safety rules, evaluation framework (golden test set, cold start strategy, regression detection), expanded forecast categories (3→6), expanded risk table (6→12), and infrastructure components (preprocessor, orchestrator, output validator, prompt version control, feedback collector).*

*Next step: VP Sales sign-off on CRO conditions, then complete pre-launch requirements (adoption protocol, divergence handling, baseline measurement, retrospective seeding), then engineering planning with dev and product leads.*
