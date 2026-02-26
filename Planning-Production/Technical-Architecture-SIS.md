# Technical Architecture: Riskified Sales Intelligence System (SIS)

**Version:** 2.0 (Production Update)
**Original Architecture Date:** February 19, 2026
**Updated:** February 26, 2026
**Author:** VP Sales (AI-assisted)
**Status:** POC Complete — Architecture reflects actual implementation

---

## Document Purpose

This is the **production-updated** version of the Technical Architecture document. It reflects the system as actually built, including all deviations from the original plan, features added beyond the plan, and the current state of every component. The original architecture doc is preserved in `/Documents/Sales/Technical-Architecture-SIS.md`.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vercel)                     │
│              Next.js 16 + React 19 + Tailwind 4         │
│                  28 pages, 33+ components                │
│           TanStack React Query + shadcn/ui               │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS (REST + SSE)
                      │ JWT Bearer Token
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                        │
│              Uvicorn, Port 8000, 4 workers                │
│           14 route modules, 50+ endpoints                │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │   Auth   │  │ Services │  │  Alerts  │  │ SSE    │ │
│  │  (JWT)   │  │  (20)    │  │  Engine  │  │ Stream │ │
│  └──────────┘  └────┬─────┘  └──────────┘  └────────┘ │
│                     │                                    │
│  ┌──────────────────┴──────────────────────────────┐    │
│  │              Orchestrator                        │    │
│  │  Agent 1 → Agents 0E+2-8 (parallel) → 9 → 10   │    │
│  │  Progress Store + Batch Store + Cost Tracker     │    │
│  └─────────────────────┬────────────────────────────┘   │
│                        │                                 │
│  ┌─────────────────────┴────────────────────────────┐   │
│  │           LLM Client (Anthropic SDK)             │   │
│  │  Model Router: Haiku (A1) / Sonnet (A2-10)      │   │
│  │  Prompt Loader: YAML + Jinja2 Templates          │   │
│  └──────────────────────────────────────────────────┘   │
│                        │                                 │
│  ┌─────────────────────┴────────────────────────────┐   │
│  │           Database (SQLAlchemy 2.0)              │   │
│  │  Dev: SQLite + WAL  |  Prod: PostgreSQL 16       │   │
│  │  14 tables, role-based scoping                   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              External Integrations                       │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ Anthropic  │  │  Google    │  │  Slack Webhook   │  │
│  │ Claude API │  │  Drive     │  │  (Alerts)        │  │
│  └────────────┘  └────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack (As Built)

### 2.1 Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.1.6 | React meta-framework with App Router |
| React | 19.2.3 | UI library |
| TypeScript | 5 | Static typing |
| Tailwind CSS | 4 | Utility-first CSS |
| shadcn/ui | Latest | Headless accessible component primitives (Radix UI) |
| TanStack React Query | 5.90.21 | Server state management, caching |
| TanStack React Table | 8.21.3 | Data table component |
| Recharts | 3.7.0 | Charting library |
| Lucide React | 0.575.0 | Icon library |
| Vitest | 4.0.18 | Unit testing |
| @testing-library/react | 16.3.2 | Component testing |
| Playwright | 1.58.2 | E2E testing |
| MSW | 2.12.10 | API mocking for tests |

### 2.2 Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115+ | REST API framework |
| Uvicorn | 0.34+ | ASGI server |
| SQLAlchemy | 2.0+ | ORM, database abstraction |
| Anthropic SDK | 0.42+ | Claude API client |
| Pydantic | 2.0+ | Data validation |
| PyJWT | 2.8+ | JWT authentication |
| Jinja2 | 3.1+ | Prompt templating |
| PyYAML | 6.0+ | Configuration files |
| tiktoken | 0.8+ | Token counting |
| nest-asyncio | 1.5+ | Async event loop support |
| slack-sdk | 3.33+ | Slack notifications (optional) |
| Pytest | 8.0+ | Testing framework |

### 2.3 Infrastructure

| Component | Technology | Notes |
|-----------|-----------|-------|
| Frontend hosting | Vercel | Automatic from GitHub, CDN, preview deployments |
| Backend hosting (dev) | Local Uvicorn | Port 8000, ngrok tunnel for demo |
| Backend hosting (prod) | Docker Compose | FastAPI + PostgreSQL 16 + Next.js |
| Database (dev) | SQLite + WAL | Single file, `data/sis.db` |
| Database (prod) | PostgreSQL 16 | Docker service, connection pooling |
| LLM Provider | Anthropic Claude | Direct SDK, no LiteLLM wrapper |

### 2.4 Changes from Original Architecture

| Component | Original Plan | Actual |
|-----------|--------------|--------|
| Frontend (Phase 1) | Streamlit | **Skipped** — went directly to Next.js |
| LLM abstraction | LiteLLM wrapper | Direct Anthropic SDK |
| JWT library | python-jose | PyJWT (security fix) |
| Agent models | Haiku (2-8), Sonnet (9-10) | Haiku (1 only), Sonnet (2-10) |
| Preprocessor | Basic text normalization | Gong JSON parser + call topic extraction |
| Data ingestion | Manual paste only | Google Drive batch + manual |
| Auth | Simple username/role | JWT with 5-level org hierarchy |
| Tables | 10 | 14 (added users, teams, coaching, action logs) |

---

## 3. Agent Execution Architecture

### 3.1 Pipeline Flow (11 Agents)

