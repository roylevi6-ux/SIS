# Automated Gong Sync — Design Document

**Date:** 2026-03-12
**Status:** Ready for Implementation (decisions finalized 2026-03-12)
**Author:** Dev Lead (Claude)
**Blocked on:** N8N webhook returning 401 Unauthorized — URL/token may need refresh

---

## 1. Product Context

### What changes for the user

Today, importing Gong calls into SIS is a multi-step manual process: the user navigates to the Upload page, selects the Google Drive folder, browses accounts, picks call counts, and clicks Import — one account at a time. There is no way to know which accounts have fresh Gong calls without manually scanning the Drive folder.

**Automated Gong Sync** replaces this with a managed watchlist + one-click bulk sync:

1. User adds accounts to a "Watchlist" — these are the deals they actively care about
2. A single "Sync" button checks ALL watched accounts for new Gong calls via N8N
3. N8N extracts calls from Gong's API and drops them in Google Drive
4. SIS detects which accounts have new data and marks them with a "New" badge
5. User still manually triggers analysis — no auto-analysis yet

### Why this matters

- **Time savings**: Checking 30 accounts manually takes 15+ minutes. Sync does it in one click.
- **Freshness visibility**: Reps and TLs immediately see which accounts have new intelligence waiting.
- **Pipeline discipline**: Accounts on the watchlist are the pipeline — this creates a natural workflow for regular deal reviews.

### What this does NOT include

- Auto-triggering analysis after sync (future phase)
- Salesforce data sync (separate feature)
- Real-time push notifications when new calls appear

---

## 2. Architecture Overview

```
                                                    +-----------+
                                                    |   N8N     |
                                                    | Webhook   |
                                                    +-----+-----+
                                                          |
                                                          | POST per account
                                                          v
+--------+     +-------------+     +-------------+     +--------+     +-----------+
|  UI    | --> |  Sync API   | --> |  N8N Client  | --> | Gong   | --> | Google    |
|        |     |  Endpoint   |     |  Service     |     | API    |     | Drive     |
|  Watch |     |             |     |              |     +--------+     +-----+-----+
|  list  | <-- |  SSE Stream | <-- | Orchestrator |                         |
+--------+     +-------------+     +------+-------+                         |
                                          |                          Drive for Desktop
                                          v                          auto-sync (~30-120s)
                                   +------+-------+                         |
                                   |  Folder      | <-----------------------+
                                   |  Scanner     |
                                   |  (gdrive_    |
                                   |   service)   |
                                   +------+-------+
                                          |
                                          v
                                   +------+-------+
                                   |  Import      |
                                   |  Pipeline    |
                                   |  (existing)  |
                                   +--------------+
```

### Flow

1. **User clicks Sync** on the Watchlist page
2. Backend creates a `SyncJob` record (status: `running`)
3. For each watched account (sequentially, with 15s delay between):
   a. POST to N8N webhook with the account's Salesforce name
   b. Record the N8N response (success/fail, calls found)
   c. Wait for Drive sync (configurable delay, default 60s after last N8N call)
4. After all N8N calls complete + Drive sync delay:
   a. Scan the local Drive folder for all watched accounts
   b. Cross-reference with DB to find un-imported calls
   c. Auto-import any new calls found (using existing `gdrive_service.upload_calls_to_db`)
5. Compute "New" status for each account based on the tag logic
6. Update `SyncJob` with results, mark complete

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sync is sequential, not parallel | Sequential with 15s delay | N8N is flaky under load; parallel requests risk failures |
| Single Drive sync wait at the end | 90s delay after last N8N call | Drive for Desktop syncs continuously; waiting at the end is simpler than per-account waits |
| Import happens automatically | Yes, all new calls are imported | No reason to see new files in Drive and not import them — dedup handles safety |
| "New" tag is per-account, not per-call | Correct | User cares "does this account have fresh intel?" not "which specific call is new" |
| N8N response is not trusted for success | Correct | N8N may say "error" but still work; we always scan Drive as the source of truth |
| Watchlist is global (not per-user) | Correct for POC | 2-person household; per-user scoping is over-engineering for now |
| No account cap on watchlist | No limit | At 15s delay, large lists just take longer — progress widget keeps user informed |
| Drive sync detection uses polling | Poll every 10s for 3 min | More reliable than fixed 90s wait; stabilize = same file count for 2 consecutive checks |
| "New" badge shown everywhere | All surfaces | Watchlist, sidebar dot, pipeline/accounts list, deal detail |
| TAM list used for SF name suggestions | Fuzzy match | User provides TAM list; used to suggest SF names when adding accounts |
| Pre-seed watchlist with all current SIS accounts | On first setup | All 66 existing accounts auto-added to watchlist |

