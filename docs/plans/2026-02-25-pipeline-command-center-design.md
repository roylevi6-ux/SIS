# Pipeline Command Center — Complete UI Overhaul Design

**Date**: 2026-02-25
**Status**: Pending Approval
**Scope**: Full redesign of Pipeline Overview, Deals, Forecast, and Divergence pages into a unified Pipeline Command Center + brand system overhaul + Quota DB

---

## 1. Executive Summary

### What changes for users
The VP Sales will open one page — the **Pipeline Command Center** — and immediately see: "Am I going to hit my number?" (quota vs pipeline vs coverage), "What changed?" (net pipeline movement), and "What needs my attention?" (inspection queue). Today this requires visiting 4 separate pages and mentally assembling the picture.

### Core principles
1. **Dollars first, counts second** — every metric leads with $ value
2. **Forecast categories as primary lens** — Commit/Realistic/Upside/Risk, not Healthy/At Risk/Critical
3. **Health as enrichment, not framework** — SIS health scores augment the forecast view, not replace it
4. **One page, zero page-hopping** — Pipeline + Deals + Forecast + Divergence merge into one
5. **Actionable, not decorative** — every widget answers "so what?" and enables a next action

---

## 2. Brand System

### 2.1 Color Palette — Riskified-Inspired Green

Anchor color: `#30D5A0` (medium emerald-teal, "middle Riskified green")

```css
:root {
  /* Brand: SIS Green (Riskified-inspired) */
  --brand-50:  #ecfdf5;    /* Faintest tint — page background */
  --brand-100: #d1fae5;    /* Light wash — hover states */
  --brand-200: #a7f3d0;    /* Light accent — card highlights */
  --brand-300: #6ee7b7;    /* Medium-light — secondary elements */
  --brand-400: #34d399;    /* ★ PRIMARY — buttons, active states, links */
  --brand-500: #10b981;    /* Darker primary — pressed states */
  --brand-600: #059669;    /* Deep — sidebar active item bg */
  --brand-700: #047857;    /* Dark — sidebar background */
  --brand-800: #065f46;    /* Darker — sidebar hover */
  --brand-900: #064e3b;    /* Darkest — sidebar base */

  /* Override shadcn primary */
  --primary: oklch(0.70 0.17 165);      /* Maps to ~brand-400 */
  --primary-foreground: oklch(0.985 0 0); /* White text on primary */

  /* Surface hierarchy (green-tinted) */
  --background: oklch(0.975 0.005 165);  /* Faint green-gray page bg */
  --card: oklch(1 0 0);                  /* Pure white — cards float */

  /* Dark green sidebar */
  --sidebar: oklch(0.20 0.04 165);       /* Dark forest green */
  --sidebar-foreground: oklch(0.92 0.01 165);
  --sidebar-primary: oklch(0.70 0.17 165); /* brand-400 */
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: oklch(0.26 0.05 165);
  --sidebar-accent-foreground: oklch(0.95 0.01 165);
  --sidebar-border: oklch(0.28 0.04 165);
  --sidebar-muted: oklch(0.55 0.03 165);
}
```

### 2.2 Semantic Data Colors

```css
:root {
  /* Health tiers (keep existing, consolidate tokens) */
  --color-healthy: #059669;
  --color-healthy-bg: #d1fae5;
  --color-at-risk: #d97706;
  --color-at-risk-bg: #fef3c7;
  --color-critical: #dc2626;
  --color-critical-bg: #fee2e2;

  /* Forecast categories */
  --color-forecast-commit: #059669;     /* Green — high confidence */
  --color-forecast-commit-bg: #d1fae5;
  --color-forecast-realistic: #2563eb;  /* Blue — moderate confidence */
  --color-forecast-realistic-bg: #dbeafe;
  --color-forecast-upside: #d97706;     /* Amber — speculative */
  --color-forecast-upside-bg: #fef3c7;
  --color-forecast-risk: #dc2626;       /* Red — at risk */
  --color-forecast-risk-bg: #fee2e2;

  /* Momentum (unchanged) */
  --color-improving: #059669;
  --color-stable: #6b7280;
  --color-declining: #dc2626;
}
```

### 2.3 Typography — Inter

Replace Geist Sans with Inter. Keep Geist Mono for code/data.

