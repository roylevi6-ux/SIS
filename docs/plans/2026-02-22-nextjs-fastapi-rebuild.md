# Next.js + FastAPI Rebuild Implementation Plan (v2 — Dev Lead Revised)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Streamlit POC frontend with a Next.js app backed by a FastAPI REST API, creating a production-grade architecture that maps 1:1 to Salesforce Lightning Web Components (Phase 3).

**Architecture:** FastAPI wraps the existing `sis/services/` layer as REST endpoints. Next.js consumes these endpoints. The Python backend (agents, orchestrator, services, DB) remains unchanged. PostgreSQL replaces SQLite. The entire service interface becomes the portability boundary.

**Tech Stack:**
- **Backend:** Python 3.12, FastAPI + Uvicorn, existing `sis/` package, Pydantic v2 schemas, PostgreSQL (via SQLAlchemy + Alembic)
- **Frontend:** Next.js 14 (App Router), TypeScript (auto-generated from OpenAPI), Tailwind CSS, shadcn/ui, TanStack Query, Recharts
- **Auth:** JWT tokens (prepared for SF SSO in Phase 3)
- **Deployment:** Vercel (frontend) + Railway or Render (backend) + Docker Compose (local dev)

**Dev Lead Review Fixes Incorporated:**
1. PostgreSQL migration moved to Task 1 (was Task 17)
2. Python upgraded to 3.12 (3.9 incompatible with Pydantic v2 / FastAPI)
3. Global error handler + structured error responses
4. Async/sync boundary: sync `def` for routes calling sync services, `run_in_executor` for pipeline
5. Connection pool configuration for PostgreSQL
6. Pydantic schemas audited against actual service return shapes
7. TypeScript types auto-generated from OpenAPI spec (not manual)
8. Alembic added for database migrations
9. Rate limiting on analysis endpoint
10. Dockerfile copy order fixed
11. Docker-compose `NEXT_PUBLIC_API_URL` fixed (uses Vercel rewrite pattern)
12. Frontend testing plan (MSW + Playwright)
13. Chat route uses sync `def` (not `async def`) to avoid blocking event loop

---

## Part 0: Foundation (Day 1)

### Task 0: Python 3.12 Upgrade

**Why:** Python 3.9.6 (current) does not support `float | None` union syntax natively, and FastAPI + Pydantic v2 work best on 3.11+. The codebase already uses 3.10+ syntax via `from __future__ import annotations`.

**Files:**
- Modify: `pyproject.toml` (python requires)
- Recreate: `.venv`

**Step 1: Install Python 3.12**

```bash
brew install python@3.12
```

**Step 2: Recreate virtual environment**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

**Step 3: Verify existing tests still pass**

```bash
pytest tests/ -v --tb=short
```

Expected: 173 tests pass.

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: upgrade Python requirement to 3.12"
```

---

### Task 1: PostgreSQL Migration

**Why (Dev Lead):** "Build on Postgres from day one. Late database migrations always surface surprises — JSON column queries, TEXT timestamps, INTEGER booleans all behave differently."

**Files:**
- Modify: `pyproject.toml` (add psycopg2-binary, alembic)
- Modify: `sis/db/engine.py` (PostgreSQL support + connection pooling)
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/` (initial migration)
- Create: `scripts/migrate_sqlite_to_pg.py`
- Modify: `.env.example`

**Step 1: Install dependencies**

```bash
uv add psycopg2-binary alembic
```

**Step 2: Update engine.py with connection pooling**

```python
# sis/db/engine.py
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/sis.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
```

**Step 3: Initialize Alembic**

```bash
alembic init alembic
```

Configure `alembic/env.py` to use `sis.db.models.Base.metadata` and `DATABASE_URL` from environment.

**Step 4: Generate initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
```

**Step 5: Start local PostgreSQL and test**

```bash
docker run -d --name sis-pg -p 5432:5432 -e POSTGRES_PASSWORD=sis -e POSTGRES_DB=sis postgres:16