---

## 3. Database Schema

### 3.1 New Table: `watchlist_accounts`

Tracks which accounts are on the watchlist. Lightweight — just a FK to accounts with metadata.

```sql
CREATE TABLE watchlist_accounts (
    id          TEXT PRIMARY KEY DEFAULT (uuid4()),
    account_id  TEXT NOT NULL REFERENCES accounts(id),
    -- The exact Salesforce account name for N8N API (case-sensitive).
    -- May differ from accounts.account_name (which is Title Case normalized).
    sf_account_name TEXT NOT NULL,
    added_by    TEXT REFERENCES users(id),
    added_at    TEXT NOT NULL DEFAULT (now_utc()),

    UNIQUE(account_id)  -- An account can only be watched once
);
CREATE INDEX ix_watchlist_account ON watchlist_accounts(account_id);
```

**Why `sf_account_name`?**
`accounts.account_name` is normalized to Title Case by `normalize_account_name()`. The N8N webhook requires the EXACT Salesforce name (case-sensitive). We store the raw SF name separately so syncs use the correct casing without polluting the display name.

### 3.2 New Table: `sync_jobs`

Tracks the overall bulk sync operation. One row per "Sync" button click.

```sql
CREATE TABLE sync_jobs (
    id              TEXT PRIMARY KEY DEFAULT (uuid4()),
    status          TEXT NOT NULL DEFAULT 'pending',
        -- pending | running | scanning | importing | completed | failed | cancelled
    triggered_by    TEXT REFERENCES users(id),
    started_at      TEXT NOT NULL DEFAULT (now_utc()),
    completed_at    TEXT,

    -- Aggregate results
    total_accounts      INTEGER NOT NULL DEFAULT 0,
    n8n_calls_made      INTEGER DEFAULT 0,
    n8n_calls_succeeded INTEGER DEFAULT 0,
    n8n_calls_failed    INTEGER DEFAULT 0,
    new_calls_found     INTEGER DEFAULT 0,
    calls_imported      INTEGER DEFAULT 0,
    calls_skipped       INTEGER DEFAULT 0,

    -- Timing
    n8n_phase_seconds   REAL,     -- Time spent calling N8N
    scan_phase_seconds  REAL,     -- Time spent scanning Drive + importing
    total_seconds       REAL,

    error_log   TEXT,   -- JSON array of errors
    created_at  TEXT NOT NULL DEFAULT (now_utc())
);
CREATE INDEX ix_sync_jobs_status ON sync_jobs(status, started_at);
```

### 3.3 New Table: `sync_account_results`

Per-account detail within a sync job. Enables showing per-account status in the UI during sync.

```sql
CREATE TABLE sync_account_results (
    id              TEXT PRIMARY KEY DEFAULT (uuid4()),
    sync_job_id     TEXT NOT NULL REFERENCES sync_jobs(id),
    account_id      TEXT NOT NULL REFERENCES accounts(id),
    account_name    TEXT NOT NULL,  -- Denormalized for display

    -- N8N phase
    n8n_status      TEXT DEFAULT 'pending',
        -- pending | calling | success | error | skipped
    n8n_calls_found     INTEGER,
    n8n_calls_processed INTEGER,
    n8n_files_created   INTEGER,
    n8n_response        TEXT,   -- Raw JSON response for debugging
    n8n_error           TEXT,
    n8n_duration_seconds REAL,

    -- Import phase
    import_status       TEXT DEFAULT 'pending',
        -- pending | scanning | importing | completed | skipped | error
    new_files_found     INTEGER DEFAULT 0,
    calls_imported      INTEGER DEFAULT 0,
    calls_skipped       INTEGER DEFAULT 0,
    import_error        TEXT,

    -- "New" tag: was this account flagged as having new data?
    has_new_data        INTEGER DEFAULT 0,  -- boolean

    created_at  TEXT NOT NULL DEFAULT (now_utc())
);
CREATE INDEX ix_sync_results_job ON sync_account_results(sync_job_id);
CREATE INDEX ix_sync_results_account ON sync_account_results(account_id);
```

