# Recording Browser Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the tabbed upload page with a 3-panel recording browser that shows drive recordings with DB comparison, deal config, and a queue for batch analysis.

**Architecture:** New backend endpoint `POST /api/gdrive/calls-status` cross-references drive folder calls against the Transcript table to return per-call status (new/active/imported). Enhanced `list_account_folders()` returns `new_count` and `db_account_id`. Frontend is a full rewrite of `upload/page.tsx` with 3-panel layout + modals for Local Folder and Manual Upload.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js 16, React 19, Tailwind CSS 4, shadcn/ui components

**Design Doc:** `docs/plans/2026-03-04-recording-browser-design.md`

---

## Task 1: Add `buying_culture` to BatchItemRequest schema

The batch schema is missing `buying_culture` — it's used in `_run_batch_item` (line 106 of `sis/api/routes/analyses.py`) but never declared. Fix this first since later tasks depend on it.

**Files:**
- Modify: `sis/api/schemas/analyses.py:94-105`
- Modify: `frontend/src/lib/api-types.ts:416-426`

**Step 1: Add field to Pydantic schema**

In `sis/api/schemas/analyses.py`, add `buying_culture` to `BatchItemRequest`:

```python
class BatchItemRequest(BaseModel):
    """Single account in a batch analysis request."""
    account_name: str
    drive_path: str
    max_calls: int = 5
    deal_type: Optional[str] = None
    cp_estimate: Optional[float] = None
    owner_id: Optional[str] = None
    buying_culture: str = "direct"
    sf_stage: Optional[int] = None
    sf_forecast_category: Optional[str] = None
    sf_close_quarter: Optional[str] = None
```

**Step 2: Add field to TypeScript type**

In `frontend/src/lib/api-types.ts`, add to `BatchItemRequest`:

```typescript
export interface BatchItemRequest {
  account_name: string;
  drive_path: string;
  max_calls: number;
  deal_type?: string;
  cp_estimate?: number;
  owner_id?: string;
  buying_culture?: string;
  sf_stage?: number;
  sf_forecast_category?: string;
  sf_close_quarter?: string;
}
```

**Step 3: Commit**

```bash
git add sis/api/schemas/analyses.py frontend/src/lib/api-types.ts
git commit -m "fix: add missing buying_culture to BatchItemRequest schema"
```

---

## Task 2: Backend — `get_all_calls_with_status()` service function

New function in `gdrive_service.py` that returns ALL calls for one account with their DB status (new/active/imported).

**Files:**
- Modify: `sis/services/gdrive_service.py` (add function after `get_recent_calls_info`, ~line 269)
- Create: `tests/test_gdrive_calls_status.py`

**Step 1: Write the failing test**

Create `tests/test_gdrive_calls_status.py`:

```python
"""Tests for get_all_calls_with_status()."""

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from sis.services.gdrive_service import get_all_calls_with_status


def _write_call(tmp_path: Path, date: str, call_id: str, title: str) -> None:
    """Write a pair of metadata + transcript JSON files."""
    meta = {
        "metaData": {
            "id": call_id,
            "title": title,
            "date": date,
            "started": f"{date}T10:00:00Z",
            "duration": 1800,
            "language": "English",
            "direction": "Conference",
            "system": "Zoom",
            "scope": "External",
        },
        "parties": [],
        "content": {"trackers": [], "topics": []},
    }
    safe_title = title.replace(" ", "_")
    meta_file = tmp_path / f"gong_call_{date}_001_{safe_title}.json"
    meta_file.write_text(json.dumps(meta))
    transcript_file = tmp_path / f"gong_call_{date}_001_{safe_title}_transcript.json"
    transcript_file.write_text(json.dumps([]))


class TestGetAllCallsWithStatus:
    """Tests for drive call listing with DB comparison."""

    def test_all_new_when_no_db_account(self, tmp_path):
        """All calls are 'new' when account doesn't exist in DB."""
        _write_call(tmp_path, "2026-03-01", "call_1", "QBR")
        _write_call(tmp_path, "2026-02-15", "call_2", "Discovery")

        result = get_all_calls_with_status(str(tmp_path), db_account_id=None)

        assert len(result["calls"]) == 2
        assert all(c["status"] == "new" for c in result["calls"])
        assert result["calls"][0]["date"] == "2026-03-01"  # sorted desc

    def test_marks_active_and_imported(self, tmp_path):
        """Calls already in DB marked as active or imported."""
        _write_call(tmp_path, "2026-03-01", "call_1", "QBR")
        _write_call(tmp_path, "2026-02-15", "call_2", "Discovery")
        _write_call(tmp_path, "2026-01-10", "call_3", "Kickoff")

        fake_account_id = str(uuid.uuid4())

        # Mock transcript_service functions
        with patch("sis.services.gdrive_service.get_transcripts_by_gong_ids") as mock_lookup:
            mock_lookup.return_value = {
                "call_2": {"is_active": True},
                "call_3": {"is_active": False},
            }
            result = get_all_calls_with_status(
                str(tmp_path), db_account_id=fake_account_id
            )

        assert result["calls"][0]["status"] == "new"       # call_1
        assert result["calls"][1]["status"] == "active"     # call_2
        assert result["calls"][2]["status"] == "imported"   # call_3

    def test_returns_gong_call_id(self, tmp_path):
        """Each call includes its gong_call_id."""
        _write_call(tmp_path, "2026-03-01", "call_abc", "QBR")

        result = get_all_calls_with_status(str(tmp_path), db_account_id=None)
        assert result["calls"][0]["gong_call_id"] == "call_abc"

    def test_empty_folder(self, tmp_path):
        """Empty folder returns empty calls list."""
        result = get_all_calls_with_status(str(tmp_path), db_account_id=None)
        assert result["calls"] == []

    def test_flat_layout(self, tmp_path):
        """Flat layout files filtered by account_name."""
        # Write flat-format files
        meta = {
            "metaData": {
                "id": "flat_1", "title": "Flat Call", "date": "2026-03-01",
                "started": "2026-03-01T10:00:00Z", "duration": 900,
                "language": "English", "direction": "Conference",
                "system": "Zoom", "scope": "External",
            },
            "parties": [], "content": {"trackers": [], "topics": []},
        }
        (tmp_path / "gong_call-Acme-2026-03-01-Flat_Call.json").write_text(json.dumps(meta))
        (tmp_path / "gong_call-Acme-2026-03-01-Flat_Call_transcript.json").write_text("[]")
        # Unrelated account
        (tmp_path / "gong_call-Beta-2026-03-01-Other.json").write_text(json.dumps(meta))

        result = get_all_calls_with_status(
            str(tmp_path), db_account_id=None, account_name="Acme"
        )
        assert len(result["calls"]) == 1
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
.venv/bin/python -m pytest tests/test_gdrive_calls_status.py -v
```

