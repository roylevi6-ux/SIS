# Automated Gong Sync — Implementation Plan

**Date:** 2026-03-12
**Design Doc:** `docs/plans/2026-03-12-automated-gong-sync-design.md`
**Estimated Effort:** 5-7 working sessions
**Dependencies:** None (builds on existing gdrive_service, transcript_service, SSE patterns)

---

## Implementation Sequence

The work is organized into 7 phases. Each phase produces a working increment that can be tested independently. Phases must be done in order because later phases depend on earlier ones.

---

## Phase 1: Database Schema + Models (backend-developer)

**Product impact:** No user-visible changes yet. Lays the foundation for all subsequent work.

### Task 1.1: Add `has_new_calls` column to `accounts`

**File:** `sis/db/models.py`

Add to the `Account` model:
```python
has_new_calls = Column(Integer, default=0)  # boolean: 1=new calls since last analysis
```

**File:** New Alembic migration

```bash
alembic revision --autogenerate -m "add_has_new_calls_to_accounts"
```

The migration should:
- `ALTER TABLE accounts ADD COLUMN has_new_calls INTEGER DEFAULT 0`

### Task 1.2: Create `WatchlistAccount` model

**File:** `sis/db/models.py`

```python
class WatchlistAccount(Base):
    __tablename__ = "watchlist_accounts"

    id = Column(Text, primary_key=True, default=_uuid)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    sf_account_name = Column(Text, nullable=False)
    added_by = Column(Text, ForeignKey("users.id"), nullable=True)
    added_at = Column(Text, nullable=False, default=_now)

    # Relationships
    account = relationship("Account")

    __table_args__ = (
        UniqueConstraint("account_id", name="uq_watchlist_account"),
        Index("ix_watchlist_account", "account_id"),
    )
```

### Task 1.3: Create `SyncJob` model

**File:** `sis/db/models.py`

```python
class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(Text, primary_key=True, default=_uuid)
    status = Column(Text, nullable=False, default="pending")
    triggered_by = Column(Text, ForeignKey("users.id"), nullable=True)
    started_at = Column(Text, nullable=False, default=_now)
    completed_at = Column(Text, nullable=True)

    total_accounts = Column(Integer, nullable=False, default=0)
    n8n_calls_made = Column(Integer, default=0)
    n8n_calls_succeeded = Column(Integer, default=0)
    n8n_calls_failed = Column(Integer, default=0)
    new_calls_found = Column(Integer, default=0)
    calls_imported = Column(Integer, default=0)
    calls_skipped = Column(Integer, default=0)

    n8n_phase_seconds = Column(Float, nullable=True)
    scan_phase_seconds = Column(Float, nullable=True)
    total_seconds = Column(Float, nullable=True)

    error_log = Column(Text, nullable=True)  # JSON array
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    account_results = relationship("SyncAccountResult", back_populates="sync_job")

    __table_args__ = (
        Index("ix_sync_jobs_status", "status", "started_at"),
    )
```

### Task 1.4: Create `SyncAccountResult` model

**File:** `sis/db/models.py`

```python
class SyncAccountResult(Base):
    __tablename__ = "sync_account_results"

    id = Column(Text, primary_key=True, default=_uuid)
    sync_job_id = Column(Text, ForeignKey("sync_jobs.id"), nullable=False)
    account_id = Column(Text, ForeignKey("accounts.id"), nullable=False)
    account_name = Column(Text, nullable=False)

    # N8N phase
    n8n_status = Column(Text, default="pending")
    n8n_calls_found = Column(Integer, nullable=True)
    n8n_calls_processed = Column(Integer, nullable=True)
    n8n_files_created = Column(Integer, nullable=True)
    n8n_response = Column(Text, nullable=True)  # Raw JSON
    n8n_error = Column(Text, nullable=True)
    n8n_duration_seconds = Column(Float, nullable=True)

    # Import phase
    import_status = Column(Text, default="pending")
    new_files_found = Column(Integer, default=0)
    calls_imported = Column(Integer, default=0)
    calls_skipped = Column(Integer, default=0)
    import_error = Column(Text, nullable=True)

    has_new_data = Column(Integer, default=0)  # boolean
    created_at = Column(Text, nullable=False, default=_now)

    # Relationships
    sync_job = relationship("SyncJob", back_populates="account_results")

    __table_args__ = (
        Index("ix_sync_results_job", "sync_job_id"),
        Index("ix_sync_results_account", "account_id"),
    )
```

### Task 1.5: Create `TamAccount` model

**File:** `sis/db/models.py`

```python
class TamAccount(Base):
    __tablename__ = "tam_accounts"

    id = Column(Text, primary_key=True, default=_uuid)
    account_name = Column(Text, nullable=False, unique=True)
    uploaded_at = Column(Text, nullable=False, default=_now)
```

Lightweight reference table for TAM list SF name suggestions.

### Task 1.6: Generate Alembic migration

Single migration for all 4 new tables + 1 new column:

```bash
alembic revision --autogenerate -m "add_watchlist_sync_tables_and_has_new_calls"
```

Verify the generated migration includes:
- `watchlist_accounts` table creation
- `sync_jobs` table creation
- `sync_account_results` table creation
- `tam_accounts` table creation
- `accounts.has_new_calls` column addition
- All indexes and constraints