### 3.4 New Column on `accounts`

```sql
ALTER TABLE accounts ADD COLUMN has_new_calls INTEGER DEFAULT 0;
    -- boolean: 1 = new calls available that haven't been analyzed
    -- Updated by sync job and cleared when analysis runs
```

This denormalized flag avoids recalculating "new" status on every page load. It gets:
- **Set to 1** by the sync orchestrator when new calls are imported
- **Cleared to 0** when an analysis run completes for the account

---

## 4. "New" Tag Logic — Detailed Specification

An account gets `has_new_calls = 1` if **either** condition is true:

### Condition A: Brand New Account
No transcripts exist for this account in the DB (the account was just created during import, or exists but has never had calls imported).

```python
# Pseudo-code
transcript_count = session.query(Transcript).filter_by(account_id=acct_id).count()
if transcript_count == 0:
    return True
```

### Condition B: New Calls Since Last Analysis
There are imported calls with dates NEWER than the 5 most recent calls used in the last analysis run.

```python
# Get the 5 call dates used in the most recent analysis
latest_run = get_latest_completed_run(account_id)
if not latest_run:
    # Never analyzed — any imported calls make it "new"
    return transcript_count > 0

analyzed_transcript_ids = json.loads(latest_run.transcript_ids)
analyzed_dates = [
    t.call_date for t in session.query(Transcript)
    .filter(Transcript.id.in_(analyzed_transcript_ids))
    .all()
]
newest_analyzed_date = max(analyzed_dates) if analyzed_dates else "0000-00-00"

# Check if any active transcript has a newer date
newer_exists = session.query(Transcript).filter(
    Transcript.account_id == account_id,
    Transcript.call_date > newest_analyzed_date,
    ~Transcript.id.in_(analyzed_transcript_ids),
).first() is not None

return newer_exists
```

### When is the flag cleared?

The flag `accounts.has_new_calls` is set to `0`:
1. When `analyze_account()` or `analyze_account_async()` completes successfully for the account
2. Manually, if the user dismisses the "New" tag (nice-to-have, not MVP)

---

## 5. N8N Client Service

### 5.1 API Contract

```python
@dataclass
class N8NExtractRequest:
    account_name: str       # EXACT Salesforce name
    start_date: str         # YYYY-MM-DD
    end_date: str | None    # YYYY-MM-DD, defaults to today

@dataclass
class N8NExtractResponse:
    success: bool
    total_calls_found: int
    calls_processed: int
    files_created: int
    google_drive_folder: str
    raw_response: dict      # Full response for debugging
    error: str | None
    duration_seconds: float
```

### 5.2 Error Handling Strategy

N8N is described as "flaky and unstable." Our strategy is **fire-and-verify**:

1. **Don't trust the response for success/failure.**
   - N8N may return an error response while actually working (false negative)
   - N8N may return success but create 0 files
   - Always verify by scanning the local Drive folder after all N8N calls complete

2. **Timeout handling.**
   - HTTP timeout: 5 minutes (300s) per request
   - If timeout occurs, log as "timed_out" but DON'T treat as fatal
   - The N8N job may still be running and files may appear later

3. **No retries within a sync.**
   - If N8N fails for an account, log the error and move to the next account
   - The user can re-sync later; retrying immediately risks overwhelming N8N
   - Exception: if we get a clearly transient error (429 Too Many Requests, 503), we can retry once after a 30s delay

4. **Rate limiting.**
   - Minimum 15 seconds between sequential N8N calls
   - After all calls complete, wait 90 seconds for Drive to sync before scanning
   - These delays are configurable in `config.py`