Expected: FAIL — `ImportError: cannot import name 'get_all_calls_with_status'`

**Step 3: Add `get_transcripts_by_gong_ids()` helper to transcript_service**

In `sis/services/transcript_service.py`, add after `transcript_exists()` (~line 137):

```python
def get_transcripts_by_gong_ids(account_id: str, gong_call_ids: list[str]) -> dict[str, dict]:
    """Look up transcripts by gong_call_id for an account.

    Returns:
        Dict mapping gong_call_id → {"is_active": bool} for each found transcript.
    """
    if not gong_call_ids:
        return {}
    with get_session() as session:
        rows = (
            session.query(Transcript.gong_call_id, Transcript.is_active)
            .filter(
                Transcript.account_id == account_id,
                Transcript.gong_call_id.in_(gong_call_ids),
            )
            .all()
        )
        return {
            row.gong_call_id: {"is_active": bool(row.is_active)}
            for row in rows
        }
```

**Step 4: Implement `get_all_calls_with_status()` in gdrive_service**

In `sis/services/gdrive_service.py`, add after `get_recent_calls_info()` (~line 269):

```python
def get_all_calls_with_status(
    account_path: str,
    db_account_id: str | None,
    account_name: str | None = None,
) -> dict:
    """Get ALL calls for an account with their DB import status.

    Cross-references drive folder contents against the Transcript table.

    Args:
        account_path: Path to account folder (nested) or root folder (flat).
        db_account_id: SIS account UUID, or None if account not in DB.
        account_name: Required for flat layout to filter by account.

    Returns:
        {
            "calls": [
                {
                    "date": "2026-03-01",
                    "title": "QBR Review",
                    "gong_call_id": "abc123",
                    "has_transcript": true,
                    "status": "new" | "active" | "imported"
                },
                ...
            ]
        }
    """
    import json as _json

    account_dir = Path(account_path)
    if not account_dir.exists():
        return {"calls": []}

    all_json = list(account_dir.glob("*.json"))

    # Filter by account name if provided (flat layout)
    if account_name:
        all_json = [
            f for f in all_json
            if _extract_account_name(f.name) == account_name
            or _extract_account_name(
                f.name.replace("-transcript.json", ".json").replace("_transcript.json", ".json")
            ) == account_name
        ]

    meta_files = [
        f for f in all_json
        if not _is_transcript(f.name) and not _is_gdrive_duplicate(f.name)
    ]
    transcript_names = {f.name for f in all_json if _is_transcript(f.name)}

    # Build call list with gong_call_id from metadata JSON
    calls = []
    for mf in meta_files:
        date_match = _DATE_RE.search(mf.name)
        call_date = date_match.group(1) if date_match else "0000-00-00"

        # Read gong_call_id from metadata file
        gong_call_id = None
        try:
            with open(mf) as fh:
                meta_data = _json.load(fh)
            gong_call_id = meta_data.get("metaData", {}).get("id")
        except Exception:
            logger.warning("Failed to read metadata from %s", mf.name)

        # Check for companion transcript file
        stem = mf.stem
        has_transcript = any(
            t.startswith(f"{stem}-transcript") or t.startswith(f"{stem}_transcript")
            for t in transcript_names
        )

        # Title extraction (same logic as get_recent_calls_info)
        title = mf.name
        title_match = re.match(
            r"gong_call-.+?-\d{4}-\d{2}-\d{2}-(.*?)\.json$", title
        )
        if not title_match:
            title_match = re.match(
                r"gong_call_\d{4}-\d{2}-\d{2}_\d+_(.*?)\.json$", title
            )
        if title_match:
            title = title_match.group(1).replace("_", " ").replace("-", " ")

        calls.append({
            "date": call_date,
            "title": title,
            "gong_call_id": gong_call_id,
            "has_transcript": has_transcript,
            "status": "new",  # default, will be updated below
        })

    # Cross-reference with DB if account exists
    if db_account_id:
        gong_ids = [c["gong_call_id"] for c in calls if c["gong_call_id"]]
        if gong_ids:
            from sis.services.transcript_service import get_transcripts_by_gong_ids
            db_lookup = get_transcripts_by_gong_ids(db_account_id, gong_ids)
            for call in calls:
                if call["gong_call_id"] in db_lookup:
                    info = db_lookup[call["gong_call_id"]]
                    call["status"] = "active" if info["is_active"] else "imported"

    calls.sort(key=lambda c: c["date"], reverse=True)
    return {"calls": calls}
```