```
Step 1:  Agent 1 (Stage Classifier)           [Haiku — fast, cheap]
            │
            ▼ stage_context
Step 2:  ┌──────────────────────────────────┐
         │  PARALLEL EXECUTION              │
         │  Agent 0E (Expansion only)       │  [Sonnet]
         │  Agent 2  (Relationship)         │  [Sonnet]
         │  Agent 3  (Commercial)           │  [Sonnet]
         │  Agent 4  (Momentum)             │  [Sonnet]
         │  Agent 5  (Technical)            │  [Sonnet]
         │  Agent 6  (Economic Buyer)       │  [Sonnet]
         │  Agent 7  (MSP & Next Steps)     │  [Sonnet]
         │  Agent 8  (Competitive)          │  [Sonnet]
         └──────────────────────────────────┘
                        │ all agent outputs
                        ▼
Step 3:  Agent 9 (Open Discovery / Validator)  [Sonnet]
                        │ + adversarial findings
                        ▼
Step 4:  Agent 10 (Synthesis)                  [Sonnet]
                        │
                        ▼
         DealAssessment: health_score, forecast, memo, actions
```

### 3.2 Agent Registry

| Agent | File | Purpose | Model | Max Output Tokens |
|-------|------|---------|-------|-------------------|
| Agent 0E | `account_health.py` | Expansion: account health, renewal, NPS | Sonnet | 5,500 |
| Agent 1 | `stage_classifier.py` | Blind stage inference (7-stage model) | Haiku | 8,000 |
| Agent 2 | `relationship.py` | Stakeholder mapping, champion ID, power map | Sonnet | 5,500 |
| Agent 3 | `commercial.py` | Pricing, objections, ROI, commercial risk | Sonnet | 5,500 |
| Agent 4 | `momentum.py` | Call cadence, engagement quality, direction | Sonnet | 5,500 |
| Agent 5 | `technical.py` | Integration readiness, POC, tech blockers | Sonnet | 5,500 |
| Agent 6 | `economic_buyer.py` | EB access, budget, decision authority | Sonnet | 5,500 |
| Agent 7 | `msp_next_steps.py` | Mutual success plan, go-live, next steps | Sonnet | 5,500 |
| Agent 8 | `competitive.py` | Status quo, displacement, no-decision risk | Sonnet | 5,500 |
| Agent 9 | `open_discovery.py` | Novel findings, evidence-based challenges, gaps | Sonnet | 5,500 |
| Agent 10 | `synthesis.py` | Consolidate all, health score, forecast, memo | Sonnet | 12,000 |

### 3.3 Stage-Aware Scoring (Major Addition)

The original architecture described stage-relevance weighting. The actual implementation goes much further with **stage-aware baselines**:

**Core principle**: Health score = deal QUALITY at current stage, NOT a progress indicator. A perfect Stage 1 deal with clear next steps CAN score 90+.

**Missing evidence scoring logic**:
- Evidence present (positive or negative) → scored on merit, full range
- Evidence missing + component expected at this stage → low score (1-2 points, ~10-18% of max)
- Evidence missing + component NOT expected at this stage → neutral midpoint score

**Neutral midpoint table** (embedded in Agent 10 prompt):

| Component (Max) | Neutral Score | Expected At |
|-----------------|---------------|-------------|
| Champion (12) | 5 | Stage 3+ |
| Commitment (11) | 5 | Stage 5+ |
| Economic Buyer (11) | 4 | Stage 4+ |
| Urgency (10) | 4 | Stage 4+ |
| Multi-threading (7) | 3 | Stage 3+ |
| Competitive (7) | 3 | Stage 3+ |
| Technical Path (6) | 3 | Stage 5+ |

Components always expected (no neutral baseline): Pain & Commercial, Momentum, Stage Fit, Account Health.

### 3.4 Prompt Architecture

Each agent uses a **YAML prompt file** with embedded instructions. Prompts are NOT Jinja2 templates (the original plan called for Jinja2 templating). Instead, prompts are loaded as raw YAML and the agent's `build_call()` method constructs the LLM call directly.

**Shared prompt elements** (in `schemas.py`):
- Anti-sycophancy instructions
- Anti-pessimism balance (added during scoring overhaul)
- Evidence citation requirements
- Output format specifications

**Agent-specific elements**:
- Domain knowledge (Riskified context)
- NEVER rules (per agent)
- Scoring rubrics
- Stage-aware instructions

### 3.5 Validation System

**NEVER Rules** (`sis/validation/never_rules.py`) — 10 hard guardrails:

| Rule | Applies At | Effect |
|------|-----------|--------|
| Health > 80 without EB | Stage 4+ | Cap at 80 |
| Health > 75 without Champion | Stage 3+ | Cap at 75 |
| Forecast ≤ At Risk if health < 40 | All stages | Force low forecast |
| + 7 additional rules | Various | See `never_rules.py` |

**Confidence penalties** (`sis/validation/__init__.py`):
- Sparse data (< 3 transcripts): confidence ceiling 0.60
- Stale transcripts (> 30 days): reduced confidence
- Low-evidence agents: proportional penalty

### 3.6 Cost Tracking

**Per-agent tracking** (`cost_tracker.py`):
- Model used, input tokens, output tokens
- Cost in USD (from pricing table)
- Retries counted

**Aggregate** (`RunCostSummary`):
- Total cost per run
- Cost per agent
- Cost per account (across runs)

**Typical costs**:
- Single account pipeline: $0.50-1.00
- Batch of 14 accounts: ~$7-14

---

