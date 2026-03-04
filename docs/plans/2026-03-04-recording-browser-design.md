# Recording Browser — Upload Page Redesign

**Date:** 2026-03-04
**Status:** Draft
**Replaces:** Current tabbed upload page (Google Drive / Local Folder / Paste Text)

## Problem

The current upload page shows account folders with call counts but gives no visibility into individual recordings — their dates, titles, or whether they already exist in SIS. Users can't tell which calls are new vs. already imported vs. actively used in the latest analysis. This leads to blind imports and confusion about what the pipeline is actually working with.

## Solution

Replace the tabbed upload page with a **3-panel Recording Browser** that lets users:
1. Browse accounts from the drive folder
2. See every recording with its DB status (new / imported / active)
3. Configure deal metadata and queue accounts for batch analysis

## Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HEADER: [Drive Path input] [Scan]               [Local] [Manual]      │
├──────────────┬──────────────────────────────────┬───────────────────────┤
│  ACCOUNTS    │  CALLS + DEAL CONFIG              │  QUEUE               │
│  (~200px)    │  (flex)                           │  (~250px)            │
│              │                                   │                      │
│  Scrollable  │  Calls list (scrollable, top)     │  Summary cards       │
│  list with   │  Info banner (sticky)             │  with remove (✕)     │
│  search      │  Deal config form (bottom)        │                      │
│              │  [Add to Queue →]                 │  [Run Analysis]      │
├──────────────┴──────────────────────────────────┴───────────────────────┤
│  PAST UPLOADS TABLE (below panels)                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Panel 1 — Account List (Left, ~200px fixed)

- Populated after user scans a drive folder path
- Each row: **Account name** + badge showing count of NEW (unimported) calls
  - e.g., `Acme Corp  [3 new]` or `Beta Inc  [Up to date]`
- **Search/filter** input at top
- Accounts with new calls sorted to top
- Click to select → populates middle panel
- Selected account highlighted with accent border

### New Backend Requirement

`POST /api/gdrive/accounts` response must be **enriched** with DB status:

```json
[
  {
    "name": "Acme Corp",
    "path": "/path/to/Acme Corp",
    "call_count": 8,
    "new_count": 3,           // calls NOT in DB
    "db_account_id": "uuid",  // null if account not in SIS
    "has_active_analysis": true
  }
]
```

This requires cross-referencing drive folder contents against `Transcript.gong_call_id` values in the DB for each matching account.

## Panel 2 — Account Detail (Middle, flex)

### Calls Table (top, scrollable)

Shows **ALL** calls from the drive folder for the selected account. Sorted by date descending.

| Column | Description |
|--------|-------------|
| Checkbox | Enabled for NEW calls only. Pre-checked by default. Disabled for ACTIVE/IMPORTED. |
| Date | Call date (YYYY-MM-DD) |
| Title | Call title from Gong metadata (truncated to ~60 chars) |
| Status | Badge indicating DB state |

**Status badges:**

| Badge | Color | Meaning |
|-------|-------|---------|
| `NEW` | Green (`bg-emerald-500/20 text-emerald-400`) | Not in DB — selectable, pre-checked |
| `ACTIVE` | Blue/accent (`bg-accent/20 text-accent`) | In DB, one of the 5 calls used in latest analysis |
| `IMPORTED` | Gray (`bg-muted text-muted-foreground`) | In DB but not in the active set |

### New Backend Endpoint

`POST /api/gdrive/calls-status` — returns all calls for one account with DB status:

```json
{
  "account_name": "Acme Corp",
  "db_account_id": "uuid-or-null",
  "calls": [
    {
      "date": "2026-03-01",
      "title": "QBR Review",
      "gong_call_id": "abc123",
      "has_transcript": true,
      "status": "new"           // "new" | "active" | "imported"
    }
  ]
}
```

**Backend logic:** For each call in the drive folder:
1. Extract `gong_call_id` from metadata JSON
2. Look up in `Transcript` table by `(account_id, gong_call_id)`
3. If not found → `"new"`
4. If found and `is_active=1` → `"active"`
5. If found and `is_active=0` → `"imported"`

Return ALL calls (no max_calls limit) so the user sees the full picture.

### Analysis Info Banner

Dynamic banner appears when at least 1 new call is checked:

> **ⓘ Importing {N} new calls. Analysis will run on the 5 most recent calls ({N} new + {5−N} currently active).**

If the account has no previous analysis:

> **ⓘ New account. Importing {N} calls for first analysis.**

If the user selects more than 5 new calls:

> **ⓘ Importing {N} new calls. Analysis will use the 5 most recent. Older calls will be stored but inactive.**

### Deal Config Form (bottom, sticky)

Split into two sections:

**Auto-filled (from existing account in DB):**
- Deal Type (select)
- AE Owner (select from IC users)
- Buying Culture (select: Direct / Proxy-Delegated)

**Requires fresh input (pipeline-position fields that change between cycles):**
- SF Stage (select: 1–7) — **required**
- SF Forecast Category (select: Commit / Realistic / Upside / At Risk) — **required**
- Close Quarter (select: generated list of 5 quarters) — **required**
- CP Estimate (number input, $) — **required**