5. **Response classification:**

| Response Status | N8N Body | Classification | Action |
|-----------------|----------|----------------|--------|
| 200 | `success: true, totalCallsFound > 0` | Definite success | Record call count |
| 200 | `success: true, totalCallsFound: 0` | No calls found | Mark as "no calls" (not an error) |
| 200 | `success: false` | Reported failure | Log warning, but still scan Drive later |
| 4xx | Any | Client error | Log as error; likely bad account name |
| 5xx | Any | Server error | Log as error, don't retry |
| Timeout | N/A | Timeout | Log as "timed_out", still scan Drive |

### 5.3 Configuration

```python
# config.py additions
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

---

## 6. Sync Orchestrator Service

The orchestrator coordinates the entire sync flow. It runs as an async background task (FastAPI `BackgroundTasks`), with SSE for real-time progress.

### 6.1 Sync Lifecycle

```
User clicks Sync
        |
        v
  Create SyncJob (status: running)
  Create SyncAccountResult per watched account (status: pending)
        |
        v
  Phase 1: N8N Extraction (sequential)
    For each watched account:
      1. Update result status -> "calling"
      2. POST to N8N webhook
      3. Record response
      4. Wait 15 seconds
      5. Update result status -> "success" | "error" | "timed_out"
      6. Emit SSE event
        |
        v
  Phase 2: Drive Sync Wait (poll-based)
    Poll local folder every 10s for up to 3 min
    "Stable" = same file count for 2 consecutive checks
    (emit SSE "waiting_for_drive" events with file count + countdown)
        |
        v
  Phase 3: Scan + Import
    For each watched account:
      1. Scan local Drive folder for account's files
      2. Cross-reference with DB (existing dedup logic)
      3. Import new calls via gdrive_service.upload_calls_to_db
      4. Compute "new" flag
      5. Update result status -> "completed"
      6. Emit SSE event
        |
        v
  Phase 4: Finalize
    Update SyncJob with aggregate stats
    Update accounts.has_new_calls for flagged accounts
    Status -> "completed"
    Final SSE event
```

### 6.2 SSE Event Schema

```typescript
// Events sent during sync
type SyncSSEEvent =
  | { type: 'sync_started'; job_id: string; total_accounts: number }
  | { type: 'n8n_progress'; account_name: string; index: number; total: number;
      status: 'calling' | 'success' | 'error' | 'timed_out' | 'no_calls';
      calls_found?: number }
  | { type: 'n8n_phase_complete'; succeeded: number; failed: number; total_calls: number }
  | { type: 'waiting_for_drive'; delay_seconds: number }
  | { type: 'import_progress'; account_name: string; index: number; total: number;
      status: 'scanning' | 'importing' | 'completed' | 'skipped';
      new_calls?: number; imported?: number }
  | { type: 'sync_completed'; job_id: string; summary: SyncSummary }
  | { type: 'sync_failed'; job_id: string; error: string }