DATABASE_URL=postgresql://postgres:sis@localhost:5432/sis alembic upgrade head
DATABASE_URL=postgresql://postgres:sis@localhost:5432/sis pytest tests/ -v --tb=short
```

Expected: All 173 tests pass against PostgreSQL.

**Step 6: Write SQLite-to-PG data migration script**

`scripts/migrate_sqlite_to_pg.py`: Reads all data from SQLite, inserts into PostgreSQL. Handles type coercion (TEXT timestamps, INTEGER booleans, TEXT JSON → JSONB).

**Step 7: Commit**

```bash
git add sis/db/engine.py alembic/ alembic.ini scripts/migrate_sqlite_to_pg.py pyproject.toml .env.example
git commit -m "feat: add PostgreSQL support with Alembic migrations and connection pooling"
```

---

## Part 1: FastAPI Backend Layer

### Task 2: FastAPI Scaffold with Error Handling

**Files:**
- Create: `sis/api/__init__.py`
- Create: `sis/api/main.py`
- Create: `sis/api/deps.py`
- Create: `sis/api/errors.py`
- Modify: `pyproject.toml` (add fastapi, uvicorn, python-multipart, slowapi)
- Create: `tests/test_api/__init__.py`
- Create: `tests/test_api/conftest.py`
- Create: `tests/test_api/test_health.py`

**Step 1: Install FastAPI dependencies**

```bash
uv add fastapi "uvicorn[standard]" python-multipart slowapi
```

**Step 2: Write the global error handler**

```python
# sis/api/errors.py
from fastapi import Request
from fastapi.responses import JSONResponse

class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

**Step 3: Write the FastAPI app entry point**

```python
# sis/api/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sis.api.errors import value_error_handler, api_error_handler, APIError

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI(
    title="SIS API",
    description="Riskified Sales Intelligence System",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(APIError, api_error_handler)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}
```

**Step 4: Write dependency injection module**

```python
# sis/api/deps.py
from sis.db.session import get_session

def get_db():
    with get_session() as session:
        yield session
```

**Step 5: Write test conftest and health test**

```python
# tests/test_api/conftest.py
import pytest
from fastapi.testclient import TestClient
from sis.api.main import app

@pytest.fixture
def client():
    return TestClient(app)
```