**Step 5: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_gdrive_calls_status.py -v
```

Expected: All 5 tests PASS.

**Step 6: Commit**

```bash
git add sis/services/gdrive_service.py sis/services/transcript_service.py tests/test_gdrive_calls_status.py
git commit -m "feat: add get_all_calls_with_status() for recording browser DB comparison"
```

---

## Task 3: Backend — Enrich `list_account_folders()` with DB status

Modify `list_account_folders()` to return `new_count`, `db_account_id`, and `has_active_analysis` per account.

**Files:**
- Modify: `sis/services/gdrive_service.py:139-197` (list_account_folders + helpers)
- Modify: `tests/test_gdrive_service.py` (update TestListAccountFolders)

**Step 1: Write failing test**

Add to `tests/test_gdrive_service.py`, inside `TestListAccountFolders`:

```python
def test_enriched_fields_present(self, drive_root):
    """Each account dict includes new_count, db_account_id, has_active_analysis."""
    accounts = gdrive_service.list_account_folders(str(drive_root))
    for acct in accounts:
        assert "new_count" in acct
        assert "db_account_id" in acct
        assert "has_active_analysis" in acct
```

**Step 2: Run to verify failure**

```bash
.venv/bin/python -m pytest tests/test_gdrive_service.py::TestListAccountFolders::test_enriched_fields_present -v
```

Expected: FAIL — KeyError on `new_count`.

**Step 3: Implement enrichment**

Modify `list_account_folders()` in `sis/services/gdrive_service.py`. After building the basic account list (line ~158), add DB enrichment:

```python
def list_account_folders(drive_path: str) -> list[dict]:
    """List all accounts in the local Drive folder with DB status enrichment.

    Returns:
        List of dicts: [{
            "name": str, "path": str, "call_count": int,
            "new_count": int, "db_account_id": str|None, "has_active_analysis": bool
        }] sorted with accounts having new calls first, then alphabetically.
    """
    root = Path(drive_path).expanduser()
    try:
        root = root.resolve(strict=True)
    except (OSError, FileNotFoundError):
        raise FileNotFoundError(f"Drive path not found: {root}")

    try:
        if _is_flat_layout(root):
            accounts = _list_accounts_flat(root)
        else:
            accounts = _list_accounts_nested(root)
    except PermissionError:
        raise PermissionError(
            f"Permission denied reading {root}. "
            "On macOS, grant Full Disk Access to your terminal app: "
            "System Settings → Privacy & Security → Full Disk Access."
        )

    # Enrich with DB status
    _enrich_accounts_with_db_status(accounts, root)

    # Sort: accounts with new calls first, then alphabetically
    accounts.sort(key=lambda a: (a["new_count"] == 0, a["name"].lower()))
    return accounts


def _enrich_accounts_with_db_status(accounts: list[dict], root: Path) -> None:
    """Add new_count, db_account_id, has_active_analysis to each account dict."""
    from sis.services.account_service import list_accounts as db_list_accounts

    # Build a lookup of DB accounts by lowercase name
    try:
        db_accounts = db_list_accounts()
    except Exception:
        # If DB is unavailable, set defaults
        for acct in accounts:
            acct["new_count"] = acct["call_count"]
            acct["db_account_id"] = None
            acct["has_active_analysis"] = False
        return

    db_by_name: dict[str, dict] = {}
    for dba in db_accounts:
        db_by_name[dba["account_name"].lower()] = dba

    for acct in accounts:
        db_match = db_by_name.get(acct["name"].lower())
        if not db_match:
            acct["new_count"] = acct["call_count"]
            acct["db_account_id"] = None
            acct["has_active_analysis"] = False
            continue

        acct["db_account_id"] = db_match["id"]
        acct["has_active_analysis"] = db_match.get("health_score") is not None

        # Count new calls by checking gong_call_ids against DB
        from sis.services.transcript_service import get_transcripts_by_gong_ids
        import json as _json

        # Read gong_call_ids from metadata files in this account's folder
        account_dir = Path(acct["path"])
        meta_files = _get_meta_files(account_dir, account_name=acct["name"] if _is_flat_layout(root) else None)
        gong_ids = []
        for mf in meta_files:
            try:
                with open(mf) as fh:
                    data = _json.load(fh)
                gid = data.get("metaData", {}).get("id")
                if gid:
                    gong_ids.append(gid)
            except Exception:
                pass

        if gong_ids:
            existing = get_transcripts_by_gong_ids(db_match["id"], gong_ids)
            acct["new_count"] = len(gong_ids) - len(existing)
        else:
            acct["new_count"] = acct["call_count"]
```

**Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_gdrive_service.py -v
```

Expected: All tests PASS (existing tests still pass because `new_count` etc. are additive fields).

**Step 5: Commit**

```bash
git add sis/services/gdrive_service.py tests/test_gdrive_service.py
git commit -m "feat: enrich list_account_folders with DB status (new_count, db_account_id)"
```

---

## Task 4: Backend — New `POST /api/gdrive/calls-status` endpoint

Expose the `get_all_calls_with_status()` function via a new API route.

**Files:**
- Modify: `sis/api/routes/gdrive.py:68-74` (add new route after existing `/calls`)

**Step 1: Add Pydantic schema and route**

In `sis/api/routes/gdrive.py`, add after the existing `/calls` route (~line 74):

```python
class CallsStatusRequest(BaseModel):
    account_path: str
    account_name: Optional[str] = None
    db_account_id: Optional[str] = None


@router.post("/calls-status")
def get_calls_with_status(body: CallsStatusRequest, user: dict = Depends(get_current_user)):
    """List ALL calls for an account with their DB import status."""
    result = gdrive_service.get_all_calls_with_status(
        body.account_path,
        db_account_id=body.db_account_id,
        account_name=body.account_name,
    )
    return result
```

**Step 2: Add API client method**

In `frontend/src/lib/api.ts`, add to the `gdrive` section:

```typescript
callsStatus: (accountPath: string, accountName?: string, dbAccountId?: string) =>
  post<{ calls: EnrichedCall[] }>('/api/gdrive/calls-status', {
    account_path: accountPath,
    account_name: accountName,
    db_account_id: dbAccountId,
  }),
```

**Step 3: Add TypeScript types**

In `frontend/src/lib/api-types.ts`, add near the existing GDrive types:

```typescript
export interface EnrichedDriveAccount {
  name: string;
  path: string;
  call_count: number;
  new_count: number;
  db_account_id: string | null;
  has_active_analysis: boolean;
}

export interface EnrichedCall {
  date: string;
  title: string;
  gong_call_id: string | null;
  has_transcript: boolean;
  status: 'new' | 'active' | 'imported';
}
```

**Step 4: Update `listAccounts` return type**

In `frontend/src/lib/api.ts`, update the `listAccounts` method to use the enriched type:

```typescript
listAccounts: (path: string) =>
  post<EnrichedDriveAccount[]>('/api/gdrive/accounts', { path }),
```

**Step 5: Commit**

```bash
git add sis/api/routes/gdrive.py frontend/src/lib/api.ts frontend/src/lib/api-types.ts
git commit -m "feat: add /api/gdrive/calls-status endpoint for recording browser"
```

---

## Task 5: Frontend — Recording Browser page structure

Replace the entire `upload/page.tsx` with the 3-panel recording browser layout. This task sets up the skeleton — panels, state, drive path scanning. No call detail or queue logic yet.

**Files:**
- Rewrite: `frontend/src/app/upload/page.tsx`

**Step 1: Write the page skeleton**

Rewrite `frontend/src/app/upload/page.tsx` with the 3-panel layout:

```tsx
'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  Upload, FolderOpen, FileText, HardDrive, Loader2,
  Search, ChevronRight, X, Play, Trash2, Eye, Check, Info,
} from 'lucide-react';
import { useICUsers } from '@/lib/hooks/use-admin';
import { api } from '@/lib/api';
import type {
  EnrichedDriveAccount, EnrichedCall, ICUser,
} from '@/lib/api-types';
import { BatchProgressView } from '@/components/batch-progress-view';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

// ── Helpers ───────────────────────────────────────────────────────────

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

const DEAL_TYPES = [
  'New Logo',
  'Expansion - Upsell',
  'Expansion - Cross Sell',
  'Expansion - Both',
  'Renewal',
];

const DEAL_TYPE_ABBREV: Record<string, string> = {
  'New Logo': 'NL',
  'Expansion - Upsell': 'EX-U',
  'Expansion - Cross Sell': 'EX-X',
  'Expansion - Both': 'EX-B',
  'Renewal': 'RN',
};

// ── Types ─────────────────────────────────────────────────────────────

interface DealConfig {
  dealType: string;
  aeOwner: string;
  ownerId: string;
  buyingCulture: string;
  sfStage: string;
  sfForecast: string;
  closeQuarter: string;
  cpEstimate: string;
}

interface QueueItem {
  accountName: string;
  accountPath: string;
  dbAccountId: string | null;
  selectedCallIds: string[];
  newCallCount: number;
  dealConfig: DealConfig;
}

const EMPTY_CONFIG: DealConfig = {
  dealType: '',
  aeOwner: '',
  ownerId: '',
  buyingCulture: '',
  sfStage: '',
  sfForecast: '',
  closeQuarter: '',
  cpEstimate: '',
};

// ── Page ──────────────────────────────────────────────────────────────

export default function UploadPage() {
  // Drive scan state
  const [drivePath, setDrivePath] = useState('');
  const [scanning, setScanning] = useState(false);
  const [driveAccounts, setDriveAccounts] = useState<EnrichedDriveAccount[]>([]);
  const [scanError, setScanError] = useState('');

  // Selection state
  const [selectedAccountName, setSelectedAccountName] = useState<string | null>(null);
  const [accountCalls, setAccountCalls] = useState<EnrichedCall[]>([]);
  const [loadingCalls, setLoadingCalls] = useState(false);
  const [selectedCallIds, setSelectedCallIds] = useState<Set<string>>(new Set());
  const [dealConfig, setDealConfig] = useState<DealConfig>(EMPTY_CONFIG);

  // Queue state
  const [queue, setQueue] = useState<QueueItem[]>([]);

  // Batch state
  const [batchId, setBatchId] = useState<string | null>(null);

  // Search filter
  const [accountSearch, setAccountSearch] = useState('');

  // IC users for AE Owner dropdown
  const { data: icUsers = [] } = useICUsers();

  // Modal state
  const [showLocalModal, setShowLocalModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);

  // Refresh key for PastUploadsTable
  const [refreshKey, setRefreshKey] = useState(0);

  // Auto-load drive path from config
  useEffect(() => {
    api.gdrive.config().then((cfg) => {
      if (cfg.path) {
        setDrivePath(cfg.path);
      }
    });
  }, []);

  // ── Drive scanning ───────────────────────────────────────────────

  const handleScan = useCallback(async () => {
    if (!drivePath.trim()) return;
    setScanning(true);
    setScanError('');
    setSelectedAccountName(null);
    setAccountCalls([]);
    try {
      const validation = await api.gdrive.validate(drivePath);
      if (!validation.is_valid) {
        setScanError(validation.message);
        setDriveAccounts([]);
        return;
      }
      const accounts = await api.gdrive.listAccounts(drivePath);
      setDriveAccounts(accounts as EnrichedDriveAccount[]);
    } catch (e: unknown) {
      setScanError(e instanceof Error ? e.message : 'Failed to scan drive folder');
    } finally {
      setScanning(false);
    }
  }, [drivePath]);

  // ── Account selection ────────────────────────────────────────────

  const selectedAccount = useMemo(
    () => driveAccounts.find((a) => a.name === selectedAccountName) ?? null,
    [driveAccounts, selectedAccountName],
  );

  const handleSelectAccount = useCallback(async (acct: EnrichedDriveAccount) => {
    setSelectedAccountName(acct.name);
    setLoadingCalls(true);
    setSelectedCallIds(new Set());
    setDealConfig(EMPTY_CONFIG);

    try {
      const result = await api.gdrive.callsStatus(
        acct.path, acct.name, acct.db_account_id ?? undefined,
      );
      setAccountCalls(result.calls);
      // Auto-select all new calls
      const newIds = new Set(
        result.calls
          .filter((c) => c.status === 'new' && c.gong_call_id)
          .map((c) => c.gong_call_id!),
      );
      setSelectedCallIds(newIds);

      // Auto-fill deal config from existing account if it exists in DB
      if (acct.db_account_id) {
        try {
          const accountData = await api.accounts.get(acct.db_account_id);
          setDealConfig((prev) => ({
            ...prev,
            dealType: accountData.deal_type ?? '',
            aeOwner: accountData.ae_owner ?? '',
            ownerId: accountData.owner_id ?? '',
            buyingCulture: accountData.buying_culture ?? '',
            // Pipeline-position fields left empty — user must update
          }));
        } catch {
          // Account might not be accessible, ignore
        }
      }
    } catch {
      setAccountCalls([]);
    } finally {
      setLoadingCalls(false);
    }
  }, []);

  // ── Call selection toggle ────────────────────────────────────────

  const toggleCall = useCallback((gongCallId: string) => {
    setSelectedCallIds((prev) => {
      const next = new Set(prev);
      if (next.has(gongCallId)) next.delete(gongCallId);
      else next.add(gongCallId);
      return next;
    });
  }, []);

  // ── Queue management ─────────────────────────────────────────────

  const queuedAccountNames = useMemo(
    () => new Set(queue.map((q) => q.accountName)),
    [queue],
  );

  const canAddToQueue = useMemo(() => {
    if (selectedCallIds.size === 0) return false;
    if (!dealConfig.dealType || !dealConfig.sfStage || !dealConfig.sfForecast
        || !dealConfig.closeQuarter || !dealConfig.cpEstimate) return false;
    return true;
  }, [selectedCallIds, dealConfig]);

  const handleAddToQueue = useCallback(() => {
    if (!selectedAccount || !canAddToQueue) return;
    const item: QueueItem = {
      accountName: selectedAccount.name,
      accountPath: selectedAccount.path,
      dbAccountId: selectedAccount.db_account_id,
      selectedCallIds: Array.from(selectedCallIds),
      newCallCount: selectedCallIds.size,
      dealConfig: { ...dealConfig },
    };
    setQueue((prev) => [...prev.filter((q) => q.accountName !== item.accountName), item]);
    setSelectedAccountName(null);
    setAccountCalls([]);
    setSelectedCallIds(new Set());
    setDealConfig(EMPTY_CONFIG);
  }, [selectedAccount, selectedCallIds, dealConfig, canAddToQueue]);

  const removeFromQueue = useCallback((accountName: string) => {
    setQueue((prev) => prev.filter((q) => q.accountName !== accountName));
  }, []);

  // ── Run analysis ─────────────────────────────────────────────────

  const handleRunAnalysis = useCallback(async () => {
    if (queue.length === 0) return;
    const items = queue.map((q) => ({
      account_name: q.accountName,
      drive_path: q.accountPath,
      max_calls: q.newCallCount,
      deal_type: q.dealConfig.dealType,
      cp_estimate: q.dealConfig.cpEstimate ? parseFloat(q.dealConfig.cpEstimate) : undefined,
      owner_id: q.dealConfig.ownerId || undefined,
      buying_culture: q.dealConfig.buyingCulture || 'direct',
      sf_stage: q.dealConfig.sfStage ? parseInt(q.dealConfig.sfStage) : undefined,
      sf_forecast_category: q.dealConfig.sfForecast || undefined,
      sf_close_quarter: q.dealConfig.closeQuarter || undefined,
    }));

    try {
      const result = await api.analyses.batch(items);
      setBatchId(result.batch_id);
    } catch (e: unknown) {
      console.error('Batch failed:', e);
    }
  }, [queue]);

  // ── Filtered accounts ────────────────────────────────────────────

  const filteredAccounts = useMemo(() => {
    if (!accountSearch.trim()) return driveAccounts;
    const q = accountSearch.toLowerCase();
    return driveAccounts.filter((a) => a.name.toLowerCase().includes(q));
  }, [driveAccounts, accountSearch]);

  // ── Batch progress view ──────────────────────────────────────────

  if (batchId) {
    return (
      <div className="p-6 max-w-5xl">
        <BatchProgressView
          batchId={batchId}
          onDismiss={() => {
            setBatchId(null);
            setQueue([]);
            setRefreshKey((k) => k + 1);
          }}
        />
      </div>
    );
  }

  // ── Analysis banner text ─────────────────────────────────────────

  const activeCallCount = accountCalls.filter((c) => c.status === 'active').length;
  const newSelected = selectedCallIds.size;
  const totalForAnalysis = Math.min(newSelected + activeCallCount, 5);

  let bannerText = '';
  if (newSelected > 0 && activeCallCount > 0) {
    const fromActive = totalForAnalysis - Math.min(newSelected, 5);
    bannerText = `Importing ${newSelected} new call${newSelected > 1 ? 's' : ''}. Analysis will run on the 5 most recent calls (${Math.min(newSelected, 5)} new + ${fromActive} currently active).`;
  } else if (newSelected > 0) {
    bannerText = `New account. Importing ${newSelected} call${newSelected > 1 ? 's' : ''} for first analysis.`;
  }
  if (newSelected > 5) {
    bannerText = `Importing ${newSelected} new calls. Analysis will use the 5 most recent. Older calls will be stored but inactive.`;
  }

  // ── Render ───────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Recording Browser</h1>
          <p className="text-sm text-muted-foreground">
            Browse recordings, compare with database, queue accounts for analysis.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowLocalModal(true)}>
            <HardDrive className="size-4 mr-1.5" />
            Local Folder
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowManualModal(true)}>
            <FileText className="size-4 mr-1.5" />
            Manual Upload
          </Button>
        </div>
      </div>

      {/* Drive Path Bar */}
      <div className="flex gap-2 mb-4">
        <Input
          placeholder="Google Drive transcripts path..."
          value={drivePath}
          onChange={(e) => setDrivePath(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleScan()}
          className="flex-1 font-mono text-xs"
        />
        <Button onClick={handleScan} disabled={scanning || !drivePath.trim()}>
          {scanning ? <Loader2 className="size-4 animate-spin mr-1.5" /> : <FolderOpen className="size-4 mr-1.5" />}
          Scan
        </Button>
      </div>

      {scanError && (
        <p className="text-sm text-red-400 mb-4">{scanError}</p>
      )}

      {/* 3-Panel Layout */}
      {driveAccounts.length > 0 && (
        <div className="grid grid-cols-[220px_1fr_260px] gap-4 min-h-[600px]">

          {/* Panel 1: Account List */}
          <AccountListPanel
            accounts={filteredAccounts}
            selectedName={selectedAccountName}
            queuedNames={queuedAccountNames}
            search={accountSearch}
            onSearchChange={setAccountSearch}
            onSelect={handleSelectAccount}
          />

          {/* Panel 2: Account Detail */}
          <AccountDetailPanel
            account={selectedAccount}
            calls={accountCalls}
            loadingCalls={loadingCalls}
            selectedCallIds={selectedCallIds}
            onToggleCall={toggleCall}
            dealConfig={dealConfig}
            onDealConfigChange={setDealConfig}
            icUsers={icUsers}
            canAddToQueue={canAddToQueue}
            onAddToQueue={handleAddToQueue}
            bannerText={bannerText}
          />

          {/* Panel 3: Queue */}
          <QueuePanel
            queue={queue}
            onRemove={removeFromQueue}
            onRunAnalysis={handleRunAnalysis}
          />
        </div>
      )}

      {/* Past Uploads Table */}
      <PastUploadsTable refreshKey={refreshKey} />

      {/* Modals for Local Folder and Manual Upload */}
      {showLocalModal && <LocalFolderModal onClose={() => setShowLocalModal(false)} />}
      {showManualModal && <ManualUploadModal onClose={() => setShowManualModal(false)} />}
    </div>
  );
}
```