```

### 6.3 Cancellation

User can cancel an in-progress sync. This:
1. Sets a cancellation flag on the SyncJob
2. The orchestrator checks this flag between N8N calls
3. Any already-started N8N call will complete (can't cancel HTTP requests mid-flight)
4. Import phase is skipped if cancelled during N8N phase
5. Status becomes "cancelled", partial results are preserved

---

## 7. API Endpoints

### 7.1 Watchlist Management

```
GET    /api/watchlist/                    → List watched accounts with "new" status
POST   /api/watchlist/                    → Add account(s) to watchlist
DELETE /api/watchlist/{account_id}        → Remove account from watchlist
PUT    /api/watchlist/{account_id}/sf-name → Update the Salesforce name for an account
```

#### GET /api/watchlist/

Returns all watched accounts with enriched data:

```json
[
  {
    "account_id": "uuid",
    "account_name": "Babyboo",
    "sf_account_name": "Babyboo",
    "has_new_calls": true,
    "health_score": 65,
    "last_analyzed": "2026-03-10T14:00:00Z",
    "last_synced": "2026-03-12T09:00:00Z",
    "transcript_count": 5,
    "drive_call_count": 12,
    "new_call_count": 3,
    "added_at": "2026-03-01T10:00:00Z"
  }
]
```

#### POST /api/watchlist/

```json
{
  "account_ids": ["uuid1", "uuid2"],
  "sf_account_names": {
    "uuid1": "Babyboo Creations Ltd",
    "uuid2": "Priceline.com LLC"
  }
}
```

The `sf_account_names` map is optional. If not provided, defaults to `accounts.account_name` (which works if the SIS name matches the Salesforce name).

#### POST /api/watchlist/add-all

Pre-seeds the watchlist with ALL current SIS accounts. Idempotent — skips already-watched.

#### POST /api/watchlist/import-csv

Upload a CSV file with columns: `account_name` (required), `sf_account_name` (optional).
Matches `account_name` against existing SIS accounts (fuzzy). Returns matched + unmatched lists for confirmation.

#### POST /api/watchlist/tam-list

Upload/update the TAM list (CSV) used for SF name suggestions. Stored in a `tam_accounts` reference table.

### 7.2 Sync Operations

```
POST   /api/sync/start                   → Start a new sync job
GET    /api/sync/status/{job_id}         → Get sync job status (polling fallback)
GET    /api/sync/stream/{job_id}         → SSE stream for real-time progress
POST   /api/sync/{job_id}/cancel         → Cancel an in-progress sync
GET    /api/sync/history                  → List recent sync jobs
```

#### POST /api/sync/start

Starts a bulk sync across all watched accounts.

```json
// Request (all optional — defaults to all watched accounts)
{
  "account_ids": ["uuid1", "uuid2"],  // Optional: subset of watchlist
  "start_date": "2025-01-01",         // Optional: defaults to N8N_DEFAULT_START_DATE
  "skip_n8n": false                    // Optional: skip N8N, just scan Drive + import
}
```

```json
// Response
{
  "job_id": "uuid",
  "status": "running",
  "total_accounts": 15,
  "sse_url": "/api/sync/stream/{job_id}"
}
```

#### GET /api/sync/stream/{job_id}

SSE endpoint following the same pattern as the existing analysis progress SSE.

### 7.3 Account Name Resolution Helper

```
GET /api/sync/suggest-sf-name/{account_id}
```

Tries to guess the Salesforce name from the Drive folder filename. Useful when adding accounts to the watchlist — shows the user what slug name exists in Drive so they can confirm/correct the SF name.

Returns:
```json
{
  "drive_slug": "babyboo",
  "suggested_sf_name": "Babyboo",
  "confidence": "exact_match" | "slug_match" | "unknown"
}
```

---

## 8. Frontend Design

### 8.1 Watchlist Page (`/watchlist`)

New page accessible from the sidebar, positioned between "Upload" and "Settings."

**Layout:**

```
+----------------------------------------------------------+
|  Watchlist                          [+ Add Accounts]      |
|                                     [Sync All]  [History] |
+----------------------------------------------------------+
|                                                           |
|  [Search filter]              [Filter: All | New | ...]   |
|                                                           |
|  +------------------------------------------------------+ |
|  | Account         | Status | Health | Last Sync | Acts  | |
|  +------------------------------------------------------+ |
|  | Babyboo   [NEW] | 3 new  |  65    | 2h ago    | [x]   | |
|  | Priceline [NEW] | 1 new  |  72    | 2h ago    | [x]   | |
|  | Serko           | Up to  |  58    | 2h ago    | [x]   | |
|  |                 | date   |        |           |       | |
|  | Abound          | No     |  --    | Never     | [x]   | |
|  |                 | calls  |        |           |       | |
|  +------------------------------------------------------+ |
|                                                           |
+----------------------------------------------------------+
```

**Columns:**
- **Account**: Name with "NEW" badge if `has_new_calls`; links to deal detail page
- **Status**: "X new calls" or "Up to date" or "No calls" or "Never synced"
- **Health**: Latest health score (or "--" if never analyzed)
- **Last Sync**: Time since last sync job that included this account
- **Actions**: Remove from watchlist (X), navigate to detail

**Add Accounts Dialog:**
- Shows all SIS accounts not already on watchlist
- Search/filter by name
- For each account, a field to confirm/edit the Salesforce name
- Multi-select + Add button

### 8.2 Sync Progress Modal

When "Sync All" is clicked, a modal/drawer appears showing real-time progress:

```
+------------------------------------------+
|  Syncing 15 accounts...        [Cancel]   |
+------------------------------------------+
|                                           |
|  Phase 1: Extracting from Gong (8/15)    |
|  [=========>            ] 53%             |
|                                           |
|  v Babyboo     - 7 calls found           |
|  v Priceline   - 3 calls found           |
|  v Serko       - No calls found          |
|  > Abound      - Calling N8N...          |
|  o Uphold      - Waiting                 |
|  ...                                     |
|                                           |
|  Phase 2: Waiting for Drive sync (45s)   |
|  [===========>          ]                |
|                                           |
|  Phase 3: Importing new calls (0/15)     |
|  [ Not started ]                         |
|                                           |
+------------------------------------------+
```

### 8.3 "New" Badge Integration

The "NEW" badge should appear **everywhere**:
1. **Watchlist page**: Primary location, next to account name
2. **Sidebar nav**: A dot indicator on the "Watchlist" nav item if ANY watched account has new data
3. **Pipeline/accounts list**: "NEW" badge next to account name in the main accounts table
4. **Deal detail page**: Badge in the account header when viewing an account with new calls

### 8.4 Account List Management

The watchlist supports three ways to add accounts:

1. **Single account**: Type or select an account name, confirm SF name, add
2. **CSV import**: Upload a CSV file with account names (and optionally SF names). Columns: `account_name` (required), `sf_account_name` (optional). CSV is matched against existing SIS accounts — unmatched names are shown as warnings.
3. **Pre-seed**: On first setup, offer a "Add All Current Accounts" button that adds all existing SIS accounts to the watchlist. The 66 current accounts should be pre-seeded.

**TAM List Integration:**
- User can upload a TAM list (CSV) as a reference for SF name suggestions
- When adding an account to the watchlist, if the SF name doesn't match, fuzzy-match against the TAM list and suggest the closest match
- TAM list is stored as a config/reference table, not per-sync

---

## 9. Edge Cases and Error Handling

### 9.1 N8N Account Name Mismatch

**Problem:** N8N requires the EXACT Salesforce name. If the stored `sf_account_name` is wrong, N8N returns 0 calls or an error.

**Solution:**
- When adding to watchlist, show the Drive slug name alongside the SF name field
- If N8N consistently returns 0 calls for an account that has calls in Drive, surface a warning
- User can update the SF name via the watchlist UI

### 9.2 Drive Sync Delay

**Problem:** After N8N creates files in Google Drive, Drive for Desktop takes time to sync them locally. Research shows typical sync is 1s–2min, averaging ~45s. No programmatic API to detect sync completion.

**Solution — Poll-based detection:**
- After all N8N calls complete, poll the local Drive folder every 10 seconds for up to 3 minutes
- "Stabilized" = same file count + same total file size for 2 consecutive checks (20s of stability)
- If stabilized before 3 min, proceed immediately (saves wait time)
- If 3 min expires without stabilization, proceed anyway with a warning
- If scan finds 0 new files but N8N reported success, show a "Files may still be syncing" message
- User can re-run just the "Scan + Import" phase (via `skip_n8n: true`) to pick up late-arriving files
- Progress widget shows real-time countdown + file count changes during the wait

### 9.3 Duplicate Google Drive Files

**Problem:** Drive for Desktop creates `(1)` duplicates during sync conflicts.

**Solution:** Already handled — `_is_gdrive_duplicate()` in `gdrive_service.py` filters these out. No change needed.

### 9.4 Concurrent Syncs

**Problem:** User clicks "Sync" while a sync is already running.

**Solution:**
- Check for any running sync job before starting a new one
- If running, return 409 Conflict with the existing job_id
- Frontend shows "Sync already in progress" and connects to the existing SSE stream

### 9.5 Very Large Drive Folder (2,970+ files)

**Problem:** Scanning 2,970+ files for each of 50 accounts could be slow.

**Solution:**
- The current `_get_meta_files()` already does a single `glob("*.json")` and filters in memory
- For 50 accounts, we scan once and group by account — not 50 separate scans
- The orchestrator should call `_group_by_account()` once, then look up each watched account in the result dict — O(1) per account after the initial O(n) scan

### 9.6 Account Exists in SIS but Not in Drive

**Problem:** A watched account has no files in the Drive folder (maybe calls were imported manually, or the Drive slug doesn't match).

**Solution:**
- During import phase, if no Drive files are found for an account, mark import_status as "skipped"
- Don't treat this as an error — the account may legitimately have no recent calls
- If N8N reported calls but Drive has none, surface a "Files may still be syncing" warning

### 9.7 N8N Timeout with Actual Success

**Problem:** N8N times out (>5 min) but actually completes the extraction. Files appear in Drive minutes later.

**Solution:**
- Log timeout as "timed_out" (not "failed")
- Still scan Drive after the sync delay — any files that arrived will be picked up
- Show the account as "Timed out — checking Drive anyway" in the UI
- The "New" tag logic is based on Drive contents, not N8N responses, so this is inherently self-healing

### 9.8 API Call Limit (50 calls per N8N request)

**Problem:** Some accounts may have >50 calls in the date range.

**Solution:**
- N8N handles this internally (processes up to 50 calls per request)
- For accounts with many calls, the initial sync will get the 50 most recent
- Subsequent syncs with a narrower date range will catch fewer calls
- For the extended POC, 50 calls is more than enough (our analysis only uses 5)

---

## 10. Data Flow Diagram

```
+-------------------+
| User adds account |
| to watchlist      |
| (with SF name)    |
+--------+----------+
         |
         v