```python
# tests/test_api/test_health.py
def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

**Step 6: Run test**

```bash
pytest tests/test_api/test_health.py -v
```

**Step 7: Commit**

```bash
git add sis/api/ tests/test_api/ pyproject.toml
git commit -m "feat: add FastAPI scaffold with global error handling and rate limiting support"
```

---

### Task 3: Schema Audit + Pydantic Response Models

**Why (Dev Lead):** "The actual service functions return dicts with different field names than assumed. Audit every service function's actual return shape before writing schemas."

**Files:**
- Create: `sis/api/schemas/__init__.py`
- Create: `sis/api/schemas/accounts.py`
- Create: `sis/api/schemas/transcripts.py`
- Create: `sis/api/schemas/analyses.py`
- Create: `sis/api/schemas/dashboard.py`
- Create: `sis/api/schemas/feedback.py`
- Create: `sis/api/schemas/admin.py`
- Create: `sis/api/schemas/chat.py`

**Step 1: Audit all 16 service modules**

Read every public function in `sis/services/` and document the exact return shape. Key mismatches to catch:
- `get_account_detail()` returns `"assessment"` not `"latest_assessment"`
- Fields named differently than expected in dashboard/trend services
- JSON columns returned as strings vs parsed dicts

**Step 2: Write Pydantic schemas matching actual return shapes**

Use `model_config = ConfigDict(from_attributes=True)` where needed. Use `Any` for JSON columns that vary by agent rather than `dict` which may fail validation.

Key request schemas:
- `AccountCreate`, `AccountUpdate`, `ICForecastUpdate`
- `TranscriptUpload`
- `AnalysisRequest`
- `FeedbackCreate`, `FeedbackResolve`
- `ChatMessage`
- `CalibrationCreate`, `PromptVersionCreate`, `CoachingCreate`

Key response schemas:
- `AccountSummary`, `AccountDetail`
- `TranscriptResponse`
- `AnalysisRunResponse`, `AgentAnalysisResponse`, `DealAssessmentResponse`
- `PipelineOverviewResponse`, `DivergenceItem`, `TeamRollupResponse`
- `FeedbackResponse`, `FeedbackSummary`
- `ChatResponse`
- All admin response types

**Step 3: Validate schemas import correctly**

```bash
python -c "from sis.api.schemas import accounts, transcripts, analyses, dashboard, feedback, admin, chat; print('All schemas OK')"
```

**Step 4: Commit**

```bash
git add sis/api/schemas/
git commit -m "feat: add Pydantic schemas audited against actual service return shapes"
```

---

### Task 4: Account & Transcript API Routes

**Files:**
- Create: `sis/api/routes/__init__.py`
- Create: `sis/api/routes/accounts.py`
- Create: `sis/api/routes/transcripts.py`
- Modify: `sis/api/main.py` (register routers)
- Create: `tests/test_api/test_accounts.py`
- Create: `tests/test_api/test_transcripts.py`

**Important (Dev Lead):** All routes use sync `def` (not `async def`). FastAPI automatically runs sync handlers in a thread pool, which avoids event loop blocking when services call `asyncio.run()` internally.

**Step 1: Write account routes**

```python
# sis/api/routes/accounts.py
from fastapi import APIRouter, HTTPException
from sis.services import account_service
from sis.api.schemas.accounts import AccountCreate, AccountUpdate, ICForecastUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.get("/")
def list_accounts(sort_by: str = "account_name", filter_team: str | None = None):
    return account_service.list_accounts(sort_by=sort_by, filter_team=filter_team)

@router.get("/{account_id}")
def get_account(account_id: str):
    result = account_service.get_account_detail(account_id)
    if not result:
        raise HTTPException(404, "Account not found")
    return result

@router.post("/")
def create_account(body: AccountCreate):
    return account_service.create_account(
        name=body.name, mrr=body.mrr_estimate,
        team_lead=body.team_lead, ae_owner=body.ae_owner, team=body.team_name,
    )

@router.put("/{account_id}")
def update_account(account_id: str, body: AccountUpdate):
    return account_service.update_account(account_id, **body.model_dump(exclude_none=True))

@router.post("/{account_id}/ic-forecast")
def set_ic_forecast(account_id: str, body: ICForecastUpdate):
    return account_service.set_ic_forecast(account_id, body.category)
```

**Step 2: Write transcript routes** (same sync `def` pattern)

**Step 3: Register routers in main.py**

**Step 4: Write tests**

**Step 5: Run tests**

```bash
pytest tests/test_api/ -v
```

**Step 6: Commit**

```bash
git add sis/api/routes/ tests/test_api/
git commit -m "feat: add account and transcript REST API routes"
```

---

### Task 5: Analysis & Dashboard API Routes

**Files:**
- Create: `sis/api/routes/analyses.py`
- Create: `sis/api/routes/dashboard.py`
- Modify: `sis/api/main.py`
- Create: `tests/test_api/test_analyses.py`
- Create: `tests/test_api/test_dashboard.py`

**Critical (Dev Lead):** The analysis pipeline runs 60-120 seconds. `BackgroundTasks` alone is insufficient — use `run_in_executor` with a `ThreadPoolExecutor` to avoid blocking the event loop.

**Step 1: Write analysis routes with thread pool execution**

```python
# sis/api/routes/analyses.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from uuid import uuid4

router = APIRouter(prefix="/api/analyses", tags=["analyses"])
executor = ThreadPoolExecutor(max_workers=4)

@router.post("/")
async def run_analysis(body: AnalysisRequest):
    """Starts pipeline in thread pool, returns run_id immediately for SSE polling."""
    run_id = str(uuid4())
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, _run_pipeline_sync, body.account_id, run_id)
    return {"run_id": run_id, "status": "started"}