## 4. Data Model (14 Tables)

### 4.1 Core Tables

```
TABLE: users
=============
  id              TEXT PRIMARY KEY     -- UUID
  name            TEXT NOT NULL
  email           TEXT NOT NULL UNIQUE
  role            TEXT NOT NULL        -- admin / gm / vp / team_lead / ic
  team_id         TEXT                 -- FK -> teams.id
  is_active       INTEGER DEFAULT 1
  created_at      TEXT NOT NULL

TABLE: teams
=============
  id              TEXT PRIMARY KEY     -- UUID
  name            TEXT NOT NULL
  parent_id       TEXT                 -- FK -> teams.id (recursive)
  leader_id       TEXT                 -- FK -> users.id
  level           TEXT NOT NULL        -- org / division / team
  created_at      TEXT NOT NULL

TABLE: accounts
================
  id              TEXT PRIMARY KEY     -- UUID
  account_name    TEXT NOT NULL
  deal_type       TEXT DEFAULT 'new_logo'  -- new_logo / expansion_upsell /
                                            -- expansion_cross_sell / expansion_renewal
  cp_estimate     REAL                 -- contract price estimate (annual)
  ic_forecast     TEXT                 -- IC forecast category
  owner_id        TEXT                 -- FK -> users.id
  sf_stage        TEXT                 -- Salesforce stage
  sf_forecast_category TEXT            -- Salesforce forecast
  sf_close_quarter TEXT               -- e.g., "Q1 2026"
  prior_contract_value REAL           -- for expansion deals
  created_at      TEXT NOT NULL

TABLE: transcripts
===================
  id              TEXT PRIMARY KEY     -- UUID
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  call_date       TEXT NOT NULL        -- ISO 8601
  participants    TEXT                 -- JSON: [{name, role, company}]
  duration_minutes INTEGER
  raw_text        TEXT NOT NULL
  preprocessed_text TEXT
  token_count     INTEGER
  call_title      TEXT                 -- extracted or manual
  call_topics     TEXT                 -- JSON: [{topic, confidence}]
  gong_call_id    TEXT UNIQUE          -- dedup key for Gong imports
  upload_source   TEXT                 -- manual / gong / gdrive
  is_active       INTEGER DEFAULT 1   -- 0 = archived (over 5 cap)
  created_at      TEXT NOT NULL

  INDEX: ix_transcripts_account ON (account_id, call_date DESC)
  UNIQUE: ix_transcripts_gong ON (gong_call_id) WHERE gong_call_id IS NOT NULL

TABLE: analysis_runs
=====================
  id              TEXT PRIMARY KEY     -- UUID
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  started_at      TEXT NOT NULL
  completed_at    TEXT
  status          TEXT DEFAULT 'pending' -- pending / running / completed / failed / partial
  trigger         TEXT DEFAULT 'manual'  -- manual / scheduled / batch
  transcript_ids  TEXT                   -- JSON: list of transcript IDs used
  input_tokens    INTEGER DEFAULT 0
  output_tokens   INTEGER DEFAULT 0
  cost_usd        REAL DEFAULT 0
  model_versions  TEXT                   -- JSON: {agent_id: model_version}
  error_log       TEXT                   -- JSON: list of error messages
  deal_type_at_run TEXT                  -- snapshot of deal_type at time of run
  created_at      TEXT NOT NULL

  INDEX: ix_analysis_runs_account ON (account_id, created_at DESC)

TABLE: agent_analyses
======================
  id              TEXT PRIMARY KEY     -- UUID
  analysis_run_id TEXT NOT NULL        -- FK -> analysis_runs.id
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  agent_id        TEXT NOT NULL        -- agent_1_stage, agent_2_relationship, etc.
  agent_name      TEXT NOT NULL        -- display name
  narrative       TEXT                 -- agent's prose analysis
  findings        TEXT                 -- JSON: agent-specific structured findings
  evidence        TEXT                 -- JSON: [{quote, source_transcript, relevance}]
  confidence_overall REAL              -- 0.0 - 1.0
  data_gaps       TEXT                 -- JSON: list of identified gaps
  sparse_data_flag INTEGER DEFAULT 0
  input_tokens    INTEGER DEFAULT 0
  output_tokens   INTEGER DEFAULT 0
  cost_usd        REAL DEFAULT 0
  model_used      TEXT
  retries         INTEGER DEFAULT 0
  status          TEXT DEFAULT 'pending' -- pending / running / completed / failed
  created_at      TEXT NOT NULL

  INDEX: ix_agent_analyses_run ON (analysis_run_id)

TABLE: deal_assessments
========================
  id              TEXT PRIMARY KEY     -- UUID
  analysis_run_id TEXT NOT NULL        -- FK -> analysis_runs.id
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  deal_memo       TEXT                 -- synthesis narrative (markdown)
  inferred_stage  INTEGER              -- 1-7
  stage_name      TEXT
  health_score    INTEGER              -- 0-100
  health_breakdown TEXT                -- JSON: {component: score, ...}
  momentum_direction TEXT              -- Improving / Stable / Declining
  ai_forecast     TEXT                 -- Strong Commit / Commit / Realistic / etc.
  divergence_flag INTEGER DEFAULT 0
  divergence_explanation TEXT
  sf_stage_at_run TEXT                 -- snapshot
  stage_gap_direction TEXT             -- ahead / behind / aligned / null
  created_at      TEXT NOT NULL

  INDEX: ix_deal_assessments_account ON (account_id, created_at DESC)
  UNIQUE: uq_deal_assessment_run ON (analysis_run_id)
```

