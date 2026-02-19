# Technical Architecture Document: Riskified Sales Intelligence System (SIS)

**Version:** 1.0
**Date:** February 19, 2026
**Status:** Architecture Design — Pre-Implementation
**Audience:** VP Sales (builder), future engineering support
**PRD Reference:** PRD v1.4 — Sections 7, 8, and Data Model

---

## 1. System Architecture Diagram

```
                              RISKIFIED SALES INTELLIGENCE SYSTEM (SIS)
                              ==========================================

    USER LAYER
    ==========
    +---------------------+     +------------------------+
    | Streamlit Dashboard  |     | Converslit Chat Panel  |
    | (Pipeline, Deals,    |     | (Conversational Query  |
    |  Divergence, Team    |     |  Interface — LLM-based |
    |  Rollup, Feedback)   |     |  RAG over stored data) |
    +----------+----------+     +-----------+------------+
               |                            |
               +------------+---------------+
                            |
                            v
    API LAYER (Internal Python functions — not HTTP for POC)
    =========================================================
    +---------------------------------------------------------------+
    |                     SIS Service Layer                          |
    |                                                               |
    |  account_service    analysis_service    query_service          |
    |  feedback_service   dashboard_service   export_service         |
    +---------------------------------------------------------------+
               |                    |                    |
               v                    v                    v
    PROCESSING LAYER
    ================
    +-------------------+
    | Transcript Upload |  (Streamlit file_uploader / text_area)
    | & Association     |  Associates transcript with Account
    +--------+----------+
             |
             v
    +-------------------+
    | Transcript        |  Speaker normalization: "ROLE_NAME (Company)"
    | Preprocessor      |  Filler removal, 8K token/transcript cap
    |                   |  Truncation markers: [TRUNCATED AT 8K TOKENS]
    +--------+----------+  Total context budget: 60K tokens
             |
             v
    +--------------------------------------------------------------+
    |                    ORCHESTRATOR                                |
    |                                                               |
    |  1. Token Budget Manager — enforces per-transcript and total  |
    |  2. Execution Controller — sequential-parallel flow           |
    |  3. Retry Manager — per-agent retry with exponential backoff  |
    |  4. Cost Tracker — logs tokens + cost per agent per run       |
    |                                                               |
    |  STEP 1: Agent 1 (Stage & Progress) ------> stage_context     |
    |              |                                                 |
    |              v                                                 |
    |  STEP 2: +--------+--------+--------+--------+--------+--+    |
    |          |Agent 2  |Agent 3 |Agent 4 |Agent 5 |Agent 6|  |    |
    |          |Relation |Commerc |Momentum|Technic |Econ   |  |    |
    |          +----+----+---+----+---+----+---+----+---+---+  |    |
    |          |Agent 7  |Agent 8 |                             |    |
    |          |MSP/Next |Compet  |                             |    |
    |          +----+----+---+----+                             |    |
    |              |         |                                  |    |
    |              v         v                                  |    |
    |  STEP 3: Agent 9 (Open Discovery / Adversarial) <-- all  |    |
    |              |                                    outputs |    |
    |              v                                            |    |
    |  STEP 4: Agent 10 (Synthesis) <-- all 9 agent outputs    |    |
    +----------------------------+-----------------------------+    |
                                 |                                  |
                                 v                                  |
    +----------------------------+-----------------------------+    |
    |                   OUTPUT VALIDATOR                        |    |
    |                                                          |    |
    |  1. Schema validation (JSON structure per Section 7.4)   |    |
    |  2. Evidence citation check (every claim needs a quote)  |    |
    |  3. Confidence-evidence alignment (HIGH needs 3+ cites)  |    |
    |  4. No invented specifics (dollar amounts verbatim)      |    |
    |  5. Prohibited language detection                        |    |
    |  6. NEVER-rule enforcement (e.g., health >70 without EB) |    |
    |                                                          |    |
    |  Outputs: PASS / WARN (with flags) / FAIL (re-generate) |    |
    +----------------------------+-----------------------------+    |
                                 |                                  |
                                 v                                  |
    DATA LAYER
    ==========
    +----------------------------+-----------------------------+
    |                    SQLite Database                        |
    |              (SQLAlchemy ORM — PostgreSQL-compatible)     |
    |                                                          |
    |  accounts | transcripts | agent_analyses                 |
    |  deal_assessments | score_feedback | calibration_logs     |
    |  analysis_runs | prompt_versions                         |
    +----------------------------------------------------------+

    CONFIGURATION LAYER (file-based, version-controlled)
    =====================================================
    +---------------------+  +----------------------+  +-------------------+
    | Prompt Templates    |  | Calibration Config   |  | Agent Registry    |
    | (YAML + Jinja2)     |  | (YAML — versioned)   |  | (agent metadata,  |
    | prompts/            |  | config/calibration/  |  |  model assignments)|
    |   agent_1_stage.yml |  |   v1.0.yml           |  | config/agents.yml |
    |   agent_2_rel.yml   |  |   v1.1.yml           |  +-------------------+
    |   ...               |  |   current.yml (link) |
    +---------------------+  +----------------------+

    LLM LAYER
    =========
    +--------------------------------------------------------------+
    |                   LLM Abstraction (LiteLLM)                   |
    |                                                               |
    |  Model Router:                                                |
    |    Agents 1-9:  anthropic/claude-3-5-haiku  (or gpt-4o-mini) |
    |    Agent 10:    anthropic/claude-sonnet-4    (or gpt-4o)      |
    |    Chat:        anthropic/claude-sonnet-4    (or gpt-4o)      |
    |                                                               |
    |  Features: retry, fallback, token counting, cost logging      |
    +--------------------------------------------------------------+
```

---

## 2. Technology Stack

### Core Runtime

| Component | Library | Version | Rationale |
|-----------|---------|---------|-----------|
| Language | Python | 3.12+ | Builder familiarity, Streamlit ecosystem, LLM library support |
| Package manager | uv | 0.6+ | Fast, resolves dependencies reliably, pip-compatible |
| Web/UI | Streamlit | 1.42+ | Python-only, rapid iteration, good enough for internal POC |
| LLM abstraction | LiteLLM | 1.60+ | Provider-agnostic (Anthropic, OpenAI, Bedrock), unified API, cost tracking built-in |
| Agent orchestration | asyncio (stdlib) | 3.12 | Parallel agent execution; no framework overhead |
| Database ORM | SQLAlchemy | 2.0+ | PostgreSQL-compatible dialect; async support; clean model definitions |
| Database engine | SQLite | 3.45+ (stdlib) | Zero-config for POC; schema designed for PostgreSQL migration |
| Prompt templates | Jinja2 | 3.1+ | Mature, well-known, supports template inheritance |
| Config management | PyYAML | 6.0+ | YAML parsing for calibration configs and prompt metadata |
| Data validation | Pydantic | 2.10+ | Agent output validation, schema enforcement, JSON serialization |
| Testing | pytest | 8.3+ | Standard Python testing; async support via pytest-asyncio |
| Testing (async) | pytest-asyncio | 0.24+ | Async test support for orchestrator and agent tests |