For **new accounts** (not in DB): all fields are empty and required.

For **existing accounts**: Deal Type, AE Owner, Buying Culture auto-filled from `Account` record. The 4 pipeline-position fields start empty with a label: *"Update before saving"*.

### "Add to Queue" Button

- Disabled until: at least 1 new call selected AND all required fields filled
- On click: account + config + selected call IDs added to queue state
- Middle panel resets to empty / prompts user to select next account
- Left panel updates: queued accounts get a checkmark indicator

## Panel 3 — Queue (Right, ~250px fixed)

### Queue Cards

Each queued account shows a compact summary card:

```
┌─────────────────────┐
│ Acme Corp         ✕ │
│ 3 new calls · NL    │
└─────────────────────┘
```

- **Account name** (bold)
- **Call count** + **Deal Type abbreviation** (NL = New Logo, EX-U = Expansion Upsell, etc.)
- **Remove button** (✕) — removes from queue, account goes back to unqueued state in left panel

### Queue Header

`QUEUE (3)` — count updates as items are added/removed.

### "Run Analysis" Button

- Sticky at bottom of queue panel
- Shows: `Run Analysis (3 accounts)`
- Disabled if queue is empty
- On click:
  1. For each queued item: import selected calls → create/update account → normalize active transcripts
  2. Submit as batch via `POST /api/analyses/batch`
  3. Transition page to `BatchProgressView` (existing SSE-based progress component)

## Header Bar

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Recording Browser                                                      │
│  [Drive Path: ________________________________] [Scan]  [Local] [Manual]│
└─────────────────────────────────────────────────────────────────────────┘
```

- **Drive path input** + **Scan button** — same as current Google Drive tab
- On first load: auto-populate from `GET /api/gdrive/config` and auto-scan
- **Local Folder** button → opens modal with the existing `LocalFolderTab` content
- **Manual Upload** button → opens modal with the existing `ManualUploadTab` content

## Past Uploads Table

Unchanged — stays below the 3-panel browser. Shows all previously imported accounts with columns: Account Name, Health Score, Stage, Forecast, Last Analyzed, Actions (View / Delete).

## State Management

All client-side, no new global state needed:

```typescript
interface QueueItem {
  accountName: string;
  accountPath: string;
  dbAccountId: string | null;       // null for new accounts
  selectedCallIds: string[];        // gong_call_ids of NEW calls to import
  newCallCount: number;
  dealConfig: {
    dealType: string;
    aeOwner: string;
    ownerID: string;
    buyingCulture: string;
    sfStage: number;
    sfForecast: string;
    closeQuarter: string;
    cpEstimate: number;
  };
}

// Page state
const [drivePath, setDrivePath] = useState<string>('');
const [driveAccounts, setDriveAccounts] = useState<EnrichedDriveAccount[]>([]);
const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
const [accountCalls, setAccountCalls] = useState<EnrichedCall[]>([]);
const [queue, setQueue] = useState<QueueItem[]>([]);
const [isRunning, setIsRunning] = useState(false);
```

## Backend Changes Summary

| Change | File | Description |
|--------|------|-------------|
| Enhance `list_account_folders()` | `gdrive_service.py` | Return `new_count`, `db_account_id`, `has_active_analysis` per account |
| New `get_all_calls_with_status()` | `gdrive_service.py` | Return ALL calls for an account with DB status (new/active/imported) |
| New route `POST /api/gdrive/calls-status` | `gdrive.py` | Expose the enriched call list endpoint |
| Enhance `POST /api/gdrive/accounts` response | `gdrive.py` | Include enriched fields from `list_account_folders()` |

## Frontend Changes Summary

| Change | File | Description |
|--------|------|-------------|
| Replace entire upload page | `upload/page.tsx` | New 3-panel Recording Browser layout |
| Add `LocalFolderModal` | `upload/page.tsx` or new component | Extract existing `LocalFolderTab` into modal |
| Add `ManualUploadModal` | `upload/page.tsx` or new component | Extract existing `ManualUploadTab` into modal |
| Update API client | `api.ts` | Add `gdrive.callsStatus()` method |
| Update types | `api-types.ts` | Add `EnrichedDriveAccount`, `EnrichedCall`, `QueueItem` types |

## Design Tokens

Follows existing Signal Clarity dark theme:
- Card backgrounds: `bg-card` (#111f17)
- Borders: `border-border`
- Selected account: `border-l-2 border-accent bg-accent/5`
- NEW badge: `bg-emerald-500/20 text-emerald-400 border-emerald-500/30`
- ACTIVE badge: `bg-sky-500/20 text-sky-400 border-sky-500/30`
- IMPORTED badge: `bg-muted text-muted-foreground`
- Queue cards: `bg-muted/50 border border-border rounded-lg p-3`

## Out of Scope

- Drag-and-drop reordering in queue
- Editing queued items inline (remove + re-add instead)
- Auto-refresh when new files appear in drive folder
- Batch import without running analysis (import-only mode)