+-------------------+
| watchlist_accounts|
| table             |
+--------+----------+
         |
         | User clicks "Sync All"
         v
+-------------------+
| sync_jobs table   |---> SSE stream to frontend
| (status: running) |
+--------+----------+
         |
         v (for each account, sequentially)
+-------------------+
| N8N Webhook POST  | ----> Gong API ----> Google Drive (cloud)
| {accountName,     |
|  startDate}       |
+--------+----------+
         |
         | (15s delay between accounts)
         | (90s total wait after last call)
         v
+-------------------+
| Local Drive folder| <---- Drive for Desktop auto-sync
| scan + group by   |
| account           |
+--------+----------+
         |
         v (for each account)
+-------------------+
| Cross-reference   |
| with transcripts  |
| table (dedup)     |
+--------+----------+
         |
         v
+-------------------+
| gdrive_service    |
| .upload_calls_    |
| to_db()           |
+--------+----------+
         |
         v
+-------------------+
| Compute "new" tag |
| Update accounts   |
| .has_new_calls    |
+-------------------+
```

---

## 11. Security Considerations

1. **N8N webhook URL is a secret.** It contains an embedded token. Store in `.env`, never expose to the frontend.
2. **No user input reaches N8N unsanitized.** The `sf_account_name` is stored at watchlist-add time and validated. The start/end dates are hardcoded or server-controlled.
3. **File system access.** The Drive folder path is server-configured via `GOOGLE_DRIVE_TRANSCRIPTS_PATH`. No user-supplied paths reach the filesystem.
4. **Auth required.** All new endpoints require JWT auth via `Depends(get_current_user)`.
5. **Rate limiting.** The 15-second inter-request delay and concurrent-sync check prevent abuse of the N8N webhook.

---

## 12. Testing Strategy

### Unit Tests
- N8N client: mock HTTP responses (success, error, timeout), verify classification logic
- "New" tag logic: test all conditions (no transcripts, newer calls, no newer calls, no analysis run)
- Sync orchestrator: mock N8N client + Drive scanner, verify state machine transitions

### Integration Tests
- Full sync flow with mocked N8N but real Drive folder scan
- Dedup: run sync twice, verify no duplicate imports

### Manual Testing
- Trigger sync with known accounts that have calls in Gong
- Verify files appear in Drive
- Verify "New" tags appear and clear after analysis

---

## 13. Decisions (Resolved 2026-03-12)

1. **Salesforce name source:** Manual entry. User provides a TAM list (CSV) for fuzzy-match suggestions when adding accounts. Drive folder slug also shown as a hint.

2. **Drive sync delay:** Poll-based detection — poll every 10s for up to 3 min, stabilize on 2 consecutive same-count checks. No fixed wait.

3. **Watchlist scope:** Global (shared) for POC. Confirmed.

4. **Sync frequency:** Manual trigger only. No scheduled cron for now.

5. **"New" badge placement:** Everywhere — watchlist, sidebar dot, pipeline/accounts list, deal detail page.

6. **Maximum watchlist size:** No cap. Progress widget keeps user informed during long syncs.

### Additional Requirements (added 2026-03-12):

7. **All calls since Jan 1, 2025** — Every sync requests the full range from 2025-01-01 to today. Dedup handles the overlap.

8. **Account list management** — Three input methods: single account, CSV import, "Add All" pre-seed. All 66 current SIS accounts should be pre-seeded on first use.

9. **N8N is one-account-at-a-time** — Sequential processing with 15s delay. Progress widget shows per-account status with detailed progress.

10. **Detailed progress widget** — Must show: current phase, per-account status (calling/success/error), file counts, Drive sync polling status with file count changes, import progress. Cancel button available throughout.

11. **N8N failure indication** — N8N is flaky. UI must clearly distinguish: success, no calls found, error, timeout. Errors should not block other accounts. "Fire and verify" approach — always check Drive regardless of N8N response.

---

## 14. Implementation Plan

See companion document: `docs/plans/2026-03-12-automated-gong-sync-plan.md`

7 phases, estimated 5-7 working sessions. Phases 2 and 3 can run in parallel.

---

## 15. Existing Code Reuse Map

This feature intentionally reuses as much existing infrastructure as possible:

| Existing Code | Reused For |
|---------------|------------|
| `gdrive_service._get_meta_files()` | Scanning Drive folder for files |
| `gdrive_service._group_by_account()` | Grouping files by account (single scan) |
| `gdrive_service._is_gdrive_duplicate()` | Filtering out Drive `(1)` duplicates |
| `gdrive_service.download_and_parse_calls()` | Parsing Gong JSON files |
| `gdrive_service.upload_calls_to_db()` | Importing calls with dedup |
| `transcript_service.transcript_exists()` | Call-level dedup via `gong_call_id` |
| `transcript_service.normalize_active_transcripts()` | Keeping only 5 most recent active |
| `progress_store.py` pattern | Template for `sync_progress_store.py` |
| `sse.py` pattern | Template for sync SSE endpoint |
| `batch_store.py` pattern | Template for multi-account progress tracking |
| `account_service.list_accounts()` | Populating watchlist enrichment data |

### What's genuinely new:
1. **N8N HTTP client** — no existing external webhook integration exists in SIS
2. **Sync orchestrator** — multi-phase async background task with progress tracking
3. **Watchlist concept** — first user-managed entity beyond accounts/transcripts
4. **`has_new_calls` flag** — first denormalized "freshness" indicator on accounts

---

## 16. Stale Sync Job Recovery

**Problem:** If the backend crashes or restarts during an active sync, the sync job remains in `status=running` in the DB. This blocks future syncs (concurrent sync guard).

**Solution:** On backend startup (or on `POST /api/sync/start`), check for stale jobs:

```python
# In start_sync or app startup
with get_session() as session:
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    stale_jobs = session.query(SyncJob).filter(
        SyncJob.status.in_(["pending", "running", "scanning", "importing"]),
        SyncJob.started_at < stale_cutoff,
    ).all()
    for job in stale_jobs:
        job.status = "failed"
        job.error_log = json.dumps(["Sync job timed out — likely backend restart"])
        logger.warning("Marking stale sync job %s as failed", job.id)
```

This is simpler than a startup hook and handles the common case cleanly.