Run `alembic upgrade head` and verify with a quick DB inspection.

### Task 1.7: Update `list_accounts` to include `has_new_calls`

**File:** `sis/services/account_service.py`

In the `list_accounts()` function, add `has_new_calls` to the summary dict:
```python
summary["has_new_calls"] = bool(acct.has_new_calls)
```

Also add it to `get_account_detail()`.

### Verification:
- [ ] `alembic upgrade head` succeeds
- [ ] New tables exist in SQLite DB
- [ ] `has_new_calls` column on accounts table
- [ ] Existing tests still pass

---

## Phase 2: Config + N8N Client Service (backend-developer)

**Product impact:** Still no user-visible changes. Builds the HTTP client that talks to N8N.

### Task 2.1: Add N8N configuration to `config.py`

**File:** `sis/config.py`

```python
# --- N8N / Gong Sync Integration ---
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://api-n8n.ai.riskxint.com/9qahgM9cMOVNdnTX4MrCQgVXbnoupuw2/webhook/gong-extractor"
)
N8N_REQUEST_TIMEOUT = int(os.getenv("N8N_REQUEST_TIMEOUT", "300"))          # 5 min
N8N_INTER_REQUEST_DELAY = int(os.getenv("N8N_INTER_REQUEST_DELAY", "15"))   # 15s between calls
N8N_DRIVE_POLL_INTERVAL = int(os.getenv("N8N_DRIVE_POLL_INTERVAL", "10"))   # 10s between Drive checks
N8N_DRIVE_POLL_MAX_WAIT = int(os.getenv("N8N_DRIVE_POLL_MAX_WAIT", "180")) # 3 min max wait
N8N_DRIVE_STABILITY_CHECKS = int(os.getenv("N8N_DRIVE_STABILITY_CHECKS", "2"))  # 2 stable checks = synced
N8N_DEFAULT_START_DATE = os.getenv("N8N_DEFAULT_START_DATE", "2025-01-01")
```

### Task 2.2: Create N8N client service

**File:** `sis/services/n8n_client.py` (new file)

Responsibilities:
- Single function `extract_gong_calls(account_name, start_date, end_date=None) -> N8NExtractResponse`
- Uses `httpx` (already in the project for async HTTP) with `timeout=N8N_REQUEST_TIMEOUT`
- Classifies response per the design doc Section 5.2 table
- Catches `httpx.TimeoutException` and returns `success=False, error="timed_out"`
- Catches `httpx.HTTPStatusError` and classifies 4xx vs 5xx
- Logs all responses at INFO level (success) or WARNING level (errors)
- **Does NOT retry** — that's the orchestrator's job

Data models (in same file, or `sis/services/n8n_models.py` if preferred):

```python
@dataclass
class N8NExtractResponse:
    success: bool
    total_calls_found: int
    calls_processed: int
    files_created: int
    google_drive_folder: str
    raw_response: dict
    error: str | None
    duration_seconds: float
    status_code: int | None  # HTTP status code, None if timeout
```

Key implementation details:
- Use `httpx.AsyncClient` since the orchestrator is async
- The POST body is `{"accountName": name, "startDate": start, "endDate": end}`
- Response parsing: safely navigate `results.totalCallsFound` etc. (N8N responses can have unexpected shapes)
- Always return a valid `N8NExtractResponse`, never raise exceptions to the caller

### Task 2.3: Write unit tests for N8N client

**File:** `tests/test_n8n_client.py` (new file)

Test cases:
- Successful response with calls found
- Successful response with 0 calls (no error)
- Response says `success: false` (classified correctly)
- 4xx error response
- 5xx error response
- Timeout
- Malformed JSON response (graceful handling)
- Missing fields in response body

Use `httpx` mock or `respx` library.

### Verification:
- [ ] All N8N client tests pass
- [ ] Config values readable from env/defaults
- [ ] No import errors when loading the new module

---

## Phase 3: Watchlist Service + API (backend-developer)

**Product impact:** Backend CRUD for the watchlist. Not yet visible to users, but testable via API.

### Task 3.1: Create watchlist service

**File:** `sis/services/watchlist_service.py` (new file)

Functions:
```python
def list_watched_accounts() -> list[dict]:
    """List all watched accounts with enriched data.

    Joins watchlist_accounts -> accounts -> latest DealAssessment.
    Adds: has_new_calls, health_score, last_analyzed, transcript_count,
          drive_call_count, new_call_count, last_synced.

    drive_call_count and new_call_count come from scanning the local
    Drive folder (reuse gdrive_service._get_meta_files + _group_by_account).
    """

def add_to_watchlist(
    account_ids: list[str],
    sf_account_names: dict[str, str] | None = None,
    added_by: str | None = None,
) -> list[dict]:
    """Add accounts to watchlist. Idempotent — skips already-watched.

    If sf_account_names not provided, defaults to accounts.account_name.
    Returns list of added watchlist entries.
    """

def remove_from_watchlist(account_id: str) -> bool:
    """Remove account from watchlist. Returns True if found and removed."""

def update_sf_name(account_id: str, sf_account_name: str) -> dict:
    """Update the Salesforce name for a watched account."""

def suggest_sf_name(account_id: str) -> dict:
    """Guess the SF name by matching account name against Drive folder filenames.

    Returns {drive_slug, suggested_sf_name, confidence}.
    """

def compute_new_calls_flag(account_id: str) -> bool:
    """Compute whether an account has new calls since last analysis.

    Implements the logic from design doc Section 4.
    Returns True if new calls available.
    """

def clear_new_calls_flag(account_id: str) -> None:
    """Clear has_new_calls flag. Called after analysis completes."""
```