```tsx
// layout.tsx
import { Inter } from 'next/font/google';
import { Geist_Mono } from 'next/font/google';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});
```

**Type scale:**

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| display | 36px | 700 | KPI hero numbers (Number Line) |
| h1 | 24px | 700 | Page title |
| h2 | 18px | 600 | Section titles |
| h3 | 16px | 600 | Card titles |
| body | 14px | 400 | Table cells, descriptions |
| body-sm | 13px | 400/500 | Badge text, secondary info |
| caption | 12px | 400 | Timestamps, helper text |
| overline | 11px | 600 | Uppercase section labels |

**Rules:**
- All financial numbers: `font-variant-numeric: tabular-nums` (Inter has this built in)
- KPI numbers use Geist Mono for extra crispness at large sizes
- Table header labels: 12px, medium weight, uppercase, tracking-wide

### 2.4 Logo

Upgrade from single "S" to branded mark:

```tsx
<div className="flex items-center gap-3 px-4 py-5">
  <div className="flex size-9 items-center justify-center rounded-xl
    bg-gradient-to-br from-brand-400 to-brand-600
    text-white font-bold text-sm tracking-tight
    shadow-lg shadow-brand-500/25">
    SIS
  </div>
  <div className="flex flex-col">
    <span className="text-sm font-semibold text-sidebar-foreground">SIS</span>
    <span className="text-[11px] text-sidebar-muted">Sales Intelligence</span>
  </div>
</div>
```

---

## 3. Pipeline Command Center — Page Layout

### 3.1 Page Structure (top to bottom)