# Rate limiting: 1 analysis per account per minute
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.get("/history/{account_id}")
def get_history(account_id: str):
    return analysis_service.get_analysis_history(account_id)

@router.get("/{run_id}/agents")
def get_agents(run_id: str):
    return analysis_service.get_agent_analyses(run_id)

@router.get("/{run_id}/status")
def get_status(run_id: str):
    # Poll analysis_runs table for current status
    ...

# rerun_agent and resynthesize use sync def (services call asyncio.run internally)
@router.post("/{run_id}/rerun/{agent_id}")
def rerun_agent(run_id: str, agent_id: str):
    return analysis_service.rerun_agent(run_id, agent_id)

@router.post("/{run_id}/resynthesize")
def resynthesize(run_id: str):
    return analysis_service.resynthesize(run_id)
```

**Step 2: Write dashboard routes** (all sync `def`, straightforward wrappers)

**Step 3: Write tests**

**Step 4: Commit**

```bash
git add sis/api/routes/ tests/test_api/
git commit -m "feat: add analysis routes with thread pool execution and dashboard routes"
```

---

### Task 6: Feedback, Calibration & Admin API Routes

**Files:**
- Create: `sis/api/routes/feedback.py`
- Create: `sis/api/routes/calibration.py`
- Create: `sis/api/routes/admin.py`
- Create: `sis/api/routes/export.py`
- Modify: `sis/api/main.py`

All routes follow the established sync `def` pattern. Wraps all remaining services:

- **Feedback:** 4 endpoints (submit, list, resolve, summary)
- **Calibration:** 4 endpoints (current, patterns, create, history)
- **Admin:** usage tracking (3), action logs (3), prompt versions (5), coaching (5), trends (3), scorecard (1), forecast (2)
- **Export:** 2 endpoints (deal brief, forecast report)
- **Golden tests, digest, seeding:** stub endpoints returning `501 Not Implemented` (to be filled in later — Dev Lead flagged these as TBD)

**Commit:**

```bash
git add sis/api/routes/
git commit -m "feat: add feedback, calibration, admin, and export API routes"
```

---

### Task 7: Chat/Query Route + SSE + OpenAPI Spec

**Files:**
- Create: `sis/api/routes/chat.py`
- Create: `sis/api/routes/sse.py`
- Modify: `sis/api/main.py`

**Critical (Dev Lead):** Chat route MUST use sync `def` (not `async def`). The query service uses `client.messages.stream()` which blocks. FastAPI auto-runs sync handlers in a thread pool.

**Step 1: Write chat route (sync def)**

```python
# sis/api/routes/chat.py
@router.post("/query")
def query(body: ChatMessage):  # sync def — NOT async def
    result = query_service.query(body.message, body.history or [])
    return result
```

**Step 2: Write SSE endpoint for pipeline progress**

```python
# sis/api/routes/sse.py
@router.get("/analysis/{run_id}")
async def analysis_progress(run_id: str):
    async def event_stream():
        while True:
            status = _get_run_status(run_id)  # DB read, fast
            yield f"data: {json.dumps(status)}\n\n"
            if status["status"] in ("completed", "failed", "partial"):
                break
            await asyncio.sleep(2)
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Step 3: Generate OpenAPI spec**

```bash
python -c "
from sis.api.main import app
import json
spec = app.openapi()
with open('docs/openapi.json', 'w') as f:
    json.dump(spec, f, indent=2)
print(f'Generated {len(spec[\"paths\"])} endpoints')
"
```

**Step 4: Commit**

```bash
git add sis/api/ docs/openapi.json
git commit -m "feat: complete FastAPI layer — chat, SSE, OpenAPI spec (~53 endpoints)"
```

---

## Part 2: Next.js Frontend

### Task 8: Next.js Project Scaffold

**Files:**
- Create: `frontend/` directory with full Next.js app
- Create: `frontend/.env.local`

**Step 1: Initialize Next.js project**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