Key implementation notes:
- `list_watched_accounts()` should do a single Drive folder scan (via `_group_by_account`) and look up each watched account, rather than scanning per-account (performance, per design Section 9.5)
- `compute_new_calls_flag()` implements the exact logic from design doc Section 4 (Condition A + Condition B)
- `suggest_sf_name()` uses existing `gdrive_service._extract_account_name()` + `_group_by_account()` to find matching slugs

### Task 3.2a: Add CSV import and pre-seed functions to watchlist service

**File:** `sis/services/watchlist_service.py`

```python
def add_all_accounts_to_watchlist(added_by: str | None = None) -> list[dict]:
    """Pre-seed watchlist with ALL current SIS accounts. Idempotent."""

def import_csv(file_content: str | bytes) -> dict:
    """Parse CSV with columns: account_name (required), sf_account_name (optional).
    Fuzzy-match account_name against SIS accounts.
    Returns: {matched: [{account_id, account_name, sf_name}], unmatched: [str]}
    """

def upload_tam_list(file_content: str | bytes) -> dict:
    """Upload/update the TAM reference list for SF name suggestions.
    Stored in tam_accounts table. Returns: {count: int}
    """

def suggest_sf_name_from_tam(account_name: str) -> str | None:
    """Fuzzy-match account name against TAM list. Returns best match or None."""
```

The TAM list needs a simple reference table:
```sql
CREATE TABLE tam_accounts (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL UNIQUE,
    uploaded_at TEXT NOT NULL DEFAULT (now_utc())
);
```

Add this table to the Alembic migration in Phase 1.

### Task 3.2: Create watchlist API routes

**File:** `sis/api/routes/watchlist.py` (new file)

```python
router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

# Pydantic schemas
class WatchlistAddRequest(BaseModel):
    account_ids: list[str]
    sf_account_names: Optional[dict[str, str]] = None

class SFNameUpdateRequest(BaseModel):
    sf_account_name: str

# Routes
@router.get("/")
def list_watchlist(user: dict = Depends(get_current_user)):
    return watchlist_service.list_watched_accounts()

@router.post("/")
def add_to_watchlist(body: WatchlistAddRequest, user: dict = Depends(get_current_user)):
    return watchlist_service.add_to_watchlist(
        body.account_ids, body.sf_account_names, added_by=user.get("sub")
    )

@router.delete("/{account_id}")
def remove_from_watchlist(account_id: str, user: dict = Depends(get_current_user)):
    removed = watchlist_service.remove_from_watchlist(account_id)
    if not removed:
        raise HTTPException(404, "Account not on watchlist")
    return {"ok": True}

@router.put("/{account_id}/sf-name")
def update_sf_name(account_id: str, body: SFNameUpdateRequest, user: dict = Depends(get_current_user)):
    return watchlist_service.update_sf_name(account_id, body.sf_account_name)
```

Add to the same file:

```python
@router.post("/add-all")
def add_all_accounts(user: dict = Depends(get_current_user)):
    """Pre-seed watchlist with all current SIS accounts."""
    return watchlist_service.add_all_accounts_to_watchlist(added_by=user.get("sub"))

@router.post("/import-csv")
async def import_csv(file: UploadFile, user: dict = Depends(get_current_user)):
    """Upload CSV to match and add accounts to watchlist."""
    content = await file.read()
    return watchlist_service.import_csv(content)

@router.post("/tam-list")
async def upload_tam_list(file: UploadFile, user: dict = Depends(get_current_user)):
    """Upload/update TAM reference list for SF name suggestions."""
    content = await file.read()
    return watchlist_service.upload_tam_list(content)
```

### Task 3.3: Register watchlist routes in main.py

**File:** `sis/api/main.py`

Add import and `app.include_router(watchlist.router)`.

### Task 3.4: Hook into analysis completion — clear `has_new_calls`

**File:** `sis/services/analysis_service.py`

In `_persist_pipeline_result()`, after successfully persisting the run, add:

```python
# Clear the "new calls" flag since we just analyzed with the latest data
from sis.services.watchlist_service import clear_new_calls_flag
clear_new_calls_flag(account_id)
```

This ensures the "New" badge disappears after analysis runs.

### Task 3.5: Write tests for watchlist service

**File:** `tests/test_watchlist_service.py` (new file)

Test cases:
- Add accounts to watchlist, verify they appear in list
- Add duplicate account (idempotent, no error)
- Remove from watchlist
- Update SF name
- `compute_new_calls_flag`: brand new account (no transcripts) -> True
- `compute_new_calls_flag`: account with transcripts but no analysis -> True
- `compute_new_calls_flag`: account with analysis, no new calls -> False
- `compute_new_calls_flag`: account with analysis, newer calls exist -> True
- `clear_new_calls_flag` sets column to 0