This is the page skeleton with all state and handlers. The child components (`AccountListPanel`, `AccountDetailPanel`, `QueuePanel`, `PastUploadsTable`, `LocalFolderModal`, `ManualUploadModal`) will be implemented in subsequent tasks.

**Step 2: Commit skeleton (will have compile errors until child components exist)**

Do NOT commit yet — continue to Tasks 6-9 which implement the child components, then commit the whole page together.

---

## Task 6: Frontend — AccountListPanel component

The left panel showing account list with search and new-call badges.

**Files:**
- Part of: `frontend/src/app/upload/page.tsx` (add after the page component)

**Step 1: Implement component**

```tsx
// ── Panel 1: Account List ────────────────────────────────────────────

function AccountListPanel({
  accounts, selectedName, queuedNames, search, onSearchChange, onSelect,
}: {
  accounts: EnrichedDriveAccount[];
  selectedName: string | null;
  queuedNames: Set<string>;
  search: string;
  onSearchChange: (v: string) => void;
  onSelect: (a: EnrichedDriveAccount) => void;
}) {
  return (
    <Card className="flex flex-col overflow-hidden">
      <CardHeader className="pb-2 px-3 pt-3">
        <CardTitle className="text-sm font-medium">Accounts</CardTitle>
        <div className="relative mt-1">
          <Search className="absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <Input
            placeholder="Filter..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-7 h-8 text-xs"
          />
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-0">
        {accounts.map((acct) => {
          const isSelected = acct.name === selectedName;
          const isQueued = queuedNames.has(acct.name);
          return (
            <button
              key={acct.name}
              onClick={() => onSelect(acct)}
              className={`w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm border-l-2 transition-colors hover:bg-accent/5 ${
                isSelected
                  ? 'border-l-accent bg-accent/5'
                  : 'border-l-transparent'
              }`}
            >
              {isQueued && <Check className="size-3.5 text-emerald-400 shrink-0" />}
              <span className="truncate flex-1 font-medium">{acct.name}</span>
              {acct.new_count > 0 ? (
                <Badge variant="outline" className="shrink-0 text-[10px] bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                  {acct.new_count} new
                </Badge>
              ) : (
                <span className="text-[10px] text-muted-foreground shrink-0">Up to date</span>
              )}
              <ChevronRight className="size-3.5 text-muted-foreground shrink-0" />
            </button>
          );
        })}
      </CardContent>
    </Card>
  );
}
```

---

## Task 7: Frontend — AccountDetailPanel component

The middle panel showing calls table, info banner, and deal config form.

**Files:**
- Part of: `frontend/src/app/upload/page.tsx`

**Step 1: Implement component**