**Step 2: Install dependencies**

```bash
cd frontend
npm install @tanstack/react-query recharts lucide-react clsx tailwind-merge
npx shadcn@latest init
npx shadcn@latest add button card badge table tabs dialog input textarea select separator dropdown-menu tooltip sheet collapsible
```

**Step 3: Configure environment**

```
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Step 4: Configure Tailwind theme** (SIS brand: emerald-600 primary, health tier colors)

**Step 5: Verify dev server starts**

```bash
npm run dev
```

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Next.js project with Tailwind, shadcn/ui, TanStack Query"
```

---

### Task 9: Auto-Generated TypeScript Types + API Client + Hooks

**Why (Dev Lead):** "Manually maintaining TypeScript types that mirror Pydantic schemas is a maintenance burden. Auto-generate from OpenAPI spec."

**Files:**
- Create: `frontend/src/lib/types.ts` (auto-generated)
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/hooks/use-accounts.ts`
- Create: `frontend/src/lib/hooks/use-analyses.ts`
- Create: `frontend/src/lib/hooks/use-dashboard.ts`
- Create: `frontend/src/lib/hooks/use-feedback.ts`
- Create: `frontend/src/lib/hooks/use-chat.ts`
- Create: `frontend/src/lib/hooks/use-admin.ts`

**Step 1: Install openapi-typescript**

```bash
cd frontend
npm install -D openapi-typescript
```

**Step 2: Generate types from OpenAPI spec**

```bash
npx openapi-typescript ../docs/openapi.json -o src/lib/types.ts
```

Add to `package.json` scripts:
```json
"generate-types": "openapi-typescript ../docs/openapi.json -o src/lib/types.ts"
```

**Step 3: Write typed API client** (using generated types)

**Step 4: Write TanStack Query hooks** for all domains (accounts, analyses, dashboard, feedback, chat, admin, etc.)

**Step 5: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add auto-generated TypeScript types, API client, and TanStack Query hooks"
```

---

### Task 10: Layout Shell + Navigation Sidebar

**Files:**
- Create: `frontend/src/components/sidebar.tsx`
- Create: `frontend/src/components/providers.tsx`
- Modify: `frontend/src/app/layout.tsx`

3 navigation groups (Analytics 6 items, Actions 4 items, Admin 9 items) matching current Streamlit sidebar. Active route highlighting, collapsible groups, responsive mobile sheet.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add sidebar navigation and layout shell"
```

---

### Task 11: Pipeline Overview Page (Primary Dashboard) **[Dev Lead Review]**

**Files:**
- Create: `frontend/src/app/pipeline/page.tsx`
- Create: `frontend/src/components/health-badge.tsx`
- Create: `frontend/src/components/momentum-indicator.tsx`
- Create: `frontend/src/components/forecast-badge.tsx`
- Create: `frontend/src/components/deal-table.tsx`

**This is the most important page.** Dev Lead requested manual review.

Maps to `sis/ui/pages/pipeline_overview.py`. Shows all deals grouped by health tier (Healthy 70+, At Risk 45-69, Critical <45) with sortable columns: name, MRR, stage, health score, momentum, AI forecast, IC forecast, days since last call.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add pipeline overview page with health badges and deal table"
```

---

### Task 12: Deal Detail Page (Drill-Down) **[Dev Lead Review]**

**Files:**
- Create: `frontend/src/app/deals/[id]/page.tsx`
- Create: `frontend/src/components/agent-card.tsx`
- Create: `frontend/src/components/evidence-viewer.tsx`
- Create: `frontend/src/components/health-breakdown.tsx`
- Create: `frontend/src/components/deal-memo.tsx`
- Create: `frontend/src/components/actions-list.tsx`