### Verification:
- [ ] All watchlist service tests pass
- [ ] API endpoints accessible via curl/httpie
- [ ] Adding and removing accounts works
- [ ] has_new_calls flag set and cleared correctly

---

## Phase 4: Sync Orchestrator + Progress Store (backend-developer)

**Product impact:** The core engine that runs the sync. Still backend-only, but the most complex phase.

### Task 4.1: Create sync progress store

**File:** `sis/services/sync_progress_store.py` (new file)

Follows the exact pattern from `sis/orchestrator/progress_store.py` but for sync jobs instead of analysis runs.

```python
# Thread-safe in-memory store for sync job progress
# Keyed by sync_job_id
# Each entry tracks:
#   - Overall job status and phase
#   - Per-account N8N status
#   - Per-account import status
#   - Drive sync countdown
#   - Error log

def init_sync(job_id: str, accounts: list[dict]) -> None:
    """Initialize sync entry with all accounts in pending state."""

def update_n8n_status(job_id: str, account_id: str,
                       status: str, calls_found: int | None = None,
                       error: str | None = None) -> None:
    """Update N8N extraction status for one account."""

def set_phase(job_id: str, phase: str, detail: dict | None = None) -> None:
    """Set current phase: 'n8n_extraction' | 'waiting_for_drive' | 'importing' | 'completed' | 'failed'"""

def update_drive_poll_status(job_id: str, elapsed_seconds: int,
                              max_seconds: int, file_count: int,
                              stable_checks: int) -> None:
    """Update Drive sync polling status (countdown + file count + stability)."""

def update_import_status(job_id: str, account_id: str,
                          status: str, imported: int = 0,
                          skipped: int = 0) -> None:
    """Update import status for one account."""

def mark_sync_completed(job_id: str, summary: dict) -> None:
    """Mark sync as completed with final summary."""

def get_sync_snapshot(job_id: str) -> dict | None:
    """Get read-only snapshot for SSE streaming."""

def cancel_sync(job_id: str) -> None:
    """Flag sync for cancellation."""

def is_sync_cancelled(job_id: str) -> bool:
    """Check cancellation flag."""
```

The snapshot returned by `get_sync_snapshot()` should be the full state that the SSE endpoint streams:

```python
{
    "job_id": "...",
    "status": "running",
    "phase": "n8n_extraction",  # or "waiting_for_drive", "importing", "completed"
    "total_accounts": 15,
    "n8n_progress": {
        "completed": 8,
        "total": 15,
        "current_account": "Abound",
    },
    "drive_poll": {
        "elapsed_seconds": 30,
        "max_seconds": 180,
        "file_count": 2985,
        "stable_checks": 1,    # out of 2 needed
        "status": "polling",   # "polling" | "stabilized" | "timeout"
    },
    "import_progress": {
        "completed": 0,
        "total": 15,
    },
    "accounts": {
        "uuid1": {
            "name": "Babyboo",
            "n8n_status": "success",
            "n8n_calls_found": 7,
            "import_status": "pending",
            "calls_imported": 0,
        },
        # ...
    },
    "summary": None,  # filled when completed
    "errors": [],
}
```

### Task 4.2: Create sync orchestrator service

**File:** `sis/services/sync_orchestrator.py` (new file)

This is the main engine. It's an async function that runs as a background task.

```python
async def run_sync(
    job_id: str,
    watched_accounts: list[dict],  # from watchlist_service
    start_date: str = N8N_DEFAULT_START_DATE,
    skip_n8n: bool = False,
) -> None:
    """Execute the full sync flow.

    Called as a background task from the API endpoint.
    Updates progress_store and DB throughout.

    Phases:
    1. N8N extraction (sequential, 15s delay between)
    2. Drive sync wait (90s countdown)
    3. Scan + Import (uses existing gdrive_service)
    4. Compute "new" flags + finalize
    """
```

Implementation details per phase:

**Phase 1 — N8N Extraction:**
- Loop through `watched_accounts` sequentially
- For each: call `n8n_client.extract_gong_calls(sf_account_name, start_date)`
- Update `sync_progress_store` and `sync_account_results` DB row after each call
- Check `is_sync_cancelled()` between each call
- `asyncio.sleep(N8N_INTER_REQUEST_DELAY)` between calls
- Track timing for `n8n_phase_seconds`

**Phase 2 — Drive Sync Wait (poll-based):**
- `set_phase(job_id, "waiting_for_drive")`
- Take initial snapshot of local Drive folder file count + total size
- Poll every `N8N_DRIVE_POLL_INTERVAL` (10s) for up to `N8N_DRIVE_POLL_MAX_WAIT` (180s)
- "Stabilized" = same file count + total size for `N8N_DRIVE_STABILITY_CHECKS` (2) consecutive checks
- Update progress store each poll with: elapsed time, file count, stability status
- If stabilized early, proceed immediately (saves wait time)
- If max wait exceeded, proceed with warning "Drive may still be syncing"
- Check cancellation flag each poll tick