### 4.2 Feedback & Calibration Tables

```
TABLE: score_feedback
======================
  id                     TEXT PRIMARY KEY
  account_id             TEXT NOT NULL
  deal_assessment_id     TEXT NOT NULL
  author                 TEXT NOT NULL
  feedback_date          TEXT NOT NULL
  health_score_at_time   INTEGER NOT NULL
  disagreement_direction TEXT NOT NULL        -- too_high / too_low
  reason_category        TEXT NOT NULL
  free_text              TEXT
  off_channel_activity   INTEGER DEFAULT 0
  resolution             TEXT DEFAULT 'pending'
  resolution_notes       TEXT
  resolved_at            TEXT
  resolved_by            TEXT
  created_at             TEXT NOT NULL

TABLE: calibration_logs
========================
  id                      TEXT PRIMARY KEY
  calibration_date        TEXT NOT NULL
  config_version          TEXT NOT NULL
  config_previous_version TEXT
  feedback_items_reviewed INTEGER
  agent_prompt_changes    TEXT              -- JSON
  config_changes          TEXT              -- JSON
  golden_test_results     TEXT              -- JSON
  approved_by             TEXT
  created_at              TEXT NOT NULL

TABLE: prompt_versions
=======================
  id                          TEXT PRIMARY KEY
  agent_id                    TEXT NOT NULL
  version                     TEXT NOT NULL
  prompt_template             TEXT NOT NULL
  calibration_config_version  TEXT
  change_notes                TEXT
  is_active                   INTEGER DEFAULT 1
  created_at                  TEXT NOT NULL
```

### 4.3 Communication & Tracking Tables

```
TABLE: chat_sessions
=====================
  id              TEXT PRIMARY KEY
  user_name       TEXT
  started_at      TEXT NOT NULL
  last_message_at TEXT

TABLE: chat_messages
=====================
  id              TEXT PRIMARY KEY
  session_id      TEXT NOT NULL
  role            TEXT NOT NULL        -- user / assistant
  content         TEXT NOT NULL
  tokens_used     INTEGER
  model_used      TEXT
  created_at      TEXT NOT NULL

TABLE: coaching_entries (NEW — not in original plan)
=====================================================
  id              TEXT PRIMARY KEY
  account_id      TEXT
  rep_name        TEXT NOT NULL
  coach_name      TEXT
  dimension       TEXT                 -- stakeholder / objection / commercial / next_steps
  coaching_date   TEXT NOT NULL
  feedback_text   TEXT NOT NULL
  incorporated    INTEGER DEFAULT 0
  created_at      TEXT NOT NULL

TABLE: user_action_logs (NEW — not in original plan)
=====================================================
  id              TEXT PRIMARY KEY
  user_name       TEXT NOT NULL
  action_type     TEXT NOT NULL        -- page_view / forecast_set / analysis_run / etc.
  account_id      TEXT
  action_details  TEXT                 -- JSON
  ip_address      TEXT
  created_at      TEXT NOT NULL
```

### 4.4 PostgreSQL Migration Notes

The schema uses SQLite-compatible types. For PostgreSQL migration:

| SQLite Pattern | PostgreSQL Replacement |
|---------------|----------------------|
| `TEXT` for timestamps | `TIMESTAMP WITH TIME ZONE` |
| `TEXT` for UUIDs | `UUID` (native type) |
| `TEXT` for JSON columns | `JSONB` (indexed, queryable) |
| `INTEGER` for booleans | `BOOLEAN` |
| `REAL` for money | `NUMERIC(10,2)` |

Docker Compose already includes PostgreSQL 16 service with the correct configuration.

---

## 5. API Design (Actual Implementation)

### 5.1 Route Structure

The FastAPI app registers 14 routers with 50+ endpoints:

| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `auth` | `/api/auth` | 3 | Login, logout, me |
| `accounts` | `/api/accounts` | 6 | Account CRUD, IC forecast |
| `transcripts` | `/api/transcripts` | 3 | Upload, list, get |
| `analyses` | `/api/analyses` | 9 | Run, batch, cancel, history, agents, rerun, resynthesize, delta, timeline |
| `dashboard` | `/api/dashboard` | 12 | Pipeline, divergence, team rollup, insights, trends (5 types), command center |
| `chat` | `/api/chat` | 1 | Query with conversation context |
| `feedback` | `/api/feedback` | 4 | Submit, list, resolve, summary |
| `calibration` | `/api/calibration` | 4 | Current, patterns, create, history |
| `export` | `/api/export` | 2 | Deal brief, forecast report |
| `sse` | `/api/sse` | 2 | Analysis progress, batch progress |
| `teams` | `/api/teams` | 4 | List, create, update, members |
| `users` | `/api/users` | 4 | List, list ICs, create, update |
| `gdrive` | `/api/gdrive` | 4 | Config, validate, list accounts, list calls, import |
| `logs` | `/api/logs` | 2 | Actions list, summary |
| + misc | various | 8 | Coaching, prompts, scorecard, forecast, tracking, quotas |

### 5.2 Authentication & Authorization

**Implementation**: JWT (HS256, PyJWT)

**Token payload**:
```json
{
  "username": "roy",
  "role": "vp",
  "user_id": "uuid",
  "exp": 1740000000,
  "iat": 1739900000
}
```