```
┌─────────────────────────────────────────────────────────────┐
│                    PAGE HEADER                               │
│  Pipeline Command Center [Q1 2026▾] [Team/VP▾] [AE▾] [🔍] │
├─────────────────────────────────────────────────────────────┤
│                    NUMBER LINE (sticky)                       │
│  Quota: $283K  │  Pipeline: $840K  │  Coverage: 2.97x       │
│  Weighted: $520K  │  Gap: +$237K above quota                 │
│  [████ Commit $310K ████][███ Real $280K ███][██ Up $180K]   │
├─────────────────────────────────────────────────────────────┤
│                    ATTENTION STRIP                            │
│  ⚠ 3 deals need attention ($890K at risk)                    │
│  • Acme Corp ($340K) — Health ↓ 72→41, declining 2 runs     │
│  • Beta Inc ($320K) — AI: At Risk, IC: Commit (divergent)   │
│  • Gamma Ltd ($230K) — No activity 21 days, S4 for 6 weeks  │
├─────────────────────────────────────────────────────────────┤
│                    PIPELINE CHANGES                           │
│  This week: +$420K added │ -$180K dropped │ +$240K net       │
│  2 stage advances │ 1 forecast flip │ 3 new risks            │
├─────────────────────────────────────────────────────────────┤
│  FILTER CHIPS                                                │
│  [Commit 8] [Realistic 12] [Upside 6] [Risk 4] [All 30]    │
│  + Health: [Healthy] [At Risk] [Critical]                    │
│  + Flags: [Divergent] [Stale] [Declining]                    │
├─────────────────────────────────────────────────────────────┤
│                    DEAL TABLE                                │
│  Account    │ AE     │ MRR   │ Type │ Stage │ Forecast │ ...│
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│  Acme Corp  │ Smith  │ $340K │ New  │ S5    │ Commit/Risk│   │
│  (TanStack Table: sort, filter, pagination, col visibility)  │
├─────────────────────────────────────────────────────────────┤
│                    TEAM FORECAST GRID (VP+ only)             │
│  Team       │ Commit │ Real  │ Upside │ Risk  │ Total │ Cov │
│  Lisa L     │ $120K  │ $80K  │ $60K   │ $55K  │ $315K │ 3.0x│
│  Lachlan    │ $95K   │ $70K  │ $45K   │ $40K  │ $250K │ 2.2x│
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Number Line (Always Visible, Sticky on Scroll)

**Product impact**: VP sees quota attainment in the first 2 seconds.

**Quarter filter** (top-right, visually prominent):
- Options: Q1 2026, Q2 2026, Q3 2026, Q4 2026, Full Year 2026
- Defaults to current quarter
- **Global scope**: Changing the quarter recalculates ALL sections on the page:
  - Number Line: quota (annual ÷ 4), pipeline value, coverage, weighted forecast, gap
  - Attention Strip: deals needing attention within that quarter's pipeline
  - Pipeline Changes: movement during that quarter (or current week within it)
  - Filter Chips: counts update to reflect the quarter's deals
  - Deal Table: filtered to deals active in that quarter (deals with assessments or calls in the period)
  - Team Forecast Grid: team breakdowns for that quarter
- The quarter filter is the first control in the header row, styled with a brand-tinted background to signal it's the primary context setter
- Default: auto-selects the current quarter based on today's date

**Team / VP filter** (hierarchical, uses org tree):
- Grouped dropdown with two sections:
  - **VPs**: Roy, Gili — selecting a VP shows all teams under them (Roy → Lisa L + Lachlan; Gili → Bar Barda + Ying)
  - **Team Leads**: Lisa L, Lachlan, Bar Barda, Ying — shows a single team's deals
- "All Teams" is the default (shows everything the user has permission to see)
- Uses the existing User/Team hierarchy (5-level: IC → TL → VP → GM → Admin)
- The dropdown auto-populates based on the logged-in user's scope: a VP only sees their own teams, a GM sees all VPs and teams
- When a VP/Team is selected, ALL sections update: Number Line recalculates for that scope, Attention Strip filters, Deal Table filters, Team Grid highlights the selected row

**Data sources:**
- Quota: from new `quotas` DB table (annual ÷ 4 for quarterly view, full amount for Full Year)
- Pipeline: sum of `mrr_estimate` across all active deals
- Coverage: pipeline ÷ quota
- Weighted: Commit × 0.90 + Realistic × 0.60 + Upside × 0.30 + Risk × 0.10
- Gap: weighted − quota (positive = ahead, negative = behind)
- Distribution bar: forecast category $ amounts as proportional segments

**Visual treatment:**
- Full-width card with subtle brand-50 background
- KPI numbers in 36px Geist Mono, bold
- Labels in 12px uppercase, muted
- Distribution bar: colored segments matching forecast category colors, with $ labels
- Sticky on scroll (sticks below the page header when user scrolls down)

### 3.3 Attention Strip (Inspection Queue)

**Product impact**: Top 3-5 deals the VP should act on RIGHT NOW, ranked by dollar impact.

**Logic for selecting deals:**
1. Declining health (health score dropped ≥10 points in latest run) — sorted by MRR
2. Divergent forecast (AI ≠ IC) — sorted by MRR
3. Stale deals (no call activity ≥14 days, stage ≥ S3) — sorted by MRR
4. Maximum 5 items shown, expandable to see all

**Visual treatment:**
- Amber/orange left border (warning, not critical)
- Collapsible: expanded by default when items exist, collapsed when empty ("All clear ✓")
- Each item: account name (link), MRR, one-line reason, days since last action
- "View all alerts" link filters the deal table to attention-needed deals

### 3.4 Pipeline Changes Strip

**Product impact**: VP sees net pipeline movement at a glance — "is the pipe growing or shrinking?"

**Metrics:**
- Pipeline added (new deals or value increases since last week)
- Pipeline dropped (lost deals or value decreases)
- Net change (added − dropped)
- Stage advances count
- Forecast flips count
- New risks count

**Data source**: Compare current deal assessments to previous-week assessments. Backend already has assessment history to compute deltas.

**Visual treatment:**
- Compact horizontal strip with inline metrics
- Green for positive (added), red for negative (dropped), gray for neutral
- Collapsible/expandable

### 3.5 Filter Chips (Replace Tabs)

**Product impact**: Multi-dimensional filtering instead of single-axis tabs.

Replace the current 5 health-tier tabs with a **chip bar** supporting multiple simultaneous filters:

**Row 1 — Forecast Category (primary):**
- `Commit (8)` | `Realistic (12)` | `Upside (6)` | `Risk (4)` | `All (30)`
- Color-coded chip backgrounds matching forecast colors
- Shows deal count AND total MRR in tooltip

**Row 2 — Health Overlay (secondary, toggleable):**
- `Healthy` | `At Risk` | `Critical`
- Can be active simultaneously with forecast filter (intersection)

**Row 3 — Attention Flags (toggleable):**
- `Divergent` | `Stale` | `Declining`
- These cross-cut both forecast and health dimensions

**Behavior**: Multiple chips can be active. Clicking a chip toggles it. Active chips filter the table to the intersection. A "Clear all" link resets to All.

### 3.6 Deal Table (Redesigned with TanStack Table)

**Columns (left to right):**

| # | Column | Width | Content |
|---|--------|-------|---------|
| 1 | Account | 200px flex | Name (link) + AE owner in subtitle row + deal memo hover tooltip |
| 2 | MRR | 90px | Dollar amount, right-aligned, tabular-nums |
| 3 | Type | 70px | "New" / "Expansion" badge |
| 4 | Stage | 100px | Stage name (not number). E.g., "Negotiate" not "S5" |
| 5 | Forecast | 120px | Combined AI/IC column. Shows AI forecast. When divergent: split display with highlight |
| 6 | Health | 80px | Score number + color dot + optional mini-bar |
| 7 | Momentum | 90px | Arrow icon + label (Improving/Stable/Declining) |
| 8 | Confidence | 60px | AI confidence score (0-1), from `overall_confidence` |
| 9 | Last Call | 80px | "2d ago" / "14d ago" with color-coded aging indicator |

**Visual enhancements:**
- **Row urgency tinting**: Critical deals → `bg-red-50/40`, At Risk → `bg-amber-50/30`
- **Divergence highlighting**: When AI ≠ IC forecast, the Forecast cell shows both with amber background
- **Deal memo hover**: Hovering account name shows `deal_memo_preview` in a tooltip
- **Sticky header**: Table header sticks when scrolling within the table
- **Zebra striping**: Alternate rows with `bg-muted/15`
- **Row hover**: `hover:bg-brand-50` (faint green tint)
- **Sort indicators**: Active sort column highlighted, direction arrows
- **Pagination**: 25 deals per page (configurable), bottom pagination bar
- **Column visibility**: Dropdown to show/hide columns (gear icon in header)

**Future (P2-P3):**
- Inline sparklines showing 4-week health trend per deal
- Row-level action menu (...) with: View Detail, Flag for Review, Add Note

### 3.7 Team Forecast Grid (VP+ Only)

**Product impact**: The Clari-style matrix showing each team's forecast breakdown.

**Structure:**
```
Team         │ Commit  │ Realistic │ Upside  │ Risk    │ Total   │ Coverage
─────────────┼─────────┼───────────┼─────────┼─────────┼─────────┼─────────
Lisa L       │ $120K   │ $80K      │ $60K    │ $55K    │ $315K   │ 3.0x
Lachlan      │ $95K    │ $70K      │ $45K    │ $40K    │ $250K   │ 2.2x
Bar Barda    │ $110K   │ $90K      │ $70K    │ $45K    │ $315K   │ 2.8x
Ying         │ $85K    │ $60K      │ $40K    │ $65K    │ $250K   │ 2.0x ⚠
```

- Color-coded cells (green for high coverage, amber for low)
- Clickable team rows → filters the deal table to that team
- Collapsible section (default: expanded for VP+, hidden for IC/TL)
- Coverage column uses quota from the new Quota DB table

---

## 4. Pages Merged / Redirected

| Current Page | Action | Destination |
|-------------|--------|-------------|
| `/pipeline` | **Redesigned** | Becomes the Pipeline Command Center |
| `/deals` | **Redirect** | `redirect('/pipeline')` — search functionality moves to pipeline filter |
| `/deals/[id]` | **Keep** | Deal detail page, accessed by clicking a deal row |
| `/forecast` | **Merge** | Forecast rollup becomes the Number Line header section |
| `/divergence` | **Merge** | Becomes a filter toggle chip ("Divergent") on the pipeline page |

**Sidebar changes:**
- "Pipeline Overview" → "Pipeline" (the command center)
- "Deal Detail" → removed (accessed from pipeline table)
- "Divergence" → removed (filter chip on pipeline)
- "Forecast" → removed (section of pipeline)

---

## 5. Sidebar Redesign

### Visual
- **Background**: Dark forest green (`--sidebar: oklch(0.20 0.04 165)`)
- **Text**: Light green-tinted white
- **Active item**: Brand-400 background with white text
- **Hover**: Slightly lighter dark green
- **Logo**: "SIS" gradient mark (brand-400 → brand-600)
- **User footer**: Same dark treatment with muted role text

### Navigation structure (simplified)

```
ANALYTICS
  ■ Pipeline              ← Command Center (was Pipeline Overview)
  ■ Trends                ← kept
  ■ Team Rollup           ← VP+ only, kept
  ■ Rep Scorecard         ← TL+ only, kept
  ■ Methodology           ← kept