**Phase 3 — Scan + Import:**
- `set_phase(job_id, "importing")`
- **Single scan:** Call `gdrive_service._get_meta_files(drive_root)` once, then `_group_by_account()` to get all files grouped by account slug
- For each watched account:
  - Match account name to Drive slug (case-insensitive)
  - Use `gdrive_service.download_and_parse_calls(drive_path, max_calls=50, account_name=slug)` to parse
  - Use `gdrive_service.upload_calls_to_db(parsed_calls, account_id)` to import with dedup
  - Update progress store + DB
  - Track `calls_imported` and `calls_skipped` counts

**Phase 4 — Finalize:**
- For each watched account, call `watchlist_service.compute_new_calls_flag(account_id)` and update `accounts.has_new_calls`
- Aggregate stats into `sync_jobs` row
- Set `status = "completed"`, `completed_at = now()`
- `mark_sync_completed(job_id, summary)`

**Error handling:**
- Wrap each N8N call in try/except — log error, continue to next account
- Wrap each import in try/except — log error, continue to next account
- If the entire orchestrator crashes, catch the outermost exception, set `status = "failed"`, persist error

### Task 4.3: Add `skip_n8n` support

The `run_sync()` function should accept `skip_n8n: bool = False`. When True:
- Skip Phase 1 and Phase 2 entirely
- Go directly to Phase 3 (scan + import)
- This is the "just check Drive for new files" mode — useful after N8N timeouts

### Task 4.4: Write tests for sync orchestrator

**File:** `tests/test_sync_orchestrator.py` (new file)

Test cases (all with mocked N8N client):
- Happy path: 3 accounts, all succeed, files found and imported
- Mixed results: 1 success, 1 error, 1 timeout
- Cancellation: cancel during N8N phase, verify import phase skipped
- skip_n8n mode: verify Phase 1+2 skipped
- No files found for an account (import_status = "skipped")
- N8N reports calls but no new files in Drive (warning in results)
- Dedup: run sync twice, second time imports 0 new calls
- Large folder scan optimization: verify `_group_by_account` called once, not per-account

### Verification:
- [ ] Orchestrator tests pass with mocked dependencies
- [ ] Progress store snapshots contain correct state at each phase
- [ ] Cancellation flag respected between N8N calls
- [ ] DB sync_jobs and sync_account_results populated correctly

---

## Phase 5: Sync API + SSE Endpoints (backend-developer)

**Product impact:** APIs are now callable. Sync can be triggered and monitored via API, just not through the UI yet.

### Task 5.1: Create sync API routes

**File:** `sis/api/routes/sync.py` (new file)

```python
router = APIRouter(prefix="/api/sync", tags=["sync"])

class SyncStartRequest(BaseModel):
    account_ids: Optional[list[str]] = None  # subset of watchlist, or None=all
    start_date: Optional[str] = None
    skip_n8n: bool = False

@router.post("/start")
async def start_sync(
    body: SyncStartRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Start a bulk sync job. Returns immediately with job_id for SSE tracking.

    Guards:
    - Check no sync is already running (409 Conflict if so)
    - Validate watchlist is not empty
    - Validate watchlist is not empty
    """

@router.get("/status/{job_id}")
def get_sync_status(job_id: str, user: dict = Depends(get_current_user)):
    """Polling fallback for sync status (for when SSE isn't available)."""

@router.post("/{job_id}/cancel")
def cancel_sync(job_id: str, user: dict = Depends(get_current_user)):
    """Cancel an in-progress sync."""

@router.get("/history")
def sync_history(user: dict = Depends(get_current_user)):
    """List recent sync jobs, most recent first."""

@router.get("/suggest-sf-name/{account_id}")
def suggest_sf_name(account_id: str, user: dict = Depends(get_current_user)):
    """Guess the Salesforce name from Drive filenames."""
```

**Concurrent sync guard** in `start_sync`:
```python
# Check for running sync
with get_session() as session:
    running = session.query(SyncJob).filter(
        SyncJob.status.in_(["pending", "running", "scanning", "importing"])
    ).first()
    if running:
        raise HTTPException(409, detail={
            "message": "Sync already in progress",
            "job_id": running.id
        })
```

### Task 5.2: Add SSE endpoint for sync progress

**File:** `sis/api/routes/sse.py` (modify existing)

Add a new endpoint:

```python
@router.get("/sync/{job_id}")
async def sync_progress(job_id: str):
    """SSE stream for sync job progress. Follows same pattern as analysis SSE."""

    async def event_stream():
        elapsed = 0
        while elapsed < SSE_TIMEOUT_SECONDS:
            snapshot = get_sync_snapshot(job_id)
            if not snapshot:
                yield f"data: {json.dumps({'job_id': job_id, 'status': 'not_found'})}\n\n"
                break
            yield f"data: {json.dumps(snapshot)}\n\n"
            if snapshot["status"] in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(1)
            elapsed += 1
        else:
            yield f"data: {json.dumps({'job_id': job_id, 'status': 'timeout'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### Task 5.3: Register sync routes in main.py

**File:** `sis/api/main.py`

```python
from sis.api.routes import sync
app.include_router(sync.router)
```

### Task 5.4: End-to-end API test

Test the full flow via API calls (curl or test client):
1. Add accounts to watchlist: `POST /api/watchlist/`
2. Start sync: `POST /api/sync/start` (with `skip_n8n: true` for testing)
3. Monitor via SSE: `GET /api/sse/sync/{job_id}`
4. Verify accounts imported, has_new_calls updated
5. Cancel a running sync: `POST /api/sync/{job_id}/cancel`

### Verification:
- [ ] `/api/sync/start` creates job and returns job_id
- [ ] SSE stream shows real-time progress
- [ ] Concurrent sync prevention works (409)
- [ ] Cancel stops the sync between accounts
- [ ] `/api/sync/history` shows past syncs
- [ ] `skip_n8n` mode works (scan-only)

---

## Phase 6: Frontend — Watchlist Page (frontend-developer)

**Product impact:** Users can now see and manage their watchlist. This is the primary user-facing delivery.

### Task 6.1: Add frontend API types

**File:** `frontend/src/lib/api-types.ts`

```typescript
// ── Watchlist ──
export interface WatchlistAccount {
  account_id: string;
  account_name: string;
  sf_account_name: string;
  has_new_calls: boolean;
  health_score: number | null;
  last_analyzed: string | null;
  last_synced: string | null;
  transcript_count: number;
  drive_call_count: number;
  new_call_count: number;
  added_at: string;
}

export interface SyncJob {
  job_id: string;
  status: 'pending' | 'running' | 'scanning' | 'importing' | 'completed' | 'failed' | 'cancelled';
  total_accounts: number;
  started_at: string;
  completed_at: string | null;
  calls_imported: number;
  calls_skipped: number;
  n8n_calls_succeeded: number;
  n8n_calls_failed: number;
  total_seconds: number | null;
}

export interface SyncProgress {
  job_id: string;
  status: string;
  phase: 'n8n_extraction' | 'waiting_for_drive' | 'importing' | 'completed' | 'failed' | 'cancelled';
  total_accounts: number;
  n8n_progress: { completed: number; total: number; current_account: string | null };
  drive_countdown: number | null;
  import_progress: { completed: number; total: number };
  accounts: Record<string, {
    name: string;
    n8n_status: string;
    n8n_calls_found: number | null;
    import_status: string;
    calls_imported: number;
  }>;
  summary: Record<string, unknown> | null;
  errors: string[];
}