**Role hierarchy** (5 levels):
1. `admin` — full access
2. `gm` — org-wide read, manage VPs
3. `vp` — division-wide access
4. `team_lead` — team-level access
5. `ic` — own deals only

**Data scoping** (`sis/services/scoping_service.py`):
- Recursive BFS to collect descendant team IDs
- Accounts filtered by owner team membership
- Dashboard aggregations respect scope

**Security notes**:
- Production guard: RuntimeError if JWT_SECRET not set when `ENVIRONMENT=production`
- Default dev secret: `sis-dev-secret-change-me` (MUST be replaced)
- Auto-logout on 401 responses (frontend)
- All endpoints require authentication via `Depends(get_current_user)`

### 5.3 Server-Sent Events (SSE)

Two SSE endpoints for real-time progress streaming:

**`GET /api/sse/analysis/{run_id}`** — Per-run pipeline progress
- 1-second polling of in-memory progress store
- Per-agent status: pending → running → completed/failed
- Includes: tokens, cost, elapsed time per agent
- Falls back to DB for completed runs not in memory
- Auto-closes on terminal status
- Timeout: 600 seconds

**`GET /api/sse/batch/{batch_id}`** — Batch analysis progress
- Tracks multiple accounts being analyzed in parallel
- Per-account: uploading → analyzing → completed/failed
- Includes: imported/skipped counts, elapsed time, cost
- Real-time batch-level counters (completed_count, failed_count)
- Auto-cleanup 10 minutes after batch terminal state

### 5.4 Key API Contracts

**Run Analysis**:
```
POST /api/analyses/
Body: { "account_id": "uuid" }
Response: { "status": "started", "account_id": "uuid", "run_id": "uuid" }
```

**Batch Analysis**:
```
POST /api/analyses/batch
Body: { "items": [{ "account_name": "...", "drive_path": "...", "max_calls": 5, ... }] }
Response: { "batch_id": "uuid", "status": "running", "items": [...], "total_items": N }
```

**Cancel Batch**:
```
POST /api/analyses/batch/{batch_id}/cancel
Response: { "status": "cancelled", "batch_id": "uuid", "cancelled_runs": N }
```

**Command Center**:
```
GET /api/dashboard/command-center?team=&ae=&period=&quarter=
Response: CommandCenterResponse (pipeline overview with filters)
```

---

## 6. Orchestrator Architecture

### 6.1 Pipeline Execution (`sis/orchestrator/pipeline.py`)

The pipeline follows a 5-step execution flow:

1. **Step 1**: Agent 1 (Haiku) runs alone → produces stage context
2. **Step 2**: Extract `stage_context` from Agent 1 output
3. **Step 3**: Agents 0E + 2-8 run in PARALLEL via `asyncio.as_completed()`
   - Agent 0E only runs for expansion deals
   - All agents receive stage_context from Agent 1
4. **Step 4**: Agent 9 (Open Discovery) runs serially, reads all prior outputs
5. **Step 5**: Agent 10 (Synthesis) runs serially, produces final assessment

**Design principles**:
- No agent-to-agent communication (all via orchestrator)
- Agents are pure functions: (transcripts, context) → output
- Failed agents retried independently; partial results acceptable
- Agent 1 failure is non-fatal (pipeline continues with stage_context=None)
- Each agent reports progress to the in-memory progress store

### 6.2 Progress Store (`sis/orchestrator/progress_store.py`)

Thread-safe in-memory dict keyed by `run_id`:
- Tracks per-agent status, tokens, cost, elapsed time, errors
- Auto-cleanup 5 minutes after terminal status
- Read by SSE endpoint at 1-second intervals
- Display names for all 11 agents

### 6.3 Batch Store (`sis/orchestrator/batch_store.py`)

Thread-safe in-memory dict keyed by `batch_id`:
- Tracks per-account status in batch operations
- Item statuses: queued → uploading → analyzing → completed/failed
- Batch statuses: running → completed/partial/failed
- Auto-cleanup 10 minutes after batch terminal state
- Cancel support: marks non-terminal items as failed, returns run_ids for cancellation

### 6.4 Cost Tracker (`sis/orchestrator/cost_tracker.py`)

Per-agent pricing lookup and cost aggregation:
- Tracks input/output tokens per agent
- Cost in USD from model pricing table
- Aggregated per-run and per-account

### 6.5 Budget System (`sis/orchestrator/budget.py`)

Token/cost budgets exist but are **not currently enforced** in the pipeline. This is a production TODO.

---

## 7. Frontend Architecture

### 7.1 Page Structure (28 Pages)

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Dashboard redirect |
| Login | `/login` | JWT login |
| Pipeline | `/pipeline` | Deal pipeline (command center with filters) |
| Deals | `/deals` | Deal list with search |
| Deal Detail | `/deals/[id]` | Synthesis-first drill-down |
| Deal Brief | `/deals/[id]/brief` | Exportable one-pager |
| Analyze | `/analyze` | Trigger new analysis |
| Upload | `/upload` | Transcript upload (manual + Google Drive batch) |
| Chat | `/chat` | Conversational query interface |
| Trends | `/trends` | 5-tab analytics dashboard |
| Forecast | `/forecast` | Forecast vs SF, divergence |
| Divergence | `/divergence` | AI vs IC divergence view |
| Team Rollup | `/team-rollup` | Team-level health aggregation |
| Meeting Prep | `/meeting-prep` | 1-on-1 coaching prep |
| Rep Scorecard | `/rep-scorecard` | Rep performance metrics |
| Calibration | `/calibration` | Prompt version management |
| Feedback | `/feedback` | Score feedback management |
| Golden Tests | `/golden-tests` | Regression test runner |
| Activity Log | `/activity-log` | Audit trail |
| Usage | `/usage` | Feature usage analytics |
| Costs | `/costs` | LLM cost tracking |
| Digest | `/digest` | Daily digest summary |
| Seeding | `/seeding` | Retrospective data loading |
| Prompts | `/prompts` | Prompt version history |
| Methodology | `/methodology` | Scoring transparency (glass box) |
| Settings/Teams | `/settings/teams` | Admin team management |