```tsx
// ── Panel 2: Account Detail ──────────────────────────────────────────

function AccountDetailPanel({
  account, calls, loadingCalls, selectedCallIds, onToggleCall,
  dealConfig, onDealConfigChange, icUsers, canAddToQueue, onAddToQueue,
  bannerText,
}: {
  account: EnrichedDriveAccount | null;
  calls: EnrichedCall[];
  loadingCalls: boolean;
  selectedCallIds: Set<string>;
  onToggleCall: (id: string) => void;
  dealConfig: DealConfig;
  onDealConfigChange: (c: DealConfig) => void;
  icUsers: ICUser[];
  canAddToQueue: boolean;
  onAddToQueue: () => void;
  bannerText: string;
}) {
  const closeQuarters = useMemo(() => generateCloseQuarters(), []);

  if (!account) {
    return (
      <Card className="flex items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Select an account to view recordings
        </p>
      </Card>
    );
  }

  if (loadingCalls) {
    return (
      <Card className="flex items-center justify-center">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </Card>
    );
  }

  const updateConfig = (field: keyof DealConfig, value: string) =>
    onDealConfigChange({ ...dealConfig, [field]: value });

  return (
    <Card className="flex flex-col overflow-hidden">
      {/* Header */}
      <CardHeader className="pb-2 px-4 pt-3">
        <CardTitle className="text-sm font-medium">
          Calls for: {account.name}
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {calls.length} recording{calls.length !== 1 ? 's' : ''} in drive folder
        </p>
      </CardHeader>

      {/* Info Banner */}
      {bannerText && (
        <div className="mx-4 mb-2 flex items-start gap-2 rounded-md bg-sky-500/10 border border-sky-500/20 px-3 py-2">
          <Info className="size-4 text-sky-400 shrink-0 mt-0.5" />
          <p className="text-xs text-sky-300">{bannerText}</p>
        </div>
      )}

      {/* Calls Table */}
      <div className="flex-1 overflow-y-auto px-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8"></TableHead>
              <TableHead className="text-xs">Date</TableHead>
              <TableHead className="text-xs">Title</TableHead>
              <TableHead className="text-xs w-24">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {calls.map((call, i) => {
              const isNew = call.status === 'new';
              const isChecked = call.gong_call_id ? selectedCallIds.has(call.gong_call_id) : false;
              return (
                <TableRow key={call.gong_call_id ?? i} className="h-9">
                  <TableCell className="pr-0">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={!isNew}
                      onChange={() => call.gong_call_id && onToggleCall(call.gong_call_id)}
                      className="rounded border-border accent-emerald-500"
                    />
                  </TableCell>
                  <TableCell className="text-xs font-mono whitespace-nowrap">{call.date}</TableCell>
                  <TableCell className="text-xs whitespace-normal">{call.title}</TableCell>
                  <TableCell>
                    <CallStatusBadge status={call.status} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Deal Config */}
      <div className="border-t border-border px-4 py-3 space-y-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Deal Configuration</p>

        {/* Auto-filled row */}
        <div className="grid grid-cols-3 gap-2">
          <ConfigSelect label="Deal Type" value={dealConfig.dealType}
            onChange={(v) => updateConfig('dealType', v)}
            options={DEAL_TYPES.map((d) => ({ value: d, label: d }))}
            required
          />
          <ConfigSelect label="AE Owner" value={dealConfig.ownerId}
            onChange={(v) => {
              const user = icUsers.find((u) => u.id === v);
              updateConfig('ownerId', v);
              if (user) updateConfig('aeOwner', user.display_name);
            }}
            options={icUsers.map((u) => ({ value: u.id, label: u.display_name }))}
          />
          <ConfigSelect label="Buying Culture" value={dealConfig.buyingCulture}
            onChange={(v) => updateConfig('buyingCulture', v)}
            options={[
              { value: 'direct', label: 'Direct' },
              { value: 'proxy_delegated', label: 'Proxy-Delegated' },
            ]}
          />
        </div>

        {/* Required fields row */}
        <div className="grid grid-cols-4 gap-2">
          <ConfigSelect label="SF Stage *" value={dealConfig.sfStage}
            onChange={(v) => updateConfig('sfStage', v)}
            options={Array.from({ length: 7 }, (_, i) => ({
              value: String(i + 1), label: `Stage ${i + 1}`,
            }))}
            required
          />
          <ConfigSelect label="Forecast *" value={dealConfig.sfForecast}
            onChange={(v) => updateConfig('sfForecast', v)}
            options={['Commit', 'Realistic', 'Upside', 'At Risk'].map((f) => ({ value: f, label: f }))}
            required
          />
          <ConfigSelect label="Close Quarter *" value={dealConfig.closeQuarter}
            onChange={(v) => updateConfig('closeQuarter', v)}
            options={closeQuarters.map((q) => ({ value: q, label: q }))}
            required
          />
          <div className="space-y-1">
            <label className="text-[10px] text-muted-foreground">CP Estimate * ($)</label>
            <Input
              type="number"
              placeholder="0"
              value={dealConfig.cpEstimate}
              onChange={(e) => updateConfig('cpEstimate', e.target.value)}
              className="h-8 text-xs"
            />
          </div>
        </div>

        <Button
          onClick={onAddToQueue}
          disabled={!canAddToQueue}
          className="w-full"
        >
          Add to Queue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      </div>
    </Card>
  );
}

// ── Sub-components ───────────────────────────────────────────────────

function CallStatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'new':
      return <Badge variant="outline" className="text-[10px] bg-emerald-500/20 text-emerald-400 border-emerald-500/30">NEW</Badge>;
    case 'active':
      return <Badge variant="outline" className="text-[10px] bg-sky-500/20 text-sky-400 border-sky-500/30">ACTIVE</Badge>;
    case 'imported':
      return <Badge variant="outline" className="text-[10px] bg-muted text-muted-foreground">IMPORTED</Badge>;
    default:
      return null;
  }
}

function ConfigSelect({
  label, value, onChange, options, required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  required?: boolean;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] text-muted-foreground">{label}</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value} className="text-xs">
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

---

## Task 8: Frontend — QueuePanel component

The right panel showing queued accounts and the Run Analysis button.

**Files:**
- Part of: `frontend/src/app/upload/page.tsx`

**Step 1: Implement component**

```tsx
// ── Panel 3: Queue ───────────────────────────────────────────────────