export interface SFNameSuggestion {
  drive_slug: string;
  suggested_sf_name: string;
  confidence: 'exact_match' | 'slug_match' | 'unknown';
}
```

### Task 6.2: Add API client methods

**File:** `frontend/src/lib/api.ts`

Add to the `api` object:

```typescript
watchlist: {
  list: () => apiFetch<WatchlistAccount[]>('/api/watchlist/'),
  add: (accountIds: string[], sfNames?: Record<string, string>) =>
    apiFetch<WatchlistAccount[]>('/api/watchlist/', {
      method: 'POST',
      body: JSON.stringify({ account_ids: accountIds, sf_account_names: sfNames }),
    }),
  remove: (accountId: string) =>
    apiFetch<{ ok: boolean }>(`/api/watchlist/${accountId}`, { method: 'DELETE' }),
  updateSFName: (accountId: string, sfName: string) =>
    apiFetch<WatchlistAccount>(`/api/watchlist/${accountId}/sf-name`, {
      method: 'PUT',
      body: JSON.stringify({ sf_account_name: sfName }),
    }),
},
sync: {
  start: (params?: { account_ids?: string[]; start_date?: string; skip_n8n?: boolean }) =>
    apiFetch<{ job_id: string; status: string; total_accounts: number }>(
      '/api/sync/start',
      { method: 'POST', body: JSON.stringify(params || {}) },
    ),
  status: (jobId: string) => apiFetch<SyncJob>(`/api/sync/status/${jobId}`),
  cancel: (jobId: string) =>
    apiFetch<{ ok: boolean }>(`/api/sync/${jobId}/cancel`, { method: 'POST' }),
  history: () => apiFetch<SyncJob[]>('/api/sync/history'),
  suggestSFName: (accountId: string) =>
    apiFetch<SFNameSuggestion>(`/api/sync/suggest-sf-name/${accountId}`),
},
```

### Task 6.3: Create `useSyncProgress` hook

**File:** `frontend/src/lib/hooks/use-sync.ts` (new file)

Custom hook that:
- Connects to SSE endpoint `/api/sse/sync/{jobId}`
- Parses `SyncProgress` events
- Exposes `{ progress, isRunning, error }`
- Auto-closes when sync completes/fails

Pattern follows the existing analysis SSE usage in the upload page.

### Task 6.4: Create Watchlist page

**File:** `frontend/src/app/(app)/watchlist/page.tsx` (new file)

Page structure (dark theme, matching Signal Clarity design system):

**Header section:**
- Title "Watchlist"
- "Add Accounts" button (opens dialog)
- "Sync All" button (primary action)
- "Scan Only" button (secondary — calls with `skip_n8n: true`)
- "History" button (shows past sync jobs)

**Filter bar:**
- Search input (filters by account name)
- Status filter: All | New | Up to Date

**Table:**
| Column | Source | Notes |
|--------|--------|-------|
| Account | `account_name` | Link to `/accounts/{id}`, NEW badge if `has_new_calls` |
| SF Name | `sf_account_name` | Editable inline, with drive slug suggestion |
| Status | computed | "X new calls" / "Up to date" / "Never synced" |
| Health | `health_score` | Color-coded badge (green/yellow/red), "--" if null |
| Last Analyzed | `last_analyzed` | Relative time ("2h ago") |
| Last Synced | `last_synced` | Relative time |
| Actions | - | Remove button (trash icon) |

**Add Accounts Dialog:**
- Modal with a multi-select list of all SIS accounts NOT already on watchlist
- Search filter
- Each row shows: account name, suggested SF name (from Drive), editable SF name field
- "Add Selected" button

**Key UX decisions:**
- Empty state: "No accounts on watchlist. Add accounts to start tracking Gong sync status."
- Sort: accounts with `has_new_calls=true` first, then alphabetically
- Table cells need `whitespace-normal` (lesson learned from methodology page)

### Task 6.5: Create Sync Progress Modal

**File:** `frontend/src/components/sync-progress-modal.tsx` (new file)

Shown when "Sync All" or "Scan Only" is clicked. Uses `useSyncProgress` hook.

Three-phase progress display:
1. **Phase 1 — N8N Extraction**: Progress bar + per-account status list (checkmark/spinner/X)
2. **Phase 2 — Drive Sync Wait**: Countdown timer
3. **Phase 3 — Import**: Progress bar + per-account import counts

Cancel button in header. Dismissible after completion.

Summary at the end: "Synced 15 accounts. 23 new calls imported. 3 accounts have new data."

### Task 6.6: Add Watchlist to sidebar navigation

**File:** `frontend/src/components/sidebar.tsx`

In the `Actions` group, add between "Import & Analyze" and "Chat":

```typescript
{ label: 'Watchlist', href: '/watchlist', icon: Eye },  // or use `ListChecks` from lucide
```

Import the icon:
```typescript
import { Eye } from 'lucide-react';
// or: import { ListChecks } from 'lucide-react';
```

Also add a "new data" dot indicator when any watched account has `has_new_calls`. This requires either:
- A lightweight API call on sidebar mount to check watchlist status, OR
- A global context/store that the watchlist page populates

For the POC, a simple approach: add `useWatchlistStatus()` hook that calls `GET /api/watchlist/` on mount and checks if any has `has_new_calls`. Show a small green dot next to "Watchlist" if so.

### Task 6.7: Add "New" badge to pipeline/accounts list and deal detail

The "NEW" badge must appear on ALL surfaces, not just the watchlist:

**File:** Pipeline/accounts list page
- Add a "NEW" badge next to account name when `has_new_calls` is true
- `has_new_calls` is already included in the account list API response (Phase 1, Task 1.6)

**File:** Deal detail page header
- Show "NEW" badge next to account name in the detail header when `has_new_calls` is true

### Task 6.8: Add CSV import + "Add All" + TAM upload to watchlist UI

**Add Accounts Dialog** should support:
1. **Search & select** — existing multi-select from SIS accounts
2. **Add All Current Accounts** button — calls `POST /api/watchlist/add-all`, pre-seeds all 66 accounts
3. **Import CSV** — file upload, shows matched/unmatched preview before confirming
4. **Upload TAM List** — separate button to upload the TAM reference CSV for SF name suggestions

### Verification:
- [ ] Watchlist page loads and shows watched accounts
- [ ] Add Accounts dialog works — accounts appear after adding
- [ ] Remove from watchlist works
- [ ] SF name edit works inline
- [ ] Sync All triggers sync, progress modal shows real-time updates
- [ ] Scan Only works (skip_n8n mode)
- [ ] NEW badge appears on accounts with new calls
- [ ] Sidebar shows Watchlist link with dot indicator for new data
- [ ] Empty state renders correctly

---

## Phase 7: Integration Testing + Polish (code-reviewer + frontend-developer)

**Product impact:** Everything works end-to-end. This phase is about hardening, not new features.

### Task 7.1: End-to-end manual test

Full scenario:
1. Add 3-5 accounts to watchlist with correct SF names
2. Click "Sync All"
3. Watch N8N extraction progress (15s between each account)
4. Watch Drive sync countdown (90s)
5. Watch import progress
6. Verify NEW badges appear for accounts with new calls
7. Click through to an account with new calls, run analysis
8. Verify NEW badge clears after analysis
9. Click "Scan Only" to re-scan without calling N8N
10. Verify "Sync already in progress" guard works (click Sync twice rapidly)

### Task 7.2: Error scenario testing

- Test with a deliberately wrong SF name (should see N8N error but sync continues)
- Test cancellation mid-sync
- Test with an account that has 0 calls in Gong
- Test with `skip_n8n: true` when new files were added manually to Drive
- Verify Drive duplicate files `(1)` are filtered correctly

### Task 7.3: Performance check

- Scan 2,970+ files in Drive folder: should complete in <5 seconds
- Full sync of 15 accounts: should complete in ~5 min (15 accounts x 15s delay + 90s wait)
- Verify SSE stream doesn't memory-leak (progress store cleanup)

### Task 7.4: Code review and polish

- Review all new files for:
  - Error handling completeness
  - Logging adequacy (INFO for success, WARNING for errors, no DEBUG spam)
  - Type safety (no `any` in frontend types)
  - Consistent naming (snake_case in Python, camelCase in TypeScript)
  - Auth on all endpoints
  - No N8N webhook URL exposed to frontend

### Task 7.5: Update `has_new_calls` in account list/detail responses

**File:** `frontend/src/lib/api-types.ts`

Add `has_new_calls?: boolean` to the `Account` interface so the pipeline/accounts pages could optionally show the flag in the future.

---

## File Change Summary

### New Files (Backend)
| File | Phase | Description |
|------|-------|-------------|
| `sis/services/n8n_client.py` | 2 | HTTP client for N8N webhook |
| `sis/services/watchlist_service.py` | 3 | Watchlist CRUD + new-calls logic |
| `sis/services/sync_orchestrator.py` | 4 | Async sync engine (3-phase flow) |
| `sis/services/sync_progress_store.py` | 4 | In-memory progress tracking for SSE |
| `sis/api/routes/watchlist.py` | 3 | Watchlist API endpoints |
| `sis/api/routes/sync.py` | 5 | Sync start/cancel/history endpoints |
| `alembic/versions/xxxx_add_watchlist_sync.py` | 1 | Migration for new tables + column |
| `tests/test_n8n_client.py` | 2 | N8N client unit tests |
| `tests/test_watchlist_service.py` | 3 | Watchlist service tests |
| `tests/test_sync_orchestrator.py` | 4 | Sync orchestrator tests |

### New Files (Frontend)
| File | Phase | Description |
|------|-------|-------------|
| `frontend/src/app/(app)/watchlist/page.tsx` | 6 | Watchlist page |
| `frontend/src/components/sync-progress-modal.tsx` | 6 | Sync progress UI |
| `frontend/src/lib/hooks/use-sync.ts` | 6 | SSE hook for sync progress |

### Modified Files (Backend)
| File | Phase | Change |
|------|-------|--------|
| `sis/db/models.py` | 1 | Add 4 models + `has_new_calls` column |
| `sis/config.py` | 2 | Add N8N config constants |
| `sis/services/analysis_service.py` | 3 | Clear `has_new_calls` after analysis |
| `sis/services/account_service.py` | 1 | Include `has_new_calls` in list/detail |
| `sis/api/routes/sse.py` | 5 | Add sync SSE endpoint |
| `sis/api/main.py` | 3, 5 | Register watchlist + sync routers |

### Modified Files (Frontend)
| File | Phase | Change |
|------|-------|--------|
| `frontend/src/lib/api-types.ts` | 6 | Add Watchlist/Sync/Progress types |
| `frontend/src/lib/api.ts` | 6 | Add `watchlist` and `sync` API methods |
| `frontend/src/components/sidebar.tsx` | 6 | Add Watchlist nav item with dot indicator |

---

## Dependency Graph

```
Phase 1 (DB)
    |
    v