### 7.2 Component Architecture (33+ Components)

**Core data display**: `data-table.tsx`, `filter-chips.tsx`, `deal-table.tsx`
**Deal components**: `deal-memo.tsx`, `agent-card.tsx`, `evidence-viewer.tsx`, `actions-list.tsx`
**Status badges**: `health-badge.tsx`, `health-breakdown.tsx`, `forecast-badge.tsx`, `divergence-badge.tsx`, `delta-badge.tsx`, `momentum-indicator.tsx`
**Progress tracking**: `analysis-progress.tsx`, `analysis-progress-detail.tsx`, `batch-progress-view.tsx`
**Charts/trends**: `deal-health-tab.tsx`, `forecast-movement-tab.tsx`, `pipeline-flow-tab.tsx`, `velocity-tab.tsx`, `team-comparison-tab.tsx`, `waterfall-chart.tsx`, `sparkline.tsx`
**Layout**: `sidebar.tsx` (role-aware navigation), `auth-guard.tsx`, `error-boundary.tsx`
**Communication**: `chat-input.tsx`, `chat-message.tsx`

### 7.3 Custom Hooks (13+)

| Hook | Purpose |
|------|---------|
| `use-accounts` | Account CRUD operations |
| `use-transcripts` | Transcript upload and listing |
| `use-analyses` | Analysis run management |
| `use-batch-analysis` | Batch analysis with SSE progress |
| `use-dashboard` | Dashboard data fetching |
| `use-chat` | Chat conversation management |
| `use-feedback` | Feedback submission and listing |
| `use-trends` | Trend data (5 types) |
| `use-admin` | Admin operations |
| `use-command-center` | Command center state |
| `use-teams` | Team hierarchy |

### 7.4 State Management

- **Server state**: TanStack React Query (fetch, cache, invalidate)
- **Auth state**: React Context (`lib/auth.tsx`) — JWT token, user role, team
- **Local UI state**: React useState/useReducer (filters, expandable rows)
- **Session storage**: Batch analysis ID persistence across page navigation

---

## 8. Service Layer (20 Services)

| Service | File | Key Functions |
|---------|------|---------------|
| **Account** | `account_service.py` | create, update, delete, list (with scoping), set_ic_forecast |
| **Analysis** | `analysis_service.py` | analyze_account, create_run, get_history, get_agents, rerun_agent, resynthesize, get_delta, get_timeline, get_carry_forward |
| **Dashboard** | `dashboard_service.py` | pipeline_overview, divergence, team_rollup, insights, command_center (with recursive team scoping + quarter filter) |
| **Transcript** | `transcript_service.py` | upload, preprocess, get_active_texts, dedup (gong_call_id) |
| **Query** | `query_service.py` | chat query with LLM, context retrieval, intent classification |
| **Feedback** | `feedback_service.py` | submit, list, resolve, summary |
| **Calibration** | `calibration_service.py` | get_current, create, history |
| **Coaching** | `coaching_service.py` | submit_note, list, summary |
| **Export** | `export_service.py` | deal_brief (markdown/PDF), forecast_report |
| **GDrive** | `gdrive_service.py` | validate_path, list_accounts, list_calls, download_and_parse, upload_to_db |
| **Team** | `team_service.py` | list, create, update, members |
| **Scoping** | `scoping_service.py` | role-based data visibility (recursive hierarchy traversal) |
| **Quota** | `quota_service.py` | team quota management |
| **Trend** | `trend_service.py` | deal_health, forecast_movement, pipeline_flow, velocity, team_comparison |
| **Rep Scorecard** | `rep_scorecard_service.py` | rep-level metrics from agent outputs |
| **Prompt Version** | `prompt_version_service.py` | version management, diff |
| **Usage Tracking** | `usage_tracking_service.py` | page views, feature adoption |
| **Action Log** | `user_action_log_service.py` | audit trail (forecast sets, uploads, runs) |
| **Forecast Data** | `forecast_data_service.py` | forecast aggregation (AI vs SF) |
| **Utils** | `utils.py` | shared utilities |

---

## 9. Alert Engine

### 9.1 Detection (`sis/alerts/engine.py`)

| Alert Type | Trigger | Severity | Stage Gate |
|------------|---------|----------|------------|
| `score_drop` | Health fell > 15 points | critical | All stages |
| `forecast_flip` | AI forecast category changed | warning | All stages |
| `stale_call` | No transcript in > 30 days | warning | All stages |
| `new_needs_attention` | Health < 40 (first assessment) | critical | All stages |

### 9.2 Delivery

| Channel | Status | File |
|---------|--------|------|
| Dashboard display | **Working** | `attention-strip.tsx` |
| Slack webhook | **Ready** (needs webhook URL config) | `slack_notifier.py` |
| Email digest | **Engine built** (needs SMTP config) | `email_digest.py` |

---

## 10. Configuration System

### 10.1 Config Files