Maps to `sis/ui/pages/deal_detail.py`. Synthesis-first layout:
1. Header: name, health badge, momentum, forecast
2. Deal memo (tabbed: TL insider / leadership briefing)
3. Health breakdown (8-component Recharts bar chart)
4. Recommended actions (with carry-forward flags)
5. Risk signals + positive signals
6. Per-agent analysis (collapsible cards with evidence)
7. Analysis history timeline
8. Score feedback button

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add deal detail page with agent cards, evidence viewer, health breakdown"
```

---

### Task 13: Upload Transcript + Run Analysis Pages **[Dev Lead Review — SSE]**

**Files:**
- Create: `frontend/src/app/upload/page.tsx`
- Create: `frontend/src/app/analyze/page.tsx`
- Create: `frontend/src/components/analysis-progress.tsx`

Upload: Account selector + textarea + metadata + submit.
Analysis: Account selector + "Run" button + SSE progress (Step 1/4 → 4/4) + link to deal detail on complete.

SSE progress component connects to `GET /api/sse/analysis/{run_id}`.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add upload transcript and run analysis pages with SSE progress"
```

---

### Task 14: Chat Interface

**Files:**
- Create: `frontend/src/app/chat/page.tsx`
- Create: `frontend/src/components/chat-message.tsx`
- Create: `frontend/src/components/chat-input.tsx`

Maps to `sis/ui/pages/chat.py`. Message list + input + source references + suggested queries.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add conversational chat interface"
```

---

### Task 15: Divergence, Team Rollup & Forecast Pages

**Files:**
- Create: `frontend/src/app/divergence/page.tsx`
- Create: `frontend/src/app/team-rollup/page.tsx`
- Create: `frontend/src/app/forecast/page.tsx`
- Create: `frontend/src/components/divergence-badge.tsx`

Divergence: "Forecast Alignment Check" framing, sorted by value impact.
Team Rollup: Per-team aggregates, Recharts stacked bar.
Forecast: AI vs IC aggregate, Recharts grouped bar.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add divergence, team rollup, and forecast comparison pages"
```

---

### Task 16: Remaining Analytics Pages

**Files:**
- Create: `frontend/src/app/rep-scorecard/page.tsx`
- Create: `frontend/src/app/trends/page.tsx`
- Create: `frontend/src/app/deals/[id]/brief/page.tsx`
- Create: `frontend/src/app/meeting-prep/page.tsx`

Rep Scorecard: 4 behavioral dimensions, radar chart.
Trends: Line charts for deal/team health over time.
Deal Brief: 3 format variants + export.
Meeting Prep: Pre-call brief with topics, questions, risks.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add rep scorecard, trends, deal brief, and meeting prep pages"
```

---

### Task 17: Admin Pages (9 pages)

**Files:**
- Create: `frontend/src/app/feedback/page.tsx`
- Create: `frontend/src/app/calibration/page.tsx`
- Create: `frontend/src/app/prompts/page.tsx`
- Create: `frontend/src/app/costs/page.tsx`
- Create: `frontend/src/app/usage/page.tsx`
- Create: `frontend/src/app/activity-log/page.tsx`
- Create: `frontend/src/app/golden-tests/page.tsx`
- Create: `frontend/src/app/digest/page.tsx`
- Create: `frontend/src/app/seeding/page.tsx`

Each page: data table/cards with filters, action buttons where applicable. Maps 1:1 to existing Streamlit admin pages.

**Commit:**

```bash
git add frontend/src/
git commit -m "feat: add all admin pages (feedback, calibration, prompts, costs, usage, etc.)"
```

---

## Part 3: Infrastructure & QA

### Task 18: Authentication Layer

**Files:**
- Create: `sis/api/auth.py`
- Create: `sis/api/routes/auth.py`
- Modify: `sis/api/deps.py`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/components/auth-provider.tsx`

JWT tokens with `python-jose`. Simple username + role login for POC (no password). Auth context in frontend. Protected routes via FastAPI dependency.

**Commit:**

```bash
git add sis/api/auth.py sis/api/routes/auth.py frontend/src/
git commit -m "feat: add JWT authentication layer (prepared for SF SSO)"
```

---

### Task 19: Deployment Configuration **[Dev Lead Review]**

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `frontend/Dockerfile`
- Create: `Procfile`
- Create: `.env.example` (complete)