Phase 2 (N8N Client)     Phase 3 (Watchlist Service + API)
    |                         |
    +----------+--------------+
               |
               v
         Phase 4 (Sync Orchestrator)
               |
               v
         Phase 5 (Sync API + SSE)
               |
               v
         Phase 6 (Frontend)
               |
               v
         Phase 7 (Integration + Polish)
```

Note: Phases 2 and 3 can be done in parallel since they don't depend on each other. Both must complete before Phase 4.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| N8N webhook URL changes | Config-driven, env var override |
| N8N response format changes | Defensive parsing, log raw response for debugging |
| Drive sync takes longer than expected | Poll-based detection (10s intervals, 3 min max), "Scan Only" re-scan button |
| Drive folder grows very large | Single scan + group by account (not per-account scans) |
| User enters wrong SF name | Drive slug suggestion, editable in watchlist UI |
| Sync takes long for many accounts | SSE progress widget keeps user informed with per-account detail, cancel button available |
| Backend restart during sync | Sync job left as "running" in DB; on next start attempt, stale job cleanup needed |

### Stale Sync Job Cleanup

Add a startup check or a guard in `start_sync`:
- If a sync job has `status=running` but `started_at` is older than 30 minutes, mark it as `failed` (it crashed)
- This prevents a stuck "sync in progress" state after a backend restart

---

## Decisions (All Resolved 2026-03-12)

All open questions have been resolved. See Design Doc Section 13 for full details.

1. **SF name source** — Manual entry + TAM list fuzzy matching + Drive slug hints
2. **Drive sync** — Poll-based (10s intervals, 3 min max, 2 stability checks)
3. **Watchlist scope** — Global (shared)
4. **Sync frequency** — Manual trigger only
5. **"New" badge** — Everywhere (watchlist, sidebar, pipeline, deal detail)
6. **Watchlist size** — No cap
7. **Date range** — Always 2025-01-01 to today
8. **Account input** — Single add + CSV import + "Add All" pre-seed
9. **N8N processing** — Sequential, one account at a time, 15s delay
10. **Progress widget** — Detailed per-account status throughout all phases

**Resolved (2026-03-13):** Switched to Okta Workflows endpoint (no auth needed). Webhook returns 503 after ~31s but files still land in Drive — this is expected behavior handled by the fire-and-verify pattern. Full implementation complete across 7 phases.