```
config/
├── agents.yml              # Agent registry (0E through 10)
├── models.yml              # Agent → model routing
├── stage_relevance.yml     # Stage definitions + objectives/exit criteria
└── calibration/
    ├── v1.0.yml            # Calibration parameters (versioned)
    └── current.yml         # Symlink to active version
```

### 10.2 Calibration Parameters

The calibration YAML contains deal-type-specific thresholds:

```yaml
# Key parameters (v1.0)
health_score_weights:        # per-component max points
confidence_ceiling:          # sparse data ceiling (0.60)
sparse_data_threshold:       # transcript count (3)
stale_signal_days:           # days since last call (30)
score_drop_alert_threshold:  # points drop for alert (15)
stale_call_days_threshold:   # days for stale alert (30)

# Stage-gated NEVER rules
never_rule_stage_gates:
  eb_absence_health_ceiling:
    ceiling: 80
    min_stage: 4
  champion_absence_health_ceiling:
    ceiling: 75
    min_stage: 3
  adversarial_challenge_required: false
```

### 10.3 Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Yes | — | LLM API access |
| `ANTHROPIC_BASE_URL` | No | `https://api.anthropic.com` | API endpoint |
| `DATABASE_URL` | No | `sqlite:///data/sis.db` | Database connection |
| `JWT_SECRET` | Prod only | `sis-dev-secret-change-me` | JWT signing key |
| `ENVIRONMENT` | No | `development` | production triggers guards |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Frontend API target |
| `GOOGLE_DRIVE_TRANSCRIPTS_PATH` | No | — | GDrive folder path |
| `BATCH_CONCURRENCY` | No | `3` | Parallel batch items |
| `SLACK_WEBHOOK_URL` | No | — | Slack alert delivery |

---

## 11. Deployment Architecture

### 11.1 Current State (POC Demo)

```
User → Vercel (Next.js frontend)
         ↓ HTTPS
       ngrok tunnel → localhost:8000 (FastAPI backend)
                        ↓
                      SQLite (data/sis.db)
                        ↓
                      Anthropic API
```

- Frontend: `https://frontend-beta-taupe-26.vercel.app`
- Backend: Local FastAPI with ngrok tunnel for demo
- Environment: `NEXT_PUBLIC_API_URL` set on Vercel to ngrok URL

### 11.2 Production Target (Docker Compose)

```yaml
# docker-compose.yml (already configured)
services:
  db:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes: [pgdata]
    healthcheck: enabled

  api:
    build: .  # Dockerfile
    ports: ["8000:8000"]
    depends_on: [db]
    command: uvicorn sis.api.main:app --host 0.0.0.0 --port 8000 --workers 4

  frontend:
    build: ./frontend  # frontend/Dockerfile
    ports: ["3000:3000"]
    depends_on: [api]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
```

### 11.3 Dockerfiles

**Backend** (`Dockerfile`):
- Base: python:3.12-slim
- Copies: pyproject.toml, sis/, config/, prompts/, alembic/
- Installs: `pip install .`
- Runs: 4-worker Uvicorn

**Frontend** (`frontend/Dockerfile`):
- Multi-stage: node:20-alpine → build → standalone
- Output: self-contained Next.js server
- Copies: .next/standalone, .next/static, public/

---

## 12. Testing Architecture

### 12.1 Backend Tests (Pytest)

```
tests/
├── conftest.py                    # Shared fixtures (DB, auth, mock data)
├── test_api/                      # API endpoint tests (12 files)
│   ├── test_accounts.py
│   ├── test_analyses.py
│   ├── test_auth.py
│   ├── test_dashboard.py
│   ├── test_feedback.py
│   └── ... (7 more)
├── test_services.py               # Service layer tests
├── test_models.py                 # ORM model tests
├── test_orchestrator.py           # Pipeline tests
├── test_never_rules.py            # NEVER rules (with stage gates)
├── test_validation.py             # Output validation
├── test_scoping.py                # Role-based access
├── test_golden.py                 # Golden test execution
└── ... (10 more files)
```

**Coverage**: 24+ test files, 400+ test cases

### 12.2 Frontend Tests (Vitest + React Testing Library)

```
frontend/src/__tests__/
├── setup.ts                       # Test configuration
├── mocks/
│   ├── server.ts                  # MSW server
│   └── handlers.ts                # API mock handlers
├── deal-detail.test.tsx           # Deal detail page
└── pipeline-overview.test.tsx     # Pipeline page
```

### 12.3 Golden Test Framework

**Purpose**: Regression detection when prompts or scoring logic changes.

**Gate**: `health_delta > 15` = FAIL (temporarily widened from 10 during scoring overhaul rollout).

**Location**: `sis/testing/golden_test.py` + `config/golden_tests/`

---

## 13. Salesforce LWC Migration Path

### 13.1 Three-Phase Strategy (Unchanged)

| Phase | Frontend | Backend | Status |
|-------|----------|---------|--------|
| Phase 1 (POC) | Streamlit | Python + SQLite | **SKIPPED** |
| Phase 2 (Current) | Next.js + FastAPI | Python + SQLite/PostgreSQL | **COMPLETE** |
| Phase 3 (Future) | Salesforce LWC | Apex → Python API | **PLANNED** |

### 13.2 Portability Rules (Followed Throughout Build)

1. **No Python-specific logic in agent prompts** — prompts are pure text with variable placeholders
2. **Agent I/O is JSON, always** — standardized schemas
3. **Orchestration separate from agent logic** — agents never call other agents
4. **Configuration is data, not code** — YAML files map to SF Custom Metadata
5. **No state inside agents** — stateless functions
6. **REST API as the portability boundary** — any frontend can consume the same endpoints