**Dockerfile (Dev Lead fix: correct copy order):**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY sis/ sis/
COPY config/ config/
COPY prompts/ prompts/
RUN pip install uv && uv pip install --system .
EXPOSE 8000
CMD ["uvicorn", "sis.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**docker-compose.yml (Dev Lead fix: NEXT_PUBLIC_API_URL):**

Frontend uses Vercel rewrite pattern in production. For local dev, API calls go to `http://localhost:8000` directly (port exposed from docker-compose). `NEXT_PUBLIC_API_URL=http://localhost:8000`.

**Procfile:**

```
web: uvicorn sis.api.main:app --host 0.0.0.0 --port $PORT --workers 4
```

**.env.example (complete):**

```
DATABASE_URL=postgresql://postgres:sis@localhost:5432/sis
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET=change-me-in-production
CORS_ORIGINS=http://localhost:3000
```

**Commit:**

```bash
git add Dockerfile docker-compose.yml Procfile .env.example frontend/Dockerfile
git commit -m "feat: add Docker, docker-compose, and deployment configuration"
```

---

### Task 20: Frontend Testing Setup

**Why (Dev Lead):** "21 pages with zero testing plan. At minimum, critical paths need tests."

**Files:**
- Create: `frontend/src/__tests__/setup.ts`
- Create: `frontend/src/__tests__/mocks/handlers.ts` (MSW)
- Create: `frontend/src/__tests__/pipeline-overview.test.tsx`
- Create: `frontend/src/__tests__/deal-detail.test.tsx`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/critical-flow.spec.ts`

**Step 1: Install testing dependencies**

```bash
cd frontend
npm install -D @testing-library/react @testing-library/jest-dom vitest msw @playwright/test
```

**Step 2: Write MSW handlers** mocking the API for component tests.

**Step 3: Write component tests** for Pipeline Overview and Deal Detail (the two most important pages).

**Step 4: Write Playwright E2E smoke test** for the critical flow: upload → analyze → view results.

**Step 5: Commit**

```bash
git add frontend/src/__tests__/ frontend/e2e/ frontend/playwright.config.ts
git commit -m "feat: add frontend testing setup (MSW mocks, component tests, Playwright E2E)"
```

---

### Task 21: End-to-End Verification

**Step 1: Start full stack**

```bash
docker compose up --build
```

**Step 2: Run backend tests against PostgreSQL**

```bash
DATABASE_URL=postgresql://postgres:sis@localhost:5432/sis pytest tests/ -v
```

**Step 3: Run API tests**

```bash
pytest tests/test_api/ -v
```

**Step 4: Run frontend tests**

```bash
cd frontend && npm test
```

**Step 5: Run Playwright E2E**

```bash
cd frontend && npx playwright test
```

**Step 6: Manual walkthrough of all 21 pages**

**Step 7: Fix any issues discovered**

**Step 8: Final commit**

```bash
git add .
git commit -m "feat: complete Next.js + FastAPI rebuild — verified end-to-end"
```

---

### Task 22: QA Lead Review

Invoke `qa-lead` agent to perform comprehensive quality review:
- Feature parity against original Streamlit pages
- API contract consistency (Pydantic schemas vs actual responses)
- Security review (auth, CORS, input validation)
- Performance baseline (API response times, frontend bundle size)
- Accessibility check (WCAG AA on key pages)

---

## Appendix A: Streamlit Page -> Next.js Page Mapping

| # | Streamlit Page | Next.js Route | Primary API Endpoint |
|---|---------------|--------------|---------------------|
| 1 | `pipeline_overview.py` | `/pipeline` | `GET /api/dashboard/pipeline` |
| 2 | `deal_detail.py` | `/deals/[id]` | `GET /api/accounts/{id}` |
| 3 | `deal_brief.py` | `/deals/[id]/brief` | `GET /api/export/brief/{id}` |
| 4 | `divergence_view.py` | `/divergence` | `GET /api/dashboard/divergence` |
| 5 | `team_rollup.py` | `/team-rollup` | `GET /api/dashboard/team-rollup` |
| 6 | `forecast_comparison.py` | `/forecast` | `GET /api/forecast/data` |
| 7 | `rep_scorecard.py` | `/rep-scorecard` | `GET /api/scorecard/reps` |
| 8 | `trend_analysis.py` | `/trends` | `GET /api/trends/*` |
| 9 | `upload_transcript.py` | `/upload` | `POST /api/transcripts` |
| 10 | `run_analysis.py` | `/analyze` | `POST /api/analyses` + SSE |
| 11 | `meeting_prep.py` | `/meeting-prep` | `GET /api/accounts/{id}` |
| 12 | `chat.py` | `/chat` | `POST /api/chat/query` |
| 13 | `feedback_dashboard.py` | `/feedback` | `GET/PATCH /api/feedback` |
| 14 | `calibration.py` | `/calibration` | `GET/POST /api/calibration` |
| 15 | `prompt_versions.py` | `/prompts` | `GET/POST /api/prompts/versions` |
| 16 | `cost_monitor.py` | `/costs` | `GET /api/tracking/summary` |
| 17 | `usage_dashboard.py` | `/usage` | `GET /api/tracking/cro-metrics` |
| 18 | `activity_log.py` | `/activity-log` | `GET /api/logs/actions` |
| 19 | `golden_tests.py` | `/golden-tests` | `GET/POST /api/golden-tests` |
| 20 | `daily_digest.py` | `/digest` | `GET/POST /api/digest/config` |
| 21 | `retrospective_seeding.py` | `/seeding` | `POST /api/seeding/run` |

## Appendix B: Revised Build Sequence

| Phase | Week | Tasks | Review Type |
|-------|------|-------|-------------|
| **Foundation** | 1 | T0 (Python 3.12) + T1 (PostgreSQL) + T2 (FastAPI scaffold) | Dev Lead manual |
| **API Layer** | 1-2 | T3 (schemas) + T4-T7 (all routes + OpenAPI) | Dev Lead reviews T4; T5-T7 subagent |
| **Next.js Core** | 2-3 | T8-T10 (scaffold, types, layout) + T11-T12 (Pipeline, Deal Detail) | Dev Lead reviews T11, T12 |
| **Next.js Pages** | 3-4 | T13-T17 (Chat, Divergence, Analytics, Admin — 17 pages) | Subagent-driven |
| **Infrastructure** | 4-5 | T18 (Auth) + T19 (Deploy) + T20 (Frontend tests) | Dev Lead reviews T19 |
| **Verification** | 5 | T21 (E2E verify) + T22 (QA Lead review) | QA Lead |

**Estimated total: ~5 weeks with AI assistance.**

## Appendix C: What Stays Unchanged

| Module | Files | Reason |
|--------|-------|--------|
| `sis/agents/` | 12 | Agent logic is backend-only |
| `sis/orchestrator/` | 5 | Pipeline execution unchanged |
| `sis/preprocessing/` | 4 | Text processing unchanged |
| `sis/validation/` | 4 | Output validation unchanged |
| `sis/services/` | 16 | Services ARE the API — FastAPI wraps them |
| `sis/llm/` | 4 | LLM client unchanged |
| `sis/db/models.py` | 1 | Schema unchanged (Alembic manages PG) |
| `prompts/` | 11 | Prompt templates unchanged |
| `config/` | YAML | Configuration unchanged |
| `tests/` | existing | Existing 173 tests still pass |

**Only `sis/ui/` becomes obsolete** — replaced by `frontend/`.

## Appendix D: Execution Approach (Hybrid)

**Manual review (Dev Lead):** Tasks 0-4, 11, 12, 13 (SSE), 19
**Subagent-driven:** Tasks 5-7, 8-10, 14-18, 20
**QA Lead review:** Task 22 (post-build)

This gives speed for the mechanical 60% and safety for the integration-critical 40%.