function QueuePanel({
  queue, onRemove, onRunAnalysis,
}: {
  queue: QueueItem[];
  onRemove: (name: string) => void;
  onRunAnalysis: () => void;
}) {
  return (
    <Card className="flex flex-col overflow-hidden">
      <CardHeader className="pb-2 px-3 pt-3">
        <CardTitle className="text-sm font-medium">
          Queue ({queue.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-3 pt-0 space-y-2">
        {queue.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-8">
            Select accounts and add them to the queue
          </p>
        )}
        {queue.map((item) => (
          <div
            key={item.accountName}
            className="flex items-center justify-between bg-muted/50 border border-border rounded-lg px-3 py-2"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{item.accountName}</p>
              <p className="text-[10px] text-muted-foreground">
                {item.newCallCount} new call{item.newCallCount !== 1 ? 's' : ''}
                {' · '}
                {DEAL_TYPE_ABBREV[item.dealConfig.dealType] ?? item.dealConfig.dealType}
              </p>
            </div>
            <button
              onClick={() => onRemove(item.accountName)}
              className="text-muted-foreground hover:text-red-400 transition-colors p-1"
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
      </CardContent>
      <div className="p-3 border-t border-border">
        <Button
          onClick={onRunAnalysis}
          disabled={queue.length === 0}
          className="w-full"
        >
          <Play className="size-4 mr-1.5" />
          Run Analysis ({queue.length} account{queue.length !== 1 ? 's' : ''})
        </Button>
      </div>
    </Card>
  );
}
```

---

## Task 9: Frontend — PastUploadsTable, LocalFolderModal, ManualUploadModal

Extract the existing `PastUploadsTable` (mostly unchanged), and wrap `LocalFolderTab` and `ManualUploadTab` in modal dialogs.

**Files:**
- Part of: `frontend/src/app/upload/page.tsx`

**Step 1: Implement PastUploadsTable**

Copy the existing `PastUploadsTable` from the current file (lines ~1204-1325). It stays almost identical — just add a top margin:

```tsx
// ── Past Uploads Table ───────────────────────────────────────────────

function PastUploadsTable({ refreshKey }: { refreshKey: number }) {
  // ... (copy existing implementation from current upload/page.tsx lines 1204-1325)
  // Wrap in <div className="mt-6"> at the outermost level
}
```

**Step 2: Implement LocalFolderModal**

Wrap the existing `LocalFolderTab` content in a dialog overlay:

```tsx
function LocalFolderModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-3xl max-h-[80vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Import from Local Folder</CardTitle>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="size-5" />
          </button>
        </CardHeader>
        <CardContent>
          <LocalFolderContent onClose={onClose} />
        </CardContent>
      </Card>
    </div>
  );
}
```

`LocalFolderContent` is the existing `LocalFolderTab` component logic, adapted to work inside a modal. Copy the core logic from the current file (lines ~561-1017), renaming and removing the outer Card wrapper.

**Step 3: Implement ManualUploadModal**

Same pattern:

```tsx
function ManualUploadModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Manual Transcript Upload</CardTitle>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="size-5" />
          </button>
        </CardHeader>
        <CardContent>
          <ManualUploadContent />
        </CardContent>
      </Card>
    </div>
  );
}
```

`ManualUploadContent` is the existing `ManualUploadTab` logic (lines ~1023-1198).

**Step 4: Commit the entire frontend rewrite**

```bash
git add frontend/src/app/upload/page.tsx
git commit -m "feat: replace upload page with 3-panel recording browser

Users can now browse drive recordings with DB status comparison,
configure deals, queue accounts, and run batch analysis.
Local Folder and Manual Upload available as modals."
```

---

## Task 10: Frontend — Add `accounts.get()` API method (if missing)

The `AccountDetailPanel` calls `api.accounts.get(accountId)` to auto-fill deal config. Verify this exists.

**Files:**
- Check: `frontend/src/lib/api.ts` for `accounts.get`

**Step 1: Check if method exists**

Search `api.ts` for `accounts:` section and look for a `get` method. If it exists (likely `api.accounts.get(id)`), this task is a no-op.

If missing, add:

```typescript
accounts: {
  // ... existing methods
  get: (id: string) => get<Account>(`/api/accounts/${id}`),
}
```

And verify the backend `GET /api/accounts/{id}` endpoint exists and returns `deal_type`, `ae_owner`, `owner_id`, `buying_culture`.

**Step 2: Commit if changes were needed**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: add accounts.get() API method for recording browser auto-fill"
```

---

## Task 11: Integration test — Full recording browser flow

Manually test the end-to-end flow: scan → browse → configure → queue → run.

**Steps:**

1. Start backend: `cd SIS && .venv/bin/python -m uvicorn sis.api.main:app --port 8000 --reload`
2. Start frontend: `cd SIS/frontend && npm run dev`
3. Navigate to `/upload`
4. Verify: Drive path auto-populates, Scan shows enriched account list
5. Click an account → verify calls table loads with correct NEW/ACTIVE/IMPORTED badges
6. Check that new calls are pre-selected, existing calls are disabled
7. Verify info banner shows correct message
8. Fill deal config, verify "Add to Queue" enables
9. Add 2+ accounts to queue, verify queue panel updates
10. Remove one from queue, verify it disappears
11. Click "Run Analysis" → verify BatchProgressView appears
12. Verify "Local Folder" and "Manual Upload" modals open correctly

**Step 2: Commit any fixes discovered during testing**

```bash
git add -A
git commit -m "fix: address integration issues from recording browser testing"
```

---

## Task 12: Run existing tests + lint

Ensure nothing broke.

**Step 1: Run all backend tests**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
.venv/bin/python -m pytest tests/ -v --tb=short
```

**Step 2: Run frontend lint/build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend
npm run build
```

**Step 3: Fix any failures, commit**

```bash
git add -A
git commit -m "fix: resolve test and build issues from recording browser changes"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add `buying_culture` to BatchItemRequest | schemas + api-types |
| 2 | `get_all_calls_with_status()` service + tests | gdrive_service, transcript_service |
| 3 | Enrich `list_account_folders()` with DB status | gdrive_service |
| 4 | New `/api/gdrive/calls-status` endpoint + API client | gdrive.py, api.ts, api-types.ts |
| 5 | Page skeleton with state + handlers | upload/page.tsx |
| 6 | AccountListPanel component | upload/page.tsx |
| 7 | AccountDetailPanel + CallStatusBadge + ConfigSelect | upload/page.tsx |
| 8 | QueuePanel component | upload/page.tsx |
| 9 | PastUploadsTable + Modals (Local Folder, Manual) | upload/page.tsx |
| 10 | Verify/add `accounts.get()` API method | api.ts |
| 11 | Integration test | manual |
| 12 | Run tests + lint | all |