### 13.3 Component Mapping

| Next.js (Phase 2) | Salesforce LWC (Phase 3) |
|-------------------|-------------------------|
| React components | LWC components |
| Props (`{...}`) | `@api` properties |
| State (`useState`) | `@track` reactivity |
| Events (`onClick`) | CustomEvent dispatch |
| TanStack Query | `@wire` decorators |
| REST fetch | Apex external callouts |
| JWT auth | Salesforce Connected App |
| YAML config | Custom Metadata Types |

---

## 14. Technical Risks (Updated)

### Risks Resolved

| Risk | Original | Resolution |
|------|----------|-----------|
| LLM Output Consistency | HIGH/HIGH | Pydantic validation, NEVER rules, golden tests |
| Prompt Iteration Velocity | HIGH/MEDIUM | YAML prompts, single-agent rerun, calibration system |
| Transcript Variability | MEDIUM/HIGH | Gong parser, GDrive batch import, robust preprocessing |
| Single-Builder Bus Factor | HIGH/CRITICAL | Clean architecture, comprehensive docs, AI assistance |

### Active Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Backend hosting for production | HIGH | HIGH | Docker Compose ready but needs cloud deployment |
| LLM cost at scale (50+ accounts) | MEDIUM | HIGH | RunBudget exists but not enforced |
| SSO integration | MEDIUM | HIGH | Must replace passwordless login |
| SQLite concurrent access | MEDIUM | MEDIUM | PostgreSQL Docker-ready, needs migration |
| Data loss (SQLite single file) | LOW | CRITICAL | Add backup script, move to PostgreSQL |

---

## 15. Project Directory Structure (Actual)

```
SIS/
├── pyproject.toml                 # Python metadata + dependencies
├── Dockerfile                     # Backend container
├── docker-compose.yml             # Full stack deployment
├── .env.example                   # Environment template
│
├── config/
│   ├── agents.yml                 # Agent registry (0E through 10)
│   ├── models.yml                 # Model routing
│   ├── stage_relevance.yml        # Stage definitions
│   ├── calibration/
│   │   └── v1.0.yml               # Calibration parameters
│   └── golden_tests/              # Golden test fixtures
│
├── prompts/                       # YAML prompt templates (11 agents)
│   ├── _base.yml
│   ├── agent_01_stage.yml
│   ├── agent_02_relationship.yml
│   └── ... (9 more)
│
├── sis/                           # Main Python package
│   ├── __init__.py                # nest_asyncio setup
│   ├── config.py                  # Configuration management
│   ├── constants.py               # Application constants
│   │
│   ├── agents/                    # 11 AI agents + runner + schemas (13 files)
│   ├── alerts/                    # Alert engine + Slack + email (3 files)
│   ├── api/                       # FastAPI routes + schemas (25+ files)
│   ├── db/                        # SQLAlchemy models + engine (4 files)
│   ├── llm/                       # Anthropic client + routing (4 files)
│   ├── orchestrator/              # Pipeline + progress + batch (7 files)
│   ├── preprocessor/              # Gong parser + topics (3 files)
│   ├── services/                  # Business logic (20 files)
│   ├── validation/                # NEVER rules + confidence (2 files)
│   ├── testing/                   # Golden test framework (2 files)
│   └── ui/                        # LEGACY Streamlit (dead code, DELETE)
│
├── scripts/                       # Utility scripts (15 files)
│   ├── seed_db.py
│   ├── migrate_hierarchy.py
│   ├── backfill_health_score_v2.py
│   ├── rerun_stage_aware.py
│   └── ... (11 more)
│
├── tests/                         # 24+ test files, 400+ test cases
│   ├── conftest.py
│   ├── test_api/                  # API tests (12 files)
│   ├── test_never_rules.py
│   ├── test_scoping.py
│   └── ...
│
├── frontend/                      # Next.js application
│   ├── package.json
│   ├── Dockerfile
│   ├── next.config.ts
│   └── src/
│       ├── app/                   # 28 pages (App Router)
│       ├── components/            # 33+ React components
│       └── lib/                   # API client, hooks, types, auth
│
├── data/                          # Database + reports (gitignored)
│   ├── sis.db                     # SQLite database
│   └── rerun_reports/             # Pipeline run reports
│
└── docs/                          # Architecture documents
    └── plans/                     # Design documents
```

### File Count Summary

| Directory | Files | Complexity |
|-----------|-------|-----------|
| `sis/agents/` | 13 | Medium — each agent ~150-300 lines |
| `sis/orchestrator/` | 7 | Medium — pipeline is core logic |
| `sis/services/` | 20 | Medium — CRUD + business logic |
| `sis/api/` | 25+ | Low — thin route layer |
| `sis/validation/` | 2 | Medium — rule engine |
| `frontend/src/app/` | 28 pages | Medium — React components |
| `frontend/src/components/` | 33+ | Medium — reusable UI |
| `tests/` | 24+ | 400+ test cases |
| **TOTAL** | ~180+ | **Production-grade for POC** |

---

*Document produced for Riskified SIS Production Phase. Updated from original Technical Architecture v1.0 to reflect actual implementation as of February 26, 2026. Architecture decisions optimized for: stage-aware scoring accuracy, real-time progress tracking, role-based access control, and Salesforce LWC portability.*