### Supporting Libraries

| Component | Library | Version | Rationale |
|-----------|---------|---------|-----------|
| Token counting | tiktoken | 0.9+ | Accurate token counting for budget enforcement (OpenAI models); LiteLLM handles Anthropic counting |
| Date/time | python-dateutil | 2.9+ | Robust date parsing for transcript dates |
| Environment | python-dotenv | 1.0+ | API key management via .env files |
| Logging | structlog | 24.4+ | Structured JSON logging; critical for debugging agent pipelines |
| Cost tracking | LiteLLM callbacks | (built-in) | Per-call cost tracking; aggregated per analysis run |

### Development Tools

| Tool | Purpose |
|------|---------|
| ruff | Linting + formatting (replaces flake8 + black + isort) |
| mypy | Type checking (strict mode) |
| pre-commit | Git hooks for ruff + mypy |

### Explicitly NOT Using

| Library | Reason |
|---------|--------|
| LangChain / LangGraph | Over-abstraction for 10 well-defined agents; adds complexity without value for this use case |
| CrewAI / AutoGen | Multi-agent frameworks add indirection; our orchestrator is ~200 lines of asyncio |
| FastAPI | No HTTP API needed for POC (Streamlit calls Python functions directly); adds unnecessary infra |
| Celery / Redis | Overkill for POC scale (100 deals, minutes-per-analysis acceptable) |
| Alembic | Migration tool — useful post-POC but premature for SQLite phase |

---

## 3. Agent Execution Architecture

### 3.1 Sequential-Parallel Pipeline

```
Timeline (per-account analysis run):
=====================================================================

t=0s     PREPROCESSOR
         - Load up to 5 transcripts for account
         - Speaker normalization, filler removal
         - Enforce 8K token cap per transcript
         - Pack into context dict (total <= 60K tokens)
         ~2-5 seconds

t=5s     STEP 1: Agent 1 (Stage & Progress)
         - Model: claude-3-5-haiku (or gpt-4o-mini)
         - Input: preprocessed transcripts
         - Output: inferred stage, confidence, reasoning
         - Must complete before Step 2 begins
         ~8-15 seconds

t=20s    STEP 2: Agents 2-8 (PARALLEL via asyncio.gather)
         - Model: claude-3-5-haiku (or gpt-4o-mini) for all 7
         - Input: preprocessed transcripts + Agent 1 stage context
         - All 7 fire simultaneously; wall-clock = slowest agent
         - Each agent is an independent async coroutine
         ~10-20 seconds (wall-clock, not cumulative)

t=40s    STEP 3: Agent 9 (Open Discovery / Adversarial)
         - Model: claude-3-5-haiku (or gpt-4o-mini)
         - Input: transcripts + all 8 prior agent outputs
         - Catches gaps + challenges most optimistic finding
         ~10-15 seconds

t=55s    STEP 4: Agent 10 (Synthesis)
         - Model: claude-sonnet-4 (or gpt-4o) — full model
         - Input: all 9 agent outputs (no raw transcripts)
         - Produces: contradiction map, deal memo, structured fields
         ~15-25 seconds

t=80s    OUTPUT VALIDATION
         - Schema validation (Pydantic)
         - Content guardrails (evidence checks, NEVER rules)
         - If FAIL: retry the failing agent (max 2 retries)
         ~1-3 seconds

TOTAL: ~60-120 seconds per account (well within "minutes" budget)
=====================================================================
```

### 3.2 Orchestrator Design

The orchestrator is a single Python module (`sis/orchestrator/pipeline.py`) that manages the entire analysis run. It is not a framework — it is approximately 200-300 lines of focused asyncio code.

```
class AnalysisPipeline:
    """Manages the 4-step agent execution pipeline for one account."""

    async def run(account_id: str) -> AnalysisResult:
        # 1. Load and preprocess transcripts
        # 2. Run Agent 1 (stage inference)
        # 3. Run Agents 2-8 in parallel (asyncio.gather)
        # 4. Run Agent 9 (adversarial, receives all prior outputs)
        # 5. Run Agent 10 (synthesis, receives all 9 outputs)
        # 6. Validate output
        # 7. Persist to database
        # 8. Return result
```

Key design decisions:

- **No agent-to-agent communication except through the orchestrator.** Agents are pure functions: `(transcripts, context) -> AgentOutput`. The orchestrator assembles context for each step.
- **Each agent is a module, not a class hierarchy.** An agent is: a prompt template (YAML/Jinja2), a Pydantic output model, and a thin runner function. No base class inheritance needed.
- **asyncio.gather for parallel execution.** Agents 2-8 are launched as concurrent coroutines. If any agent fails, the others continue (using `return_exceptions=True`). Failed agents get retried independently.

### 3.3 Error Handling and Retries

```
Per-Agent Retry Strategy:
=========================

  Attempt 1: Normal call
      |
      v
  [Success?] --yes--> validate output --> store
      |
      no (LLM error, timeout, rate limit)
      |
      v
  Wait: 2 seconds (exponential backoff base)
      |
  Attempt 2: Same prompt, same model
      |
      v
  [Success?] --yes--> validate output --> store
      |
      no
      |
      v
  Wait: 4 seconds
      |
  Attempt 3: Same prompt, FALLBACK model (e.g., haiku -> sonnet, sonnet -> gpt-4o)
      |
      v
  [Success?] --yes--> validate output --> store
      |
      no
      |
      v
  Mark agent as FAILED for this run.
  Synthesis Agent receives a "agent_X_failed" flag.
  Analysis continues — partial results are better than no results.
```

Error categories and handling:

| Error Type | Handling |
|-----------|----------|
| LLM API timeout (>60s) | Retry with same model |
| LLM rate limit (429) | Retry after backoff (respect Retry-After header) |
| LLM content filter | Log, retry with softened prompt variant |
| Invalid JSON output | Retry (LLM didn't follow schema) |
| Validation failure (NEVER rule) | Retry with appended "reminder" to prompt |
| Preprocessing failure | Abort run, notify user |
| Database write failure | Retry write; if persistent, return result without persistence + alert |

### 3.4 Token Budget Management

```
Budget Allocation (per account analysis run):
=============================================

Total budget ceiling: ~120K tokens input + ~30K tokens output = ~150K total

Preprocessor:
  - 5 transcripts x 8K tokens each = 40K tokens (input to agents)

Agent 1 (Stage):
  - Input:  ~40K (transcripts) + ~1K (system prompt) = 41K
  - Output: ~2K tokens
  - Model:  haiku

Agents 2-8 (each):
  - Input:  ~40K (transcripts) + ~2K (Agent 1 context) + ~1K (system prompt) = 43K
  - Output: ~2K tokens each
  - Model:  haiku
  - Total for Step 2: 7 x 43K input + 7 x 2K output = 301K + 14K
  - (But parallel, so wall-clock cost = 1 agent's time)

Agent 9 (Open Discovery):
  - Input:  ~40K (transcripts) + ~16K (8 agent outputs) + ~1K (system) = 57K
  - Output: ~2K tokens
  - Model:  haiku

Agent 10 (Synthesis):
  - Input:  ~18K (9 agent outputs, NO raw transcripts) + ~2K (system) = 20K
  - Output: ~4K tokens (deal memo + structured fields)
  - Model:  sonnet (full model)

TOTAL TOKENS PER RUN:
  Input:  ~500K tokens across all agents
  Output: ~22K tokens across all agents

ESTIMATED COST PER RUN (Anthropic pricing, Feb 2026):
  Haiku input:   ~480K tokens x $0.80/1M  = $0.38
  Haiku output:  ~18K tokens x $4.00/1M   = $0.07
  Sonnet input:  ~20K tokens x $3.00/1M   = $0.06
  Sonnet output: ~4K tokens x $15.00/1M   = $0.06
  -------------------------------------------------
  TOTAL PER RUN:                            ~$0.57

MONTHLY BUDGET CHECK:
  100 accounts x 1 analysis/week = 400 runs/month
  400 x $0.57 = ~$228/month
  + Conversational queries (~$50/month estimate)
  + Re-runs and retries (~$50/month estimate)
  = ~$328/month (well within $500 ceiling)
```

**Budget enforcement in code:**

The orchestrator tracks cumulative tokens per run. If any agent's input exceeds its allocation by >20%, the run is paused and the preprocessor is asked to further truncate. The cost tracker logs every LLM call to the `analysis_runs` table for monthly budget monitoring.

### 3.5 Cost Optimization Strategy

| Strategy | Implementation |
|----------|---------------|
| Smaller models for Agents 1-9 | Haiku/gpt-4o-mini handles focused single-lens analysis well |
| Full model only for Synthesis | Agent 10 needs the strongest reasoning for contradiction mapping |
| No raw transcripts to Synthesis | Agent 10 reads agent outputs only — saves ~40K tokens per run |
| Preprocessing truncation | 8K token cap per transcript prevents runaway costs |
| Caching (future) | If a transcript hasn't changed, reuse prior agent outputs |
| Batch analysis | Process multiple accounts sequentially to avoid rate limits |

---

## 4. Data Model — SQLAlchemy Schema

The schema below uses SQLAlchemy 2.0 declarative style with type annotations. All types and constraints are PostgreSQL-compatible. SQLite-specific workarounds are noted.

```
TABLE: accounts
=================
  id              TEXT PRIMARY KEY     -- UUID, maps to SF Account ID
  account_name    TEXT NOT NULL
  mrr_estimate    REAL                 -- nullable until known
  ic_forecast_category  TEXT           -- Commit/Best Case/Pipeline/Upside/At Risk/No Decision Risk
                                       -- Entered separately by TL/VP AFTER AI scoring
  team_lead       TEXT
  ae_owner        TEXT
  team_name       TEXT                 -- for team rollup views
  created_at      TEXT NOT NULL        -- ISO 8601 timestamp (TEXT for SQLite compat)
  updated_at      TEXT NOT NULL


TABLE: transcripts
====================
  id              TEXT PRIMARY KEY     -- UUID
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  call_date       TEXT NOT NULL        -- ISO 8601 date
  participants    TEXT                 -- JSON array of participant objects
                                       -- [{name, role, company}]
  duration_minutes  INTEGER
  raw_text        TEXT NOT NULL        -- original uploaded text
  preprocessed_text  TEXT              -- after normalization + truncation
  token_count     INTEGER              -- preprocessed token count
  upload_source   TEXT DEFAULT 'manual'  -- 'manual' for POC
  created_at      TEXT NOT NULL

  INDEX: ix_transcripts_account_date ON (account_id, call_date DESC)
  CONSTRAINT: max 5 transcripts per account (enforced in application layer)


TABLE: analysis_runs
=====================
  id              TEXT PRIMARY KEY     -- UUID
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  started_at      TEXT NOT NULL
  completed_at    TEXT
  status          TEXT NOT NULL        -- pending/running/completed/failed/partial
  trigger         TEXT DEFAULT 'manual'  -- manual/scheduled/rerun
  transcript_ids  TEXT                 -- JSON array of transcript IDs included
  total_input_tokens   INTEGER
  total_output_tokens  INTEGER
  total_cost_usd       REAL
  model_versions  TEXT                 -- JSON: {agent_1: "haiku", agent_10: "sonnet"}
  prompt_config_version  TEXT          -- calibration config version used
  error_log       TEXT                 -- JSON array of errors if any


TABLE: agent_analyses
======================
  id              TEXT PRIMARY KEY     -- UUID
  analysis_run_id TEXT NOT NULL        -- FK -> analysis_runs.id
  account_id      TEXT NOT NULL        -- FK -> accounts.id (denormalized for query speed)
  agent_id        TEXT NOT NULL        -- agent_1_stage, agent_2_relationship, etc.
  agent_name      TEXT NOT NULL        -- human-readable name
  transcript_count_analyzed  INTEGER
  narrative       TEXT NOT NULL        -- 2-4 paragraphs analytical prose
  findings        TEXT                 -- JSON: agent-specific structured data
  evidence        TEXT                 -- JSON array: [{claim_id, transcript_index,
                                       --   speaker, quote, interpretation}]
  confidence_overall  REAL             -- 0.0 to 1.0
  confidence_rationale  TEXT
  data_gaps       TEXT                 -- JSON array of strings
  sparse_data_flag  INTEGER DEFAULT 0  -- boolean (0/1 for SQLite)
  input_tokens    INTEGER
  output_tokens   INTEGER
  cost_usd        REAL
  model_used      TEXT                 -- actual model used (may differ from plan if fallback)
  retries         INTEGER DEFAULT 0
  status          TEXT DEFAULT 'completed'  -- completed/failed/skipped
  created_at      TEXT NOT NULL

  INDEX: ix_agent_analyses_run ON (analysis_run_id)
  INDEX: ix_agent_analyses_account_agent ON (account_id, agent_id, created_at DESC)


TABLE: deal_assessments
========================
  id              TEXT PRIMARY KEY     -- UUID
  analysis_run_id TEXT NOT NULL        -- FK -> analysis_runs.id (1:1)
  account_id      TEXT NOT NULL        -- FK -> accounts.id

  -- Synthesis narrative
  deal_memo       TEXT NOT NULL        -- 3-5 paragraphs
  contradiction_map  TEXT              -- JSON array: [{dimension, agents_agree[],
                                       --   agents_contradict[], resolution, confidence}]
  synthesis_reasoning  TEXT            -- paragraph explaining score derivation

  -- Stage inference
  inferred_stage  INTEGER NOT NULL     -- 1-7
  stage_name      TEXT NOT NULL        -- SQL/Validation/Commercial/Stakeholder/Legal/Integration/Onboarding
  stage_confidence  REAL NOT NULL      -- 0.0-1.0
  stage_reasoning TEXT

  -- Health score (0-100) and breakdown
  health_score    INTEGER NOT NULL
  health_breakdown  TEXT NOT NULL      -- JSON: {economic_buyer: 18, stage: 12,
                                       --   momentum: 14, technical: 8, competitive: 7,
                                       --   stakeholder: 9, commitment: 8, commercial: 9}
                                       -- Components sum to health_score

  -- Confidence interval
  overall_confidence  REAL NOT NULL    -- 0.0-1.0
  confidence_rationale  TEXT
  key_unknowns    TEXT                 -- JSON array of strings

  -- Momentum
  momentum_direction  TEXT NOT NULL    -- Improving/Stable/Declining
  momentum_trend  TEXT                 -- Improving/Stable/Declining/Unknown

  -- Forecast
  ai_forecast_category  TEXT NOT NULL  -- Commit/Best Case/Pipeline/Upside/At Risk/No Decision Risk
  forecast_confidence  REAL
  forecast_rationale  TEXT             -- what would change the category up or down

  -- Signals and actions
  top_positive_signals  TEXT           -- JSON array: [{signal, supporting_agents[], evidence}]
  top_risks       TEXT                 -- JSON array: [{risk, severity, supporting_agents[], evidence}]
  recommended_actions  TEXT            -- JSON array: [{who, what, when, why, priority, owner}]

  -- Divergence (computed post-hoc after IC forecast entered)
  divergence_flag  INTEGER DEFAULT 0   -- boolean
  divergence_explanation  TEXT

  created_at      TEXT NOT NULL

  INDEX: ix_deal_assessments_account ON (account_id, created_at DESC)
  UNIQUE: uq_deal_assessment_run ON (analysis_run_id)  -- one assessment per run


TABLE: score_feedback
======================
  id              TEXT PRIMARY KEY     -- UUID
  account_id      TEXT NOT NULL        -- FK -> accounts.id
  deal_assessment_id  TEXT NOT NULL    -- FK -> deal_assessments.id
  author          TEXT NOT NULL        -- TL name
  feedback_date   TEXT NOT NULL        -- ISO 8601

  health_score_at_time  INTEGER NOT NULL
  disagreement_direction  TEXT NOT NULL  -- too_high / too_low
  reason_category TEXT NOT NULL        -- off_channel / stakeholder_context /
                                       -- stage_mismatch / score_too_high / other
  free_text       TEXT
  off_channel_activity  INTEGER DEFAULT 0  -- boolean

  resolution      TEXT DEFAULT 'pending'  -- pending / accepted / rejected
  resolution_notes  TEXT
  resolved_at     TEXT
  resolved_by     TEXT

  created_at      TEXT NOT NULL

  INDEX: ix_score_feedback_account ON (account_id, created_at DESC)


TABLE: calibration_logs
========================
  id              TEXT PRIMARY KEY     -- UUID
  calibration_date  TEXT NOT NULL
  config_version  TEXT NOT NULL        -- e.g., "v1.2"
  config_previous_version  TEXT
  feedback_items_reviewed  INTEGER
  agent_prompt_changes  TEXT           -- JSON: {agent_id: {before: "", after: ""}}
  config_changes  TEXT                 -- JSON: YAML config diffs
  stage_weight_changes  TEXT           -- JSON: before/after per agent-stage pair
  golden_test_results  TEXT            -- JSON: {test_case_id: pass/fail, regressions: []}
  tl_agreement_rates  TEXT             -- JSON: {agent_id: rate}
  approved_by     TEXT
  created_at      TEXT NOT NULL


TABLE: prompt_versions
=======================
  id              TEXT PRIMARY KEY     -- UUID
  agent_id        TEXT NOT NULL        -- agent_1_stage, etc.
  version         TEXT NOT NULL        -- semantic version e.g., "1.0.0"
  prompt_template TEXT NOT NULL        -- full Jinja2 template content
  calibration_config_version  TEXT     -- which calibration config this was tested with
  change_notes    TEXT
  is_active       INTEGER DEFAULT 1   -- boolean; only one active per agent_id
  created_at      TEXT NOT NULL

  UNIQUE: uq_prompt_version ON (agent_id, version)
  INDEX: ix_prompt_active ON (agent_id, is_active) WHERE is_active = 1


TABLE: chat_sessions
=====================
  id              TEXT PRIMARY KEY     -- UUID
  user_name       TEXT
  started_at      TEXT NOT NULL
  last_message_at TEXT


TABLE: chat_messages
=====================
  id              TEXT PRIMARY KEY     -- UUID
  session_id      TEXT NOT NULL        -- FK -> chat_sessions.id
  role            TEXT NOT NULL        -- user / assistant
  content         TEXT NOT NULL
  tokens_used     INTEGER
  model_used      TEXT
  created_at      TEXT NOT NULL

  INDEX: ix_chat_messages_session ON (session_id, created_at)
```

### PostgreSQL Migration Notes

The schema above deliberately avoids SQLite-specific features. When migrating to PostgreSQL:

| SQLite Pattern | PostgreSQL Replacement |
|---------------|----------------------|
| `TEXT` for timestamps | `TIMESTAMP WITH TIME ZONE` |
| `TEXT` for UUIDs | `UUID` (native type) |
| `TEXT` for JSON columns | `JSONB` (indexed, queryable) |
| `INTEGER` for booleans | `BOOLEAN` |
| `REAL` for money | `NUMERIC(10,2)` |
| Application-layer constraints | Database-level CHECK constraints |
| No concurrent writes | Connection pooling via pgBouncer |

SQLAlchemy's `Column` definitions should use type mapping that auto-switches:

```python
# In sis/db/types.py — conditional type mapping
# Use TypeDecorator for JSON columns that serialize/deserialize automatically
# Use mapped_column with type annotations for SQLAlchemy 2.0 style
```

---

## 5. Agentforce Migration Path

### 5.1 Design Patterns for Portability

The system is designed so that each component maps cleanly to an Agentforce concept:

| SIS Component | Agentforce Equivalent | Migration Strategy |
|--------------|----------------------|-------------------|
| Agent 1-10 (Python functions) | Agent Actions (Apex/Flow) | Each agent's prompt template + output schema becomes an Agent Action. The prompt is the logic; the Python wrapper is disposable. |
| Orchestrator (asyncio pipeline) | Agentforce Topics + Flow orchestration | The sequential-parallel flow becomes a Flow with parallel paths. Topic routing replaces the orchestrator. |
| SQLite tables | Salesforce Custom Objects | Each table maps to a custom object. JSON columns become related lists or rich text fields. |
| Calibration YAML | Custom Metadata Types | Key-value calibration params become Custom Metadata, editable in Setup without code deployment. |
| Prompt templates (Jinja2) | Prompt Template objects | Agentforce has native prompt template management. Variables map to Jinja2 variables. |
| Streamlit dashboard | Salesforce Lightning pages | Custom Lightning Web Components for deal health, pipeline views. |
| Chat interface | Agentforce conversational layer | Native capability — this is Agentforce's core strength. |
| Output validator | Apex validation triggers | Before-save triggers on custom objects enforce schema and NEVER rules. |

### 5.2 Portability Rules (enforced during POC development)

1. **No Python-specific logic in agent prompts.** Prompts are pure text with `{{variable}}` placeholders. They must work identically when called from Apex or any other language.

2. **Agent I/O is JSON, always.** Every agent takes a JSON input and produces a JSON output matching the standardized schema (PRD Section 7.4). No Python objects cross agent boundaries.

3. **Orchestration logic is separate from agent logic.** The orchestrator knows the order (1 -> 2-8 parallel -> 9 -> 10) and passes outputs between steps. Agents never call other agents directly.

4. **Configuration is data, not code.** Calibration values, model assignments, stage-relevance weights — all live in YAML files that could be loaded into Salesforce Custom Metadata.

5. **No state inside agents.** Agents are stateless functions. All state lives in the database. An agent receives everything it needs in its input payload.

### 5.3 Migration Checklist (for Phase 3)

```
Phase 3 Migration Steps:
========================
[ ] Create Custom Objects matching SQLite schema
[ ] Migrate data from SQLite to Salesforce custom objects
[ ] Convert each agent's prompt template to Agentforce Prompt Template
[ ] Create Apex classes for output validation (mirror Python validators)
[ ] Build Flow to replace asyncio orchestrator (parallel paths supported)
[ ] Create Agent Actions wrapping LLM calls with prompt templates
[ ] Build Lightning Web Components for dashboard views
[ ] Configure Agentforce Topics for conversational interface
[ ] Set up Custom Metadata Types for calibration config
[ ] Run golden test set against Agentforce pipeline — compare to Python results
[ ] Parallel-run both systems for 2 weeks before cutover
```

---

## 6. API Design — Internal Service Interfaces

Even though Streamlit calls Python functions directly (no HTTP), clean interfaces are essential for testability, Agentforce migration, and separation of concerns.

### 6.1 Analysis Service

```
analyze_account(account_id: str) -> AnalysisResult
    """Run the full 10-agent pipeline for one account.

    Returns:
        AnalysisResult:
            run_id: str
            status: "completed" | "partial" | "failed"
            deal_assessment: DealAssessment
            agent_outputs: dict[str, AgentOutput]
            validation_warnings: list[str]
            cost: CostSummary
    """

rerun_agent(run_id: str, agent_id: str) -> AgentOutput
    """Re-run a single agent (e.g., after prompt change).
    Does NOT re-run Synthesis — call resynthesize() separately.
    """

resynthesize(run_id: str) -> DealAssessment
    """Re-run Agent 10 (Synthesis) using existing agent outputs from a run.
    Useful after rerunning individual agents or changing calibration.
    """

get_analysis_history(account_id: str) -> list[AnalysisResult]
    """Get all analysis runs for an account, most recent first."""
```

### 6.2 Account Service

```
create_account(name: str, mrr: float | None, team_lead: str,
               ae_owner: str, team: str) -> Account

update_account(account_id: str, **fields) -> Account

set_ic_forecast(account_id: str, category: str) -> DivergenceResult
    """Set the IC forecast category (entered separately, post-scoring).
    Computes divergence against latest AI forecast and returns result.
    """

list_accounts(team: str | None, health_tier: str | None,
              sort_by: str) -> list[AccountSummary]

get_account_detail(account_id: str) -> AccountDetail
    """Full account detail including latest assessment, transcript list,
    feedback history, and analysis history.
    """
```

### 6.3 Transcript Service

```
upload_transcript(account_id: str, raw_text: str, call_date: str,
                  participants: list[Participant] | None,
                  duration_minutes: int | None) -> Transcript
    """Upload and preprocess a transcript. Enforces 5-transcript limit
    (oldest is archived, not deleted, if limit exceeded).
    """

preprocess_transcript(raw_text: str) -> PreprocessedResult
    """Run preprocessing pipeline:
    1. Speaker label normalization -> ROLE_NAME (Company)
    2. Filler word removal
    3. Token counting
    4. Truncation to 8K tokens if needed
    Returns preprocessed text + metadata.
    """

list_transcripts(account_id: str) -> list[Transcript]
    """Transcripts for account, ordered by call_date DESC."""
```

### 6.4 Feedback Service

```
submit_feedback(account_id: str, assessment_id: str,
                author: str, direction: str, reason: str,
                free_text: str | None,
                off_channel: bool) -> ScoreFeedback

list_feedback(account_id: str | None, author: str | None,
              status: str | None) -> list[ScoreFeedback]

resolve_feedback(feedback_id: str, resolution: str,
                 notes: str, resolved_by: str) -> ScoreFeedback
```

### 6.5 Query Service (Conversational Interface)

```
query(session_id: str, user_message: str) -> QueryResponse
    """Process a natural language query about the pipeline.

    The query service:
    1. Classifies intent (deal lookup, pipeline overview, comparison, etc.)
    2. Retrieves relevant data from the database
    3. Constructs a context-rich prompt for the LLM
    4. Returns the LLM's response with source references

    Returns:
        QueryResponse:
            answer: str
            sources: list[SourceReference]  -- accounts/assessments referenced
            follow_up_suggestions: list[str]
    """

new_session(user_name: str) -> str
    """Create a new chat session. Returns session_id."""
```

### 6.6 Dashboard Service

```
get_pipeline_overview(team: str | None) -> PipelineOverview
    """Aggregated pipeline view:
    - Deals grouped by health tier (Healthy 70+, At Risk 45-69, Critical <45)
    - Per-deal: name, MRR, stage, health score, momentum, AI category, IC category
    - Team-level aggregates
    """

get_divergence_report(team: str | None) -> list[DivergenceItem]
    """Deals where AI and IC forecasts differ, sorted by value impact."""

get_forecast_comparison(team: str | None) -> ForecastComparison
    """AI aggregate vs. IC aggregate forecast at team and org level.
    Includes weighted pipeline value under both models.
    """

get_deal_brief(account_id: str) -> DealBrief
    """One-page brief for pipeline review prep:
    - Health score + confidence
    - Momentum direction
    - Top 3 positive signals
    - Top 3 risks
    - 2 inspection questions for the TL
    - Recommended actions
    """

get_feedback_dashboard() -> FeedbackDashboard
    """Aggregated view of all TL feedback for calibration review."""
```

### 6.7 Export Service

```
export_deal_brief(account_id: str, format: str) -> bytes
    """Export deal brief as PDF or Markdown. For pipeline review prep."""

export_forecast_report(team: str | None, format: str) -> bytes
    """Export forecast comparison report. Board-presentable format."""
```

---

## 7. Project Directory Structure

```
sis/
|
|-- pyproject.toml                  # Project metadata, dependencies (uv/pip compatible)
|-- .env.example                    # Template for API keys
|-- .gitignore
|-- README.md
|
|-- config/
|   |-- agents.yml                  # Agent registry: id, name, model assignment, description
|   |-- models.yml                  # Model routing config: agent -> model mapping
|   |-- calibration/
|   |   |-- v1.0.yml                # Calibration config — versioned
|   |   |-- current.yml             # Symlink to active version
|   |-- stage_relevance.yml         # Agent-stage weight matrix (from PRD Section 7.5)
|
|-- prompts/
|   |-- _base.yml.j2               # Shared prompt preamble (anti-sycophancy, output format)
|   |-- agent_01_stage.yml.j2
|   |-- agent_02_relationship.yml.j2
|   |-- agent_03_commercial.yml.j2
|   |-- agent_04_momentum.yml.j2
|   |-- agent_05_technical.yml.j2
|   |-- agent_06_economic_buyer.yml.j2
|   |-- agent_07_msp_next_steps.yml.j2
|   |-- agent_08_competitive.yml.j2
|   |-- agent_09_open_discovery.yml.j2
|   |-- agent_10_synthesis.yml.j2
|   |-- chat_system.yml.j2         # System prompt for conversational interface
|
|-- sis/                            # Main application package
|   |-- __init__.py
|   |
|   |-- agents/                     # One module per agent — stateless functions
|   |   |-- __init__.py
|   |   |-- base.py                 # AgentRunner: loads prompt, calls LLM, validates output
|   |   |-- agent_01_stage.py       # Agent-specific: output model, findings schema
|   |   |-- agent_02_relationship.py
|   |   |-- agent_03_commercial.py
|   |   |-- agent_04_momentum.py
|   |   |-- agent_05_technical.py
|   |   |-- agent_06_economic_buyer.py
|   |   |-- agent_07_msp_next_steps.py
|   |   |-- agent_08_competitive.py
|   |   |-- agent_09_open_discovery.py
|   |   |-- agent_10_synthesis.py
|   |
|   |-- orchestrator/
|   |   |-- __init__.py
|   |   |-- pipeline.py             # AnalysisPipeline: 4-step execution flow
|   |   |-- budget.py               # Token budget tracking and enforcement
|   |   |-- retry.py                # Retry logic with exponential backoff + fallback
|   |   |-- cost_tracker.py         # Per-run cost aggregation
|   |
|   |-- preprocessing/
|   |   |-- __init__.py
|   |   |-- preprocessor.py         # Speaker normalization, filler removal, truncation
|   |   |-- speaker_normalizer.py   # ROLE_NAME (Company) format
|   |   |-- token_counter.py        # Token counting abstraction
|   |
|   |-- validation/
|   |   |-- __init__.py
|   |   |-- output_validator.py     # Schema + content guardrail checks
|   |   |-- schemas.py              # Pydantic models for all agent outputs
|   |   |-- never_rules.py          # NEVER-rule enforcement per agent
|   |
|   |-- services/
|   |   |-- __init__.py
|   |   |-- analysis_service.py     # analyze_account, rerun_agent, resynthesize
|   |   |-- account_service.py      # CRUD + IC forecast + divergence
|   |   |-- transcript_service.py   # Upload, preprocess, manage transcripts
|   |   |-- feedback_service.py     # Score feedback CRUD
|   |   |-- query_service.py        # Conversational interface logic
|   |   |-- dashboard_service.py    # Pipeline overview, deal brief, reports
|   |   |-- export_service.py       # PDF/Markdown export
|   |
|   |-- llm/
|   |   |-- __init__.py
|   |   |-- client.py               # LiteLLM wrapper: model routing, retry, cost tracking
|   |   |-- prompt_loader.py        # Load YAML + render Jinja2 templates
|   |   |-- model_router.py         # Agent -> model mapping from config
|   |
|   |-- db/
|   |   |-- __init__.py
|   |   |-- engine.py               # SQLAlchemy engine setup (SQLite / PostgreSQL)
|   |   |-- models.py               # SQLAlchemy ORM models (all tables)
|   |   |-- session.py              # Session management
|   |   |-- seed.py                 # Initial data seeding (golden test accounts)
|   |
|   |-- ui/
|   |   |-- __init__.py
|   |   |-- app.py                  # Streamlit app entry point + page routing
|   |   |-- pages/
|   |   |   |-- pipeline_overview.py    # Main dashboard
|   |   |   |-- deal_detail.py          # Per-account drill-down
|   |   |   |-- divergence_view.py      # AI vs IC comparison
|   |   |   |-- team_rollup.py          # Team-level aggregates
|   |   |   |-- upload_transcript.py    # Transcript upload + association
|   |   |   |-- run_analysis.py         # Trigger analysis + progress view
|   |   |   |-- feedback.py             # Score feedback form
|   |   |   |-- feedback_dashboard.py   # Aggregated feedback view
|   |   |   |-- chat.py                 # Conversational interface
|   |   |   |-- calibration.py          # Calibration config viewer + log
|   |   |   |-- cost_monitor.py         # LLM cost tracking dashboard
|   |   |-- components/
|   |   |   |-- health_badge.py         # Reusable health score display
|   |   |   |-- momentum_indicator.py   # Improving/Stable/Declining visual
|   |   |   |-- agent_card.py           # Per-agent analysis summary card
|   |   |   |-- evidence_viewer.py      # Expandable evidence quotes
|   |   |   |-- divergence_badge.py     # Forecast alignment indicator
|
|-- tests/
|   |-- __init__.py
|   |-- conftest.py                 # Shared fixtures: test DB, mock LLM, sample transcripts
|   |-- test_preprocessing/
|   |   |-- test_preprocessor.py
|   |   |-- test_speaker_normalizer.py
|   |-- test_agents/
|   |   |-- test_agent_base.py      # Tests for AgentRunner
|   |   |-- test_agent_outputs.py   # Schema validation for each agent's output
|   |-- test_orchestrator/
|   |   |-- test_pipeline.py        # End-to-end pipeline tests (mocked LLM)
|   |   |-- test_retry.py
|   |   |-- test_budget.py
|   |-- test_validation/
|   |   |-- test_output_validator.py
|   |   |-- test_never_rules.py
|   |-- test_services/
|   |   |-- test_analysis_service.py
|   |   |-- test_account_service.py
|   |   |-- test_feedback_service.py
|   |-- test_db/
|   |   |-- test_models.py          # ORM model tests
|   |-- fixtures/
|   |   |-- sample_transcript_1.txt
|   |   |-- sample_transcript_2.txt
|   |   |-- golden_test_set/        # 25 golden test deals
|   |   |   |-- won_clear_01.json
|   |   |   |-- lost_clear_01.json
|   |   |   |-- stalled_01.json
|   |   |   |-- multi_transcript_01.json
|   |   |   |-- single_transcript_01.json
|
|-- scripts/
|   |-- run_golden_tests.py         # Regression testing against golden set
|   |-- seed_db.py                  # Initialize DB with schema + optional seed data
|   |-- cost_report.py              # Generate monthly cost report from DB
|   |-- export_for_migration.py     # Export all data in Agentforce-compatible format
|
|-- docs/
|   |-- architecture.md             # This document
|   |-- prompt_guidelines.md        # How to write/modify agent prompts
|   |-- calibration_guide.md        # How to run calibration cycles
|   |-- deployment.md               # Docker setup, environment config
```

### File Count and Complexity Estimate

| Directory | Files | Complexity |
|-----------|-------|-----------|
| `sis/agents/` | 12 | Medium — each agent is ~100-150 lines (prompt loading + output model) |
| `sis/orchestrator/` | 5 | Medium — pipeline is the core logic (~300 lines) |
| `sis/preprocessing/` | 4 | Low — text processing, well-defined rules |
| `sis/validation/` | 4 | Medium — Pydantic models + rule engine |
| `sis/services/` | 8 | Medium — mostly CRUD + orchestrator calls |
| `sis/llm/` | 4 | Low — thin wrapper around LiteLLM |
| `sis/db/` | 5 | Low — standard SQLAlchemy models |
| `sis/ui/` | 15 | Medium — Streamlit pages, each ~100-200 lines |
| `tests/` | 15+ | Medium — mocked LLM tests, golden test runner |
| **TOTAL** | ~70 | **Manageable for one builder with AI assistance** |

---

## 8. Technical Risks

### Risk 1: LLM Output Consistency (Probability: HIGH, Impact: HIGH)

**Risk:** Agents produce outputs that don't conform to the expected JSON schema, vary wildly between runs on the same transcript, or hallucinate evidence quotes not present in the source text.

**Why it matters:** The entire system depends on structured, reliable agent output. If Agent 3 returns malformed JSON or invents a pricing quote, the Synthesis Agent produces garbage, and TL trust collapses immediately.

**Mitigations:**
- Pydantic models validate every agent output before it enters the pipeline. Malformed output triggers a retry.
- Jinja2 prompt templates include explicit output format examples (few-shot) and XML-structured output blocks.
- The output validator cross-references evidence quotes against the source transcript text (fuzzy match, not exact, to allow for minor LLM reformatting).
- Golden test set regression runs detect drift across model versions.
- Temperature set to 0 for all agent calls (maximize determinism).

**Residual risk:** Even with validation, subtle semantic errors (correct JSON, wrong interpretation) will slip through. This is why TL feedback + calibration exists.

### Risk 2: Prompt Engineering Iteration Velocity (Probability: HIGH, Impact: MEDIUM)

**Risk:** The 10 agent prompts are the product. Getting them right requires dozens of iterations per agent across varied transcript types. The VP Sales (builder) is not a prompt engineer. Slow iteration = delayed POC.

**Why it matters:** The 6-8 week timeline leaves roughly 2-3 weeks for prompt development after infrastructure is built. With 10 agents, that's approximately 2 days per agent for tuning — tight.

**Mitigations:**
- Prompt-as-YAML design means prompts can be edited without touching code. Iteration cycle: edit YAML, re-run one agent, compare output.
- The `rerun_agent()` API allows re-running a single agent without repeating the full pipeline — critical for fast iteration.
- Golden test set provides automated regression detection (does this prompt change break anything?).
- Start with Agent 1 (Stage) and Agent 10 (Synthesis) — they're the critical path. Agents 2-8 can start with simpler prompts and be refined over time.
- Calibration config separates thresholds from prompt logic — TLs can tune weights without prompt editing.

**Residual risk:** Prompt quality may not reach production-grade in 6-8 weeks. Plan for the POC to demonstrate the architecture and workflow, with prompts at "80% good" quality. Calibration cycles post-launch close the gap.

### Risk 3: Transcript Format Variability (Probability: MEDIUM, Impact: HIGH)

**Risk:** Gong transcript exports may vary in format (speaker labels, timestamps, metadata, encoding). The preprocessor may not handle all variations, producing malformed input that degrades agent analysis quality silently (no error, just bad output).

**Why it matters:** Garbage in, garbage out. If the preprocessor fails to correctly identify speakers, agents cannot track stakeholder engagement, champion behavior, or buyer vs. seller signals.

**Mitigations:**
- Obtain 5-10 real Gong transcript samples before writing the preprocessor. This is a P0 blocker (PRD OQ1).
- The preprocessor outputs a `quality_report` (detected speakers, token count, truncation applied, format warnings) that is stored and surfaceable in the UI.
- Speaker normalization uses a flexible regex-based approach with fallback to "UNKNOWN_SPEAKER_N" rather than failing silently.
- Build the preprocessor first and test it thoroughly before building any agents.

**Residual risk:** Edge cases in transcript formatting will surface in production. The quality report makes them visible rather than silent.

### Risk 4: Conversational Interface Quality (Probability: MEDIUM, Impact: MEDIUM)

**Risk:** The chat interface (P0-13, P0-14) requires an LLM to answer arbitrary pipeline questions by querying the database. This is a RAG-like system that must reliably retrieve and synthesize data across accounts. Poor retrieval = wrong answers = eroded trust.

**Why it matters:** The VP Sales explicitly wants to query the system conversationally ("which deals need attention?"). If the chat gives wrong or incomplete answers, the VP won't trust the dashboard either.

**Mitigations:**
- The query service does NOT do vector search / semantic retrieval over raw text. It translates user questions into structured database queries (SQL or ORM calls), retrieves structured data, and then asks the LLM to format a response. This is simpler and more reliable than full RAG.
- Pre-built query patterns for common questions ("deals at risk," "stalled deals," "forecast comparison") ensure the most frequent queries work well.
- The response always includes source references (which accounts/assessments it drew from) so the user can verify.
- Use Sonnet-class model for chat (same as Synthesis) — needs strong reasoning to translate natural language to data queries.

**Residual risk:** Complex multi-hop questions ("which reps have the most deals where AI and IC disagree by more than one category?") may produce incorrect results. Scope the POC chat to well-defined query types and expand iteratively.

### Risk 5: Single-Builder Bus Factor (Probability: HIGH, Impact: CRITICAL)

**Risk:** The VP Sales is building this with AI agent assistance. There is no dev team. If the VP becomes unavailable, or if the system requires debugging beyond the VP's technical depth, the project stalls.

**Why it matters:** The POC has organizational investment (CRO approval, TL commitments, baseline measurements). A stalled POC is worse than no POC — it damages credibility for future AI initiatives.

**Mitigations:**
- Architecture deliberately favors simplicity: SQLite (no database ops), Streamlit (no frontend framework), standard Python (no exotic patterns), well-known libraries only.
- Structured logging (structlog) means debugging is possible by reading log files, not stepping through code.
- Configuration-as-YAML means calibration and prompt changes don't require code changes.
- Docker containerization (post-POC) means the system can be handed to a developer without environment setup struggles.
- This architecture document and the prompt guidelines serve as onboarding material for a future developer.
- The directory structure and clean service interfaces mean a developer can understand the system's boundaries quickly.

**Residual risk:** This is the highest risk. If the VP encounters a fundamental issue (e.g., asyncio deadlock, SQLAlchemy session management bug, Streamlit state management complexity), resolution may require developer assistance. Recommendation: identify one developer who can be on-call for 2-4 hours/week during the POC as a safety net.

---

## Appendix A: Prompt Template Structure

Each agent's prompt is a YAML file with embedded Jinja2 templates. This structure separates metadata from prompt content and allows the calibration config to inject values without editing prompt logic.

```yaml
# prompts/agent_03_commercial.yml.j2
metadata:
  agent_id: agent_3_commercial
  agent_name: "Commercial & Risk"
  version: "1.0.0"
  model_preference: "haiku"  # overridden by config/models.yml

system_prompt: |
  You are the Commercial & Risk analysis agent in a sales intelligence system.
  You analyze enterprise sales call transcripts to assess the commercial state
  of the deal and identify risks.

  {{ include('_base.yml.j2') }}

  <domain_knowledge>
  Riskified sells enterprise fraud prevention. Pricing is MRR-based, tied to
  GMV (Gross Merchandise Value). Typical deal values: $50K-$500K+ MRR.
  Common objections: ROI uncertainty, integration complexity, incumbent
  satisfaction, budget timing.
  </domain_knowledge>

  <never_rules>
  - NEVER output a specific pricing number derived from inference rather than
    explicit transcript statement. If pricing was discussed but no number was
    stated, say "Pricing discussed but specific figures not stated in transcript."
  - NEVER speculate about budget authority unless explicitly stated by a speaker.
  </never_rules>

  <calibration>
  Sparse data threshold: {{ calibration.global.sparse_data_threshold }} transcripts
  Stale signal days: {{ calibration.global.stale_signal_days }}
  </calibration>

user_prompt: |
  <task>
  Analyze the following sales call transcripts for {{ account_name }}.
  Focus exclusively on commercial dynamics and risk signals.
  </task>

  <stage_context>
  Agent 1 (Stage & Progress) inferred this deal is in Stage {{ stage.number }}:
  {{ stage.name }} (confidence: {{ stage.confidence }}).
  Reasoning: {{ stage.reasoning }}
  </stage_context>

  <transcripts>
  {% for transcript in transcripts %}
  <transcript index="{{ loop.index }}" date="{{ transcript.call_date }}">
  {{ transcript.preprocessed_text }}
  </transcript>
  {% endfor %}
  </transcripts>

  <output_format>
  Respond with valid JSON matching this exact schema:
  {
    "agent_id": "agent_3_commercial",
    "deal_id": "{{ deal_id }}",
    "analysis_date": "{{ analysis_date }}",
    "transcript_count_analyzed": {{ transcripts | length }},
    "narrative": "2-4 paragraphs of analytical prose about commercial state and risks",
    "findings": {
      "pricing_discussed": true/false,
      "pricing_status": "agreed/negotiating/not_discussed/mentioned_no_specifics",
      "roi_framing": "landed/presented/not_discussed",
      "active_objections": [...],
      "resolved_objections": [...],
      "budget_signals": "...",
      "commercial_readiness": "Low/Medium/High"
    },
    "evidence": [...],
    "confidence": {
      "overall": 0.0-1.0,
      "rationale": "...",
      "data_gaps": [...]
    },
    "sparse_data_flag": true/false
  }
  </output_format>
```

---

## Appendix B: Streamlit Application Layout

```
Sidebar Navigation:
====================
  [Logo/Title: SIS]
  ---
  Pipeline Overview        (pipeline_overview.py)
  Deal Detail              (deal_detail.py) — selected from overview
  Divergence View          (divergence_view.py)
  Team Rollup              (team_rollup.py)
  ---
  Upload Transcript        (upload_transcript.py)
  Run Analysis             (run_analysis.py)
  ---
  Chat                     (chat.py)
  ---
  Feedback Dashboard       (feedback_dashboard.py)
  Calibration              (calibration.py)
  Cost Monitor             (cost_monitor.py)

Key Streamlit Patterns:
========================
- st.session_state for chat history and selected account context
- st.cache_data for database reads (invalidated on new analysis run)
- st.columns for side-by-side metrics (health score + momentum + forecast)
- st.expander for per-agent detail sections in deal drill-down
- st.progress for analysis pipeline progress (Step 1/4, Step 2/4, etc.)
- st.form for feedback submission (prevents re-run on every widget interaction)
- Multi-page app using Streamlit's built-in pages/ directory convention
```

---

## Appendix C: Development Sequence Recommendation

Given the 6-8 week timeline, here is the recommended build order. Each phase produces something testable.

```
WEEK 1-2: Foundation
=====================
  [x] Project scaffold (directory structure, pyproject.toml, dependencies)
  [x] SQLAlchemy models + SQLite setup (seed.py creates schema)
  [x] LLM client wrapper (LiteLLM integration, cost tracking)
  [x] Prompt loader (YAML + Jinja2 rendering)
  [x] Transcript preprocessor (speaker normalization, truncation)
  [x] Basic Streamlit shell (sidebar nav, upload page)
  MILESTONE: Can upload a transcript, preprocess it, store it, call an LLM

WEEK 3-4: Agent Pipeline
=========================
  [x] Agent base runner (load prompt, call LLM, validate output)
  [x] Agent 1 (Stage) — prompt + output model + tests
  [x] Agent 10 (Synthesis) — prompt + output model + tests
  [x] Orchestrator pipeline (sequential-parallel flow)
  [x] Output validator (schema + NEVER rules)
  [x] Agents 2-8 — prompts + output models (parallel development)
  [x] Agent 9 (Open Discovery)
  MILESTONE: Can run full 10-agent pipeline on a transcript set

WEEK 5-6: Dashboard + Chat
============================
  [x] Pipeline overview page (health scores, grouping, sorting)
  [x] Deal detail page (drill-down, per-agent cards, evidence viewer)
  [x] Divergence view
  [x] Conversational interface (chat page + query service)
  [x] Deal brief export
  [x] Feedback submission form
  MILESTONE: Full end-to-end workflow: upload -> analyze -> view -> chat -> feedback

WEEK 7-8: Calibration + Polish
================================
  [x] Golden test set creation (25 historical deals)
  [x] Regression test runner (scripts/run_golden_tests.py)
  [x] First calibration cycle with TL feedback
  [x] Prompt refinement based on calibration
  [x] Team rollup view
  [x] Forecast comparison report
  [x] Cost monitor page
  [x] Feedback dashboard
  MILESTONE: POC ready for champion TL use
```

---

*Document produced for Riskified SIS POC. Architecture decisions optimized for: builder simplicity, Agentforce portability, cost efficiency, and fast iteration on prompts/calibration.*