ACTIONS
  ■ Import & Analyze      ← kept
  ■ Chat                  ← kept
  ■ Meeting Prep          ← kept

ADMIN (admin only)
  ■ Team Management       ← kept
  ■ Feedback              ← TL+ only
  ■ Calibration           ← admin only
  ... (other admin items unchanged)
```

Removed from sidebar: "Deal Detail", "Divergence", "Forecast"

---

## 6. Quota Database Table

### Schema

```python
class Quota(Base):
    __tablename__ = "quotas"

    id = Column(Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    period = Column(Text, nullable=False)    # "2026" (annual)
    amount = Column(Float, nullable=False)   # Annual quota in USD
    created_at = Column(Text, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(Text, default=lambda: datetime.utcnow().isoformat())

    __table_args__ = (
        UniqueConstraint('user_id', 'period', name='uq_user_period'),
    )
```

### Seed Data (2026 Annual Quotas)

| User | Annual Amount | Maps to existing User |
|------|-------------|----------------------|
| Nadine Barchecht | $104,750 | L4 under Lisa L |
| Omer Snir | $104,750 | L4 under Lisa L |
| Stefania Fanari | $104,750 | L4 under Lisa L |
| Keiko Navon | $125,700 | L4 under Lachlan |
| Nicholas Kirtley | $125,700 | L4 under Lachlan |
| Dror Gross | $104,750 | L4 under Bar Barda |
| Uriel Ross | $104,750 | L4 under Bar Barda |
| Yos Jacobs | $104,750 | L4 under Bar Barda |
| Lei Bao | $83,800 | L4 under Ying |
| Wenze Li | $83,800 | L4 under Ying |
| ZhenYu Qiao | $83,800 | L4 under Ying |

**Rollup logic**: Team lead quota = sum of their ICs. VP quota = sum of their TLs. GM quota = sum of their VPs. These are stored at the IC level; rollups are computed at query time using the existing User/Team hierarchy.

### API Endpoints

```
GET  /api/quotas/{user_id}?period=2026    → user's quota
GET  /api/quotas/team/{team_id}?period=2026 → team rollup
POST /api/quotas/                          → create/update quota (admin only)
```

---

## 7. New Dependencies

| Package | Purpose | Bundle Impact |
|---------|---------|--------------|
| `@tanstack/react-table` | Sortable, filterable deal table | +15KB |
| `@formkit/auto-animate` | Smooth list animations | +2KB |
| `inter` (via next/font) | Inter typeface | ~0 (font optimization by Next.js) |

**Deferred to later:**
- `@tremor/react` — cherry-pick KPI card and sparkline components (copy-paste, no install)
- `motion` (Framer Motion) — number counter animations
- `@phosphor-icons/react` — duotone dashboard icons
- `@nivo/funnel` — funnel chart for pipeline

**Use existing:**
- `recharts` 3.7.0 (already installed) — for forecast donut, distribution bar, sparklines

---

## 8. Backend Changes Required

### New endpoint: Pipeline Command Center data

```
GET /api/dashboard/command-center?team={team_id}&ae={ae_name}&period=Q1-2026
```

Returns:
```json
{
  "quota": { "amount": 283000, "period": "Q1-2026" },
  "pipeline": {
    "total_value": 840000,
    "total_deals": 30,
    "coverage": 2.97,
    "weighted_value": 520000,
    "gap": 237000
  },
  "forecast_breakdown": {
    "commit": { "count": 8, "value": 310000 },
    "realistic": { "count": 12, "value": 280000 },
    "upside": { "count": 6, "value": 180000 },
    "risk": { "count": 4, "value": 70000 }
  },
  "attention_items": [
    {
      "account_id": "...",
      "account_name": "Acme Corp",
      "mrr_estimate": 340000,
      "reason": "Health dropped 72→41, declining 2 consecutive runs",
      "type": "declining"
    }
  ],
  "changes_this_week": {
    "added": 420000,
    "dropped": 180000,
    "net": 240000,
    "stage_advances": 2,
    "forecast_flips": 1,
    "new_risks": 3
  },
  "deals": [ /* PipelineDeal[] with all fields */ ],
  "team_grid": [ /* VP+ only: team × forecast category matrix */ ]
}
```

### Modified endpoints
- Existing `/api/dashboard/pipeline` → can be replaced by command-center endpoint
- Existing `/api/dashboard/insights` → folded into `attention_items`

---

## 9. Phased Delivery

### Phase 0 — Brand Foundation (3-4 days)
- [ ] Switch font from Geist to Inter in layout.tsx
- [ ] Implement Riskified green color palette in globals.css
- [ ] Dark green sidebar (background, text, active states, logo)
- [ ] Tinted page background (brand-50)
- [ ] Unified semantic color tokens (health, forecast, momentum)
- [ ] Consolidated color usage across all badge/indicator components
- [ ] Max-width constraint on main content area

### Phase 1 — Page Merge + Number Line + Table (5-6 days)
- [ ] Create Quota DB table + migration + seed script
- [ ] Create `/api/quotas/` endpoints
- [ ] Create `/api/dashboard/command-center` endpoint
- [ ] Build Number Line component (quota/pipeline/coverage/weighted/gap)
- [ ] Build forecast distribution bar (horizontal stacked segments)
- [ ] Build filter chips (forecast categories + health + flags)
- [ ] Rebuild deal table with TanStack Table
- [ ] Add AE column, combined forecast column, confidence column
- [ ] Add row urgency tinting + divergence highlighting
- [ ] Add deal memo hover tooltip
- [ ] Redirect /deals → /pipeline
- [ ] Remove Forecast and Divergence from sidebar
- [ ] Simplify sidebar navigation structure

### Phase 2 — Intelligence Layer (4-5 days)
- [ ] Build Attention Strip / Inspection Queue component
- [ ] Build Pipeline Changes strip
- [ ] Build Team Forecast Grid (VP+ only)
- [ ] Add forecast donut chart (Recharts)
- [ ] Add pipeline distribution sparkline
- [ ] Add aging indicators to Last Call column (green/amber/red bar)
- [ ] Add inline health sparklines to deal table (4-week trend)
- [ ] Add AutoAnimate to deal list for smooth filter transitions
- [ ] Polish: sticky Number Line on scroll, sticky table header

---

## 10. Files Affected

### New files
- `frontend/src/components/number-line.tsx`
- `frontend/src/components/attention-strip.tsx`
- `frontend/src/components/pipeline-changes.tsx`
- `frontend/src/components/filter-chips.tsx`
- `frontend/src/components/team-forecast-grid.tsx`
- `frontend/src/components/forecast-donut.tsx`
- `frontend/src/components/data-table.tsx` (TanStack Table wrapper)
- `frontend/src/lib/hooks/use-command-center.ts`
- `frontend/src/lib/hooks/use-quotas.ts`
- `sis/models/quota.py`
- `sis/services/quota_service.py`
- `sis/routes/quotas.py`
- `scripts/seed_quotas.py`

### Modified files
- `frontend/src/app/layout.tsx` — Inter font
- `frontend/src/app/globals.css` — full color system overhaul
- `frontend/src/components/sidebar.tsx` — dark sidebar + simplified nav
- `frontend/src/app/pipeline/page.tsx` — complete rewrite → Command Center
- `frontend/src/app/deals/page.tsx` — redirect to /pipeline
- `frontend/src/components/health-badge.tsx` — use semantic tokens
- `frontend/src/components/forecast-badge.tsx` — use semantic tokens
- `frontend/src/components/momentum-indicator.tsx` — use semantic tokens
- `frontend/src/components/deal-table.tsx` — replace with TanStack-based data-table
- `sis/models/__init__.py` — register Quota model
- `sis/services/dashboard_service.py` — add command-center aggregation
- `sis/routes/dashboard.py` — add command-center endpoint

### Deleted/redirected
- `frontend/src/app/deals/page.tsx` — becomes redirect
- `frontend/src/app/forecast/page.tsx` — merged into pipeline
- `frontend/src/app/divergence/page.tsx` — merged into pipeline (filter chip)
- `frontend/src/components/pipeline-movers.tsx` — replaced by attention-strip + pipeline-changes
