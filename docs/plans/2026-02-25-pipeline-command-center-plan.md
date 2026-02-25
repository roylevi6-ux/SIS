# Pipeline Command Center — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Overhaul the Pipeline Overview into a unified Command Center with Riskified-green brand system, forecast-first framing, quota tracking, and intelligence widgets.

**Architecture:** Three-phase delivery — Phase 0 rewires the visual foundation (colors, fonts, sidebar), Phase 1 builds the Command Center page (Number Line, TanStack Table, filter chips, Quota DB + API), Phase 2 adds intelligence widgets (Attention Strip, Pipeline Changes, Team Forecast Grid). Each phase is independently shippable.

**Tech Stack:** Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui, TanStack Table, Recharts, Inter font, FastAPI, SQLAlchemy 2.0, SQLite.

**Design doc:** `docs/plans/2026-02-25-pipeline-command-center-design.md`
**Visual mockup:** `docs/plans/pipeline-command-center-mockup.html`

---

## Phase 0 — Brand Foundation

### Task 1: Switch font from Geist Sans to Inter

**Files:**
- Modify: `frontend/src/app/layout.tsx`

**Step 1: Update the font import and CSS variable**

Replace the Geist Sans import with Inter. Keep Geist Mono for code/numbers.

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Geist_Mono } from 'next/font/google';
import './globals.css';

import { Providers } from '@/components/providers';
import { AuthGuard } from '@/components/auth-guard';
import { ErrorBoundary } from '@/components/error-boundary';
import { DesktopSidebar, MobileSidebar } from '@/components/sidebar';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'SIS — Sales Intelligence System',
  description: 'AI-powered sales pipeline intelligence',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <AuthGuard>
            <DesktopSidebar />
            <MobileSidebar />
            <ErrorBoundary>
              <main className="min-h-screen lg:ml-64">
                <div className="pt-16 lg:pt-0">{children}</div>
              </main>
            </ErrorBoundary>
          </AuthGuard>
        </Providers>
      </body>
    </html>
  );
}
```

**Step 2: Update the Tailwind font variable in globals.css**

In `frontend/src/app/globals.css`, change line 10:
```css
--font-sans: var(--font-inter);
```
(was `--font-geist-sans`)

**Step 3: Verify the app renders with Inter**

Run: `cd frontend && npm run dev`
Expected: App loads, text renders in Inter (check browser DevTools → Computed → font-family)

**Step 4: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css
git commit -m "feat(brand): switch body font from Geist Sans to Inter"
```

---

### Task 2: Implement Riskified green color palette in globals.css

**Files:**
- Modify: `frontend/src/app/globals.css`

**Step 1: Replace the :root color variables**

Replace the entire `:root { ... }` block (lines 64-97) with the new Riskified-green palette:

```css
:root {
  --radius: 0.625rem;
  --background: oklch(0.975 0.005 165);   /* Faint green-gray page bg */
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);                   /* Pure white cards */
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.70 0.17 165);        /* Brand-400 green */
  --primary-foreground: oklch(0.985 0 0);  /* White on green */
  --secondary: oklch(0.97 0.005 165);     /* Green-tinted secondary */
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0.005 165);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.95 0.01 165);         /* Green-tinted accent */
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0.005 165);       /* Green-tinted border */
  --input: oklch(0.922 0.005 165);
  --ring: oklch(0.70 0.17 165);           /* Brand-400 focus ring */
  --chart-1: oklch(0.70 0.17 165);        /* Brand green */
  --chart-2: oklch(0.6 0.118 184.704);
  --chart-3: oklch(0.398 0.07 227.392);
  --chart-4: oklch(0.828 0.189 84.429);
  --chart-5: oklch(0.769 0.188 70.08);

  /* Dark green sidebar */
  --sidebar: oklch(0.20 0.04 165);
  --sidebar-foreground: oklch(0.92 0.01 165);
  --sidebar-primary: oklch(0.70 0.17 165);
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: oklch(0.26 0.05 165);
  --sidebar-accent-foreground: oklch(0.95 0.01 165);
  --sidebar-border: oklch(0.28 0.04 165);
  --sidebar-ring: oklch(0.70 0.17 165);
}
```

**Step 2: Add forecast category color tokens to the @theme inline block**

After the existing health tier colors (line ~19), add:

```css
  /* Forecast category colors */
  --color-forecast-commit: #059669;
  --color-forecast-commit-bg: #d1fae5;
  --color-forecast-realistic: #2563eb;
  --color-forecast-realistic-bg: #dbeafe;
  --color-forecast-upside: #d97706;
  --color-forecast-upside-bg: #fef3c7;
  --color-forecast-risk: #dc2626;
  --color-forecast-risk-bg: #fee2e2;

  /* Brand palette (direct hex for components that need it) */
  --color-brand-50: #ecfdf5;
  --color-brand-100: #d1fae5;
  --color-brand-200: #a7f3d0;
  --color-brand-300: #6ee7b7;
  --color-brand-400: #34d399;
  --color-brand-500: #10b981;
  --color-brand-600: #059669;
  --color-brand-700: #047857;
  --color-brand-800: #065f46;
  --color-brand-900: #064e3b;
```

**Step 3: Verify colors render correctly**

Run: `cd frontend && npm run dev`
Expected: Page background has a faint green-gray tint. Sidebar is dark forest green. Primary buttons are green.

**Step 4: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "feat(brand): implement Riskified-green color palette and semantic tokens"
```

---

### Task 3: Dark green sidebar + branded SIS logo

**Files:**
- Modify: `frontend/src/components/sidebar.tsx`

**Step 1: Update the SidebarLogo component**

Replace the existing `SidebarLogo` function (lines 180-196) with:

```tsx
function SidebarLogo() {
  return (
    <div className="flex items-center gap-3 px-4 py-5 border-b border-sidebar-border">
      <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-white font-bold text-sm tracking-tight shadow-lg shadow-brand-500/25 shrink-0">
        SIS
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-semibold text-sidebar-foreground leading-tight">
          SIS
        </span>
        <span className="text-[11px] text-sidebar-muted leading-tight">
          Sales Intelligence
        </span>
      </div>
    </div>
  );
}
```

Note: The `text-sidebar-muted` utility needs a mapping. Add to the `@theme inline` block in globals.css:
```css
  --color-sidebar-muted: var(--sidebar-muted);
```

And add `--sidebar-muted: oklch(0.55 0.03 165);` to the `:root` block (add below `--sidebar-ring`).

**Step 2: Simplify the NAV_GROUPS array**

Update `NAV_GROUPS` (lines 74-110) — remove "Deal Detail", "Divergence", "Forecast" since they're merged into Pipeline. Rename "Pipeline Overview" to "Pipeline":

```tsx
const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Analytics',
    items: [
      { label: 'Pipeline', href: '/pipeline', icon: LayoutDashboard },
      { label: 'Team Rollup', href: '/team-rollup', icon: Users, minRole: 'vp' },
      { label: 'Rep Scorecard', href: '/rep-scorecard', icon: Award, minRole: 'team_lead' },
      { label: 'Methodology', href: '/methodology', icon: BookOpen },
    ],
  },
  {
    label: 'Actions',
    items: [
      { label: 'Import & Analyze', href: '/upload', icon: Upload },
      { label: 'Chat', href: '/chat', icon: MessageSquare },
      { label: 'Meeting Prep', href: '/meeting-prep', icon: Calendar },
    ],
  },
  {
    label: 'Admin',
    items: [
      { label: 'Team Management', href: '/settings/teams', icon: Users, minRole: 'admin' },
      { label: 'Feedback', href: '/feedback', icon: ThumbsUp, minRole: 'team_lead' },
      { label: 'Calibration', href: '/calibration', icon: Settings, minRole: 'admin' },
      { label: 'Prompt Versions', href: '/prompts', icon: Code, minRole: 'admin' },
      { label: 'Costs', href: '/costs', icon: DollarSign, minRole: 'admin' },
      { label: 'Usage', href: '/usage', icon: BarChart3, minRole: 'admin' },
      { label: 'Activity Log', href: '/activity-log', icon: ClipboardList, minRole: 'admin' },
      { label: 'Golden Tests', href: '/golden-tests', icon: CheckCircle, minRole: 'admin' },
      { label: 'Digest', href: '/digest', icon: Mail, minRole: 'team_lead' },
      { label: 'Seeding', href: '/seeding', icon: Database, minRole: 'admin' },
    ],
  },
];
```

**Step 3: Remove unused icon imports**

Remove `FileText`, `GitCompare`, `TrendingUp`, `Play` from the lucide-react import (they were used by the removed nav items).

**Step 4: Verify sidebar renders with dark green background and new logo**

Run: `cd frontend && npm run dev`
Expected: Sidebar is dark forest green, logo shows gradient "SIS" mark, navigation has fewer items (no Deal Detail, Divergence, Forecast).

**Step 5: Commit**

```bash
git add frontend/src/components/sidebar.tsx frontend/src/app/globals.css
git commit -m "feat(brand): dark green sidebar with branded SIS logo, simplified nav"
```

---

### Task 4: Update badge components to use semantic color tokens

**Files:**
- Modify: `frontend/src/components/health-badge.tsx`
- Modify: `frontend/src/components/forecast-badge.tsx`
- Modify: `frontend/src/components/momentum-indicator.tsx`

**Step 1: Update health-badge.tsx**

Read the current file, then update the color mapping to use the CSS variable-based classes. The colors are already correct (`text-healthy`, `text-at-risk`, `text-critical`) — just ensure the background variants use the `-bg` tokens. Current implementation should already work with the new palette since we kept the same hex values.

Verify the badge renders correctly — no code change needed if using existing `text-healthy` / `bg-healthy-light` classes.

**Step 2: Update forecast-badge.tsx**

Update to use the new forecast semantic tokens. Replace the color logic:

```tsx
function forecastColor(category: string | null): { text: string; bg: string } {
  switch (category?.toLowerCase()) {
    case 'commit':
      return { text: 'text-forecast-commit', bg: 'bg-forecast-commit-bg' };
    case 'realistic':
      return { text: 'text-forecast-realistic', bg: 'bg-forecast-realistic-bg' };
    case 'upside':
      return { text: 'text-forecast-upside', bg: 'bg-forecast-upside-bg' };
    case 'at risk':
    case 'risk':
      return { text: 'text-forecast-risk', bg: 'bg-forecast-risk-bg' };
    default:
      return { text: 'text-muted-foreground', bg: 'bg-muted' };
  }
}
```

**Step 3: Verify badges render correctly**

Run: `cd frontend && npm run dev`
Navigate to `/pipeline`, check that badges use correct colors.

**Step 4: Commit**

```bash
git add frontend/src/components/forecast-badge.tsx frontend/src/components/health-badge.tsx frontend/src/components/momentum-indicator.tsx
git commit -m "feat(brand): update badge components to use semantic color tokens"
```

---

### Task 5: Redirect /deals to /pipeline

**Files:**
- Modify: `frontend/src/app/deals/page.tsx`

**Step 1: Replace the deals page with a redirect**

```tsx
// frontend/src/app/deals/page.tsx
import { redirect } from 'next/navigation';

export default function DealsPage() {
  redirect('/pipeline');
}
```

**Step 2: Verify redirect works**

Run: `cd frontend && npm run dev`
Navigate to `/deals` — should redirect to `/pipeline`.

**Step 3: Commit**

```bash
git add frontend/src/app/deals/page.tsx
git commit -m "feat(merge): redirect /deals to /pipeline command center"
```

---

## Phase 1 — Command Center Core

### Task 6: Create Quota DB model + seed script

**Files:**
- Modify: `sis/db/models.py` — add Quota model
- Modify: `sis/db/__init__.py` — export Quota
- Create: `scripts/seed_quotas.py` — seed 2026 quota data

**Step 1: Add Quota model to models.py**

Add at the end of `sis/db/models.py` (before any final exports):

```python
class Quota(Base):
    __tablename__ = "quotas"

    id = Column(Text, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    period = Column(Text, nullable=False)    # "2026" for annual
    amount = Column(Float, nullable=False)   # Annual quota in USD
    created_at = Column(Text, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(Text, default=lambda: datetime.utcnow().isoformat())

    __table_args__ = (
        UniqueConstraint('user_id', 'period', name='uq_quota_user_period'),
    )
```

Make sure `uuid4` is imported from `uuid` and `UniqueConstraint` from `sqlalchemy`.

**Step 2: Register in __init__.py**

Add `Quota` to the imports in `sis/db/__init__.py`.

**Step 3: Create seed script**

```python
# scripts/seed_quotas.py
"""Seed 2026 annual quotas for all ICs."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sis.db import get_session
from sis.db.models import Quota, User

QUOTAS_2026 = {
    "Nadine Barchecht": 104_750,
    "Omer Snir": 104_750,
    "Stefania Fanari": 104_750,
    "Keiko Navon": 125_700,
    "Nicholas Kirtley": 125_700,
    "Dror Gross": 104_750,
    "Uriel Ross": 104_750,
    "Yos Jacobs": 104_750,
    "Lei Bao": 83_800,
    "Wenze Li": 83_800,
    "ZhenYu Qiao": 83_800,
}

def seed():
    db = get_session()
    try:
        for name, amount in QUOTAS_2026.items():
            user = db.query(User).filter(User.name == name).first()
            if not user:
                print(f"WARNING: User '{name}' not found, skipping")
                continue
            existing = db.query(Quota).filter(
                Quota.user_id == user.id, Quota.period == "2026"
            ).first()
            if existing:
                existing.amount = amount
                print(f"Updated: {name} → ${amount:,.0f}")
            else:
                db.add(Quota(user_id=user.id, period="2026", amount=amount))
                print(f"Created: {name} → ${amount:,.0f}")
        db.commit()
        print(f"\nSeeded {len(QUOTAS_2026)} quotas for 2026")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
```

**Step 4: Create the table and seed**

Run:
```bash
cd /Users/roylevierez/Documents/Sales/SIS
python -c "from sis.db.models import Base; from sis.db import engine; Base.metadata.create_all(engine)"
python scripts/seed_quotas.py
```
Expected: "Seeded 11 quotas for 2026"

**Step 5: Verify the data**

Run:
```bash
python -c "
from sis.db import get_session
from sis.db.models import Quota
db = get_session()
for q in db.query(Quota).all():
    print(f'{q.user_id}: {q.period} = \${q.amount:,.0f}')
db.close()
"
```
Expected: 11 rows printed

**Step 6: Commit**

```bash
git add sis/db/models.py sis/db/__init__.py scripts/seed_quotas.py
git commit -m "feat(quota): add Quota model and seed 2026 annual quotas for 11 ICs"
```

---

### Task 7: Quota API endpoints

**Files:**
- Create: `sis/api/routes/quotas.py`
- Modify: `sis/api/main.py` — register the new router

**Step 1: Create the quotas route file**

```python
# sis/api/routes/quotas.py
"""Quota endpoints — read quotas, admin create/update."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from sis.db import get_session
from sis.db.models import Quota, User, Team
from sis.api.routes.auth import get_current_user

router = APIRouter(prefix="/api/quotas", tags=["quotas"])


class QuotaResponse(BaseModel):
    user_id: str
    user_name: str
    period: str
    amount: float


class QuotaCreate(BaseModel):
    user_id: str
    period: str
    amount: float


def _rollup_quota(db: Session, user_id: str, period: str) -> float:
    """Compute quota for a user: own quota if IC, sum of subordinates otherwise."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 0.0

    # IC: direct quota
    own = db.query(Quota).filter(
        Quota.user_id == user_id, Quota.period == period
    ).first()

    if user.role == "ic":
        return own.amount if own else 0.0

    # Team lead / VP / GM / Admin: sum subordinate quotas
    # Find all teams this user leads
    led_teams = db.query(Team).filter(Team.leader_id == user_id).all()
    total = 0.0
    for team in led_teams:
        members = db.query(User).filter(User.team_id == team.id).all()
        for member in members:
            total += _rollup_quota(db, member.id, period)
    return total


@router.get("/{user_id}")
def get_quota(
    user_id: str,
    period: str = "2026",
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    amount = _rollup_quota(db, user_id, period)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return QuotaResponse(
        user_id=user_id,
        user_name=user.name,
        period=period,
        amount=amount,
    )


@router.get("/team/{team_id}")
def get_team_quota(
    team_id: str,
    period: str = "2026",
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = db.query(User).filter(User.team_id == team_id).all()
    total = sum(_rollup_quota(db, m.id, period) for m in members)
    return {"team_id": team_id, "team_name": team.name, "period": period, "amount": total}


@router.post("/")
def upsert_quota(
    data: QuotaCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    existing = db.query(Quota).filter(
        Quota.user_id == data.user_id, Quota.period == data.period
    ).first()
    if existing:
        existing.amount = data.amount
    else:
        db.add(Quota(user_id=data.user_id, period=data.period, amount=data.amount))
    db.commit()
    return {"ok": True}
```

**Step 2: Register in main.py**

Add to `sis/api/main.py`:
```python
from sis.api.routes import quotas
app.include_router(quotas.router)
```

**Step 3: Test the endpoints**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && python -m uvicorn sis.api.main:app --reload --port 8000`

Then in another terminal:
```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","role":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Get a user's quota
curl -s http://localhost:8000/api/quotas/<IC_USER_ID>?period=2026 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Expected: Returns `{ "user_id": "...", "user_name": "...", "period": "2026", "amount": 104750 }`

**Step 4: Commit**

```bash
git add sis/api/routes/quotas.py sis/api/main.py
git commit -m "feat(quota): add GET/POST quota endpoints with hierarchy rollup"
```

---

### Task 8: Command Center backend endpoint

**Files:**
- Modify: `sis/services/dashboard_service.py` — add `get_command_center()` function
- Modify: `sis/api/routes/dashboard.py` — add `/api/dashboard/command-center` route

**Step 1: Add the command center service function**

Add to `sis/services/dashboard_service.py`:

```python
def get_command_center(
    db: Session,
    visible_user_ids: set[str] | None,
    period: str = "2026",
    quarter: str | None = None,     # "Q1", "Q2", "Q3", "Q4", or None for full year
    team_id: str | None = None,
    ae_name: str | None = None,
) -> dict:
    """
    Aggregated command center data:
    - quota + pipeline totals
    - forecast breakdown (commit/realistic/upside/risk)
    - attention items (declining, divergent, stale)
    - weekly changes
    - all deals (for table)
    - team grid (for VP+)
    """
    from sis.db.models import Account, DealAssessment, AnalysisRun, Quota, User, Team
    from sqlalchemy import func, and_

    # --- Base query: latest assessment per account ---
    latest_run_sq = (
        db.query(
            AnalysisRun.account_id,
            func.max(AnalysisRun.completed_at).label("max_completed"),
        )
        .filter(AnalysisRun.status == "completed")
        .group_by(AnalysisRun.account_id)
        .subquery()
    )

    query = (
        db.query(Account, DealAssessment, AnalysisRun)
        .join(AnalysisRun, Account.id == AnalysisRun.account_id)
        .join(DealAssessment, AnalysisRun.id == DealAssessment.run_id)
        .join(
            latest_run_sq,
            and_(
                AnalysisRun.account_id == latest_run_sq.c.account_id,
                AnalysisRun.completed_at == latest_run_sq.c.max_completed,
            ),
        )
    )

    # Scope by visible users
    if visible_user_ids is not None:
        query = query.filter(Account.owner_id.in_(visible_user_ids))

    # Filter by team
    if team_id:
        team_user_ids = {u.id for u in db.query(User).filter(User.team_id == team_id).all()}
        # Also include sub-teams (VP selecting sees child teams)
        child_teams = db.query(Team).filter(Team.parent_id == team_id).all()
        for ct in child_teams:
            team_user_ids |= {u.id for u in db.query(User).filter(User.team_id == ct.id).all()}
        query = query.filter(Account.owner_id.in_(team_user_ids))

    # Filter by AE
    if ae_name:
        query = query.filter(Account.ae_owner == ae_name)

    results = query.all()

    # --- Build deals list ---
    deals = []
    for acct, assessment, run in results:
        deals.append({
            "account_id": acct.id,
            "account_name": acct.account_name,
            "mrr_estimate": acct.mrr_estimate or 0,
            "team_name": acct.team_name,
            "team_lead": acct.team_lead,
            "ae_owner": acct.ae_owner,
            "deal_type": acct.deal_type,
            "ic_forecast_category": acct.ic_forecast_category,
            "last_call_date": _latest_call_date(db, acct.id),
            "health_score": assessment.health_score,
            "momentum_direction": assessment.momentum_direction,
            "ai_forecast_category": assessment.ai_forecast_category,
            "inferred_stage": assessment.inferred_stage,
            "stage_name": assessment.stage_name,
            "overall_confidence": assessment.confidence_overall if hasattr(assessment, 'confidence_overall') else None,
            "divergence_flag": assessment.divergence_flag or False,
            "deal_memo_preview": (assessment.deal_memo or "")[:200],
        })

    # --- Forecast breakdown ---
    forecast_map = {"commit": [], "realistic": [], "upside": [], "risk": []}
    for d in deals:
        cat = (d["ai_forecast_category"] or "").lower().replace(" ", "_").replace("at_risk", "risk")
        if cat in forecast_map:
            forecast_map[cat].append(d["mrr_estimate"])
        else:
            forecast_map["risk"].append(d["mrr_estimate"])

    forecast_breakdown = {}
    for cat, values in forecast_map.items():
        forecast_breakdown[cat] = {"count": len(values), "value": sum(values)}

    # --- Pipeline totals ---
    total_value = sum(d["mrr_estimate"] for d in deals)
    weighted = (
        sum(forecast_map["commit"]) * 0.90
        + sum(forecast_map["realistic"]) * 0.60
        + sum(forecast_map["upside"]) * 0.30
        + sum(forecast_map["risk"]) * 0.10
    )

    # --- Quota ---
    # If team_id or ae_name provided, scope the quota appropriately
    quota_amount = 0.0
    if visible_user_ids is not None and len(visible_user_ids) > 0:
        quotas = db.query(Quota).filter(
            Quota.user_id.in_(visible_user_ids),
            Quota.period == period,
        ).all()
        quota_amount = sum(q.amount for q in quotas)
    else:
        # All quotas for the org
        quotas = db.query(Quota).filter(Quota.period == period).all()
        quota_amount = sum(q.amount for q in quotas)

    # Quarter adjustment: divide by 4
    if quarter and quarter.startswith("Q"):
        quota_amount = quota_amount / 4.0

    coverage = (total_value / quota_amount) if quota_amount > 0 else 0
    gap = weighted - quota_amount

    # --- Attention items ---
    attention = _compute_attention_items(db, deals, results)

    # --- Changes this week ---
    changes = _compute_weekly_changes(db, visible_user_ids)

    return {
        "quota": {"amount": quota_amount, "period": quarter or period},
        "pipeline": {
            "total_value": total_value,
            "total_deals": len(deals),
            "coverage": round(coverage, 2),
            "weighted_value": round(weighted, 0),
            "gap": round(gap, 0),
        },
        "forecast_breakdown": forecast_breakdown,
        "attention_items": attention[:5],
        "changes_this_week": changes,
        "deals": deals,
    }


def _latest_call_date(db, account_id: str) -> str | None:
    """Get the most recent call date for an account."""
    from sis.db.models import Transcript
    t = db.query(Transcript.call_date).filter(
        Transcript.account_id == account_id,
        Transcript.is_active == 1,
    ).order_by(Transcript.call_date.desc()).first()
    return t[0] if t else None


def _compute_attention_items(db, deals: list, raw_results: list) -> list:
    """Identify deals needing VP attention: declining, divergent, stale."""
    from datetime import datetime, timedelta

    items = []
    now = datetime.utcnow()

    for d in deals:
        reasons = []

        # Declining health
        if d["momentum_direction"] == "declining":
            reasons.append(f"Health declining, score {d['health_score'] or 'N/A'}")

        # Divergent forecast
        if d["divergence_flag"]:
            ai = d["ai_forecast_category"] or "N/A"
            ic = d["ic_forecast_category"] or "N/A"
            reasons.append(f"AI: {ai}, IC: {ic} (divergent)")

        # Stale: no call in 14+ days
        if d["last_call_date"]:
            try:
                last = datetime.fromisoformat(d["last_call_date"].replace("Z", ""))
                days_ago = (now - last).days
                if days_ago >= 14:
                    reasons.append(f"No activity {days_ago} days")
            except (ValueError, TypeError):
                pass

        if reasons:
            items.append({
                "account_id": d["account_id"],
                "account_name": d["account_name"],
                "mrr_estimate": d["mrr_estimate"],
                "reason": reasons[0],  # Primary reason
                "type": "declining" if "declining" in reasons[0].lower() else
                        "divergent" if "divergent" in reasons[0].lower() else "stale",
            })

    # Sort by MRR descending (highest-dollar items first)
    items.sort(key=lambda x: x["mrr_estimate"], reverse=True)
    return items


def _compute_weekly_changes(db, visible_user_ids: set[str] | None) -> dict:
    """Compare current vs previous-week assessments to compute pipeline changes."""
    # Stub for Phase 2 — returns placeholder values for now
    return {
        "added": 0,
        "dropped": 0,
        "net": 0,
        "stage_advances": 0,
        "forecast_flips": 0,
        "new_risks": 0,
    }
```

**Step 2: Add the route**

Add to `sis/api/routes/dashboard.py`:

```python
@router.get("/command-center")
def command_center(
    team: str | None = None,
    ae: str | None = None,
    period: str = "2026",
    quarter: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    visible = _resolve_scoping(user, db)
    return dashboard_service.get_command_center(
        db=db,
        visible_user_ids=visible,
        period=period,
        quarter=quarter,
        team_id=team,
        ae_name=ae,
    )
```

**Step 3: Test the endpoint**

```bash
curl -s http://localhost:8000/api/dashboard/command-center?quarter=Q1 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Expected: JSON with quota, pipeline, forecast_breakdown, attention_items, changes_this_week, deals

**Step 4: Commit**

```bash
git add sis/services/dashboard_service.py sis/api/routes/dashboard.py
git commit -m "feat(api): add /dashboard/command-center endpoint with quota, forecast, attention"
```

---

### Task 9: Frontend types and data hook for Command Center

**Files:**
- Modify: `frontend/src/lib/pipeline-types.ts` — add CommandCenter types
- Modify: `frontend/src/lib/api.ts` — add `commandCenter()` API call
- Modify: `frontend/src/lib/api-types.ts` — add types
- Create: `frontend/src/lib/hooks/use-command-center.ts`

**Step 1: Add TypeScript types**

Add to `frontend/src/lib/pipeline-types.ts`:

```typescript
export interface CommandCenterQuota {
  amount: number;
  period: string;
}

export interface CommandCenterPipeline {
  total_value: number;
  total_deals: number;
  coverage: number;
  weighted_value: number;
  gap: number;
}

export interface ForecastCategory {
  count: number;
  value: number;
}

export interface ForecastBreakdown {
  commit: ForecastCategory;
  realistic: ForecastCategory;
  upside: ForecastCategory;
  risk: ForecastCategory;
}

export interface AttentionItem {
  account_id: string;
  account_name: string;
  mrr_estimate: number;
  reason: string;
  type: 'declining' | 'divergent' | 'stale';
}

export interface WeeklyChanges {
  added: number;
  dropped: number;
  net: number;
  stage_advances: number;
  forecast_flips: number;
  new_risks: number;
}

export interface CommandCenterResponse {
  quota: CommandCenterQuota;
  pipeline: CommandCenterPipeline;
  forecast_breakdown: ForecastBreakdown;
  attention_items: AttentionItem[];
  changes_this_week: WeeklyChanges;
  deals: PipelineDeal[];
}
```

**Step 2: Add API method**

Add to `api.dashboard` in `frontend/src/lib/api.ts`:

```typescript
commandCenter: (params?: { team?: string; ae?: string; period?: string; quarter?: string }) => {
  const searchParams = new URLSearchParams();
  if (params?.team) searchParams.set('team', params.team);
  if (params?.ae) searchParams.set('ae', params.ae);
  if (params?.period) searchParams.set('period', params.period);
  if (params?.quarter) searchParams.set('quarter', params.quarter);
  const qs = searchParams.toString();
  return apiFetch<CommandCenterResponse>(`/api/dashboard/command-center${qs ? `?${qs}` : ''}`);
},
```

Import `CommandCenterResponse` from pipeline-types at the top of the file (or add to api-types).

**Step 3: Create the hook**

```typescript
// frontend/src/lib/hooks/use-command-center.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

interface CommandCenterParams {
  team?: string;
  ae?: string;
  period?: string;
  quarter?: string;
}

export function useCommandCenter(params?: CommandCenterParams) {
  return useQuery({
    queryKey: ['dashboard', 'command-center', params],
    queryFn: () => api.dashboard.commandCenter(params),
    staleTime: 30_000,     // 30s before refetch
    refetchInterval: 60_000, // Auto-refetch every 60s
  });
}
```

**Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

**Step 5: Commit**

```bash
git add frontend/src/lib/pipeline-types.ts frontend/src/lib/api.ts frontend/src/lib/hooks/use-command-center.ts
git commit -m "feat(frontend): add CommandCenter types, API method, and React Query hook"
```

---

### Task 10: Install TanStack Table

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install the dependency**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend
npm install @tanstack/react-table
```

**Step 2: Verify installation**

Run: `npm ls @tanstack/react-table`
Expected: Shows installed version (8.x or 9.x)

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: install @tanstack/react-table for deal table"
```

---

### Task 11: Build the Number Line component

**Files:**
- Create: `frontend/src/components/number-line.tsx`

**Step 1: Create the Number Line component**

```tsx
// frontend/src/components/number-line.tsx
'use client';

import type { CommandCenterPipeline, CommandCenterQuota, ForecastBreakdown } from '@/lib/pipeline-types';

interface NumberLineProps {
  quota: CommandCenterQuota;
  pipeline: CommandCenterPipeline;
  forecast: ForecastBreakdown;
}

function formatDollar(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function KpiItem({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="text-2xl font-bold font-mono tabular-nums text-foreground sm:text-3xl">
        {value}
      </span>
      {subtext && (
        <span className="text-xs text-muted-foreground">{subtext}</span>
      )}
    </div>
  );
}

function DistributionBar({ forecast }: { forecast: ForecastBreakdown }) {
  const total =
    forecast.commit.value +
    forecast.realistic.value +
    forecast.upside.value +
    forecast.risk.value;
  if (total === 0) return null;

  const segments = [
    { key: 'commit', label: 'Commit', value: forecast.commit.value, color: 'bg-forecast-commit' },
    { key: 'realistic', label: 'Realistic', value: forecast.realistic.value, color: 'bg-forecast-realistic' },
    { key: 'upside', label: 'Upside', value: forecast.upside.value, color: 'bg-forecast-upside' },
    { key: 'risk', label: 'Risk', value: forecast.risk.value, color: 'bg-forecast-risk' },
  ];

  return (
    <div className="space-y-1.5">
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        {segments.map((seg) => {
          const pct = (seg.value / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={seg.key}
              className={`${seg.color} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${seg.label}: ${formatDollar(seg.value)} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        {segments.map((seg) => (
          <span key={seg.key}>
            {seg.label} {formatDollar(seg.value)}
          </span>
        ))}
      </div>
    </div>
  );
}

export function NumberLine({ quota, pipeline, forecast }: NumberLineProps) {
  const gapSign = pipeline.gap >= 0 ? '+' : '';
  const gapColor = pipeline.gap >= 0 ? 'text-healthy' : 'text-critical';
  const coverageColor =
    pipeline.coverage >= 3 ? 'text-healthy' :
    pipeline.coverage >= 2 ? 'text-at-risk' :
    'text-critical';

  return (
    <div className="rounded-xl border bg-brand-50/50 p-5 space-y-4">
      {/* KPI Row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <KpiItem label="Quota" value={formatDollar(quota.amount)} subtext={quota.period} />
        <KpiItem label="Pipeline" value={formatDollar(pipeline.total_value)} subtext={`${pipeline.total_deals} deals`} />
        <div className="flex flex-col items-center">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Coverage
          </span>
          <span className={`text-2xl font-bold font-mono tabular-nums sm:text-3xl ${coverageColor}`}>
            {pipeline.coverage.toFixed(1)}x
          </span>
        </div>
        <KpiItem label="Weighted" value={formatDollar(pipeline.weighted_value)} />
        <div className="flex flex-col items-center">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Gap
          </span>
          <span className={`text-2xl font-bold font-mono tabular-nums sm:text-3xl ${gapColor}`}>
            {gapSign}{formatDollar(Math.abs(pipeline.gap))}
          </span>
          <span className="text-xs text-muted-foreground">
            {pipeline.gap >= 0 ? 'above quota' : 'below quota'}
          </span>
        </div>
      </div>

      {/* Distribution Bar */}
      <DistributionBar forecast={forecast} />
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add frontend/src/components/number-line.tsx
git commit -m "feat(ui): add Number Line component with KPIs and forecast distribution bar"
```

---

### Task 12: Build the Filter Chips component

**Files:**
- Create: `frontend/src/components/filter-chips.tsx`

**Step 1: Create the filter chips component**

```tsx
// frontend/src/components/filter-chips.tsx
'use client';

import { cn } from '@/lib/utils';
import type { ForecastBreakdown } from '@/lib/pipeline-types';

export type ForecastFilter = 'all' | 'commit' | 'realistic' | 'upside' | 'risk';
export type HealthFilter = 'healthy' | 'at_risk' | 'critical';
export type FlagFilter = 'divergent' | 'stale' | 'declining';

interface FilterChipsProps {
  forecast: ForecastBreakdown;
  totalDeals: number;
  activeForecast: ForecastFilter;
  activeHealth: HealthFilter[];
  activeFlags: FlagFilter[];
  onForecastChange: (filter: ForecastFilter) => void;
  onHealthToggle: (filter: HealthFilter) => void;
  onFlagToggle: (filter: FlagFilter) => void;
  onClearAll: () => void;
  /** Counts for health tiers (from deal list) */
  healthCounts: { healthy: number; at_risk: number; critical: number };
  /** Counts for flags (from deal list) */
  flagCounts: { divergent: number; stale: number; declining: number };
}

function Chip({
  label,
  count,
  active,
  colorClass,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  colorClass: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? `${colorClass} text-white shadow-sm`
          : 'bg-muted text-muted-foreground hover:bg-muted/80'
      )}
    >
      {label}
      <span className={cn(
        'inline-flex items-center justify-center rounded-full px-1.5 text-[10px] font-semibold min-w-[20px]',
        active ? 'bg-white/20 text-white' : 'bg-background text-foreground'
      )}>
        {count}
      </span>
    </button>
  );
}

export function FilterChips({
  forecast,
  totalDeals,
  activeForecast,
  activeHealth,
  activeFlags,
  onForecastChange,
  onHealthToggle,
  onFlagToggle,
  onClearAll,
  healthCounts,
  flagCounts,
}: FilterChipsProps) {
  const hasActiveFilters =
    activeForecast !== 'all' || activeHealth.length > 0 || activeFlags.length > 0;

  return (
    <div className="space-y-2">
      {/* Row 1: Forecast category */}
      <div className="flex flex-wrap items-center gap-2">
        <Chip label="All" count={totalDeals} active={activeForecast === 'all'} colorClass="bg-foreground" onClick={() => onForecastChange('all')} />
        <Chip label="Commit" count={forecast.commit.count} active={activeForecast === 'commit'} colorClass="bg-forecast-commit" onClick={() => onForecastChange('commit')} />
        <Chip label="Realistic" count={forecast.realistic.count} active={activeForecast === 'realistic'} colorClass="bg-forecast-realistic" onClick={() => onForecastChange('realistic')} />
        <Chip label="Upside" count={forecast.upside.count} active={activeForecast === 'upside'} colorClass="bg-forecast-upside" onClick={() => onForecastChange('upside')} />
        <Chip label="Risk" count={forecast.risk.count} active={activeForecast === 'risk'} colorClass="bg-forecast-risk" onClick={() => onForecastChange('risk')} />

        <span className="mx-1 text-border">|</span>

        {/* Health overlay */}
        <Chip label="Healthy" count={healthCounts.healthy} active={activeHealth.includes('healthy')} colorClass="bg-healthy" onClick={() => onHealthToggle('healthy')} />
        <Chip label="At Risk" count={healthCounts.at_risk} active={activeHealth.includes('at_risk')} colorClass="bg-at-risk" onClick={() => onHealthToggle('at_risk')} />
        <Chip label="Critical" count={healthCounts.critical} active={activeHealth.includes('critical')} colorClass="bg-critical" onClick={() => onHealthToggle('critical')} />

        <span className="mx-1 text-border">|</span>

        {/* Flags */}
        <Chip label="Divergent" count={flagCounts.divergent} active={activeFlags.includes('divergent')} colorClass="bg-at-risk" onClick={() => onFlagToggle('divergent')} />
        <Chip label="Stale" count={flagCounts.stale} active={activeFlags.includes('stale')} colorClass="bg-muted-foreground" onClick={() => onFlagToggle('stale')} />
        <Chip label="Declining" count={flagCounts.declining} active={activeFlags.includes('declining')} colorClass="bg-critical" onClick={() => onFlagToggle('declining')} />

        {hasActiveFilters && (
          <button
            onClick={onClearAll}
            className="text-xs text-muted-foreground hover:text-foreground underline ml-2"
          >
            Clear all
          </button>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/components/filter-chips.tsx
git commit -m "feat(ui): add FilterChips component with forecast, health, and flag toggles"
```

---

### Task 13: Build the TanStack Table-based deal table

**Files:**
- Create: `frontend/src/components/data-table.tsx`

**Step 1: Create the data table component**

This is the largest component. It uses `@tanstack/react-table` for sorting, filtering, pagination, and column visibility.

```tsx
// frontend/src/components/data-table.tsx
'use client';

import { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { HealthBadge } from '@/components/health-badge';
import { MomentumIndicator } from '@/components/momentum-indicator';
import { ForecastBadge } from '@/components/forecast-badge';
import type { PipelineDeal } from '@/lib/pipeline-types';

function formatMrr(value: number | null): string {
  if (!value) return '$0';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function daysAgo(dateStr: string | null): string {
  if (!dateStr) return 'N/A';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff === 0) return 'Today';
  if (diff === 1) return '1d ago';
  return `${diff}d ago`;
}

function daysAgoColor(dateStr: string | null): string {
  if (!dateStr) return 'text-muted-foreground';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff <= 7) return 'text-healthy';
  if (diff <= 14) return 'text-at-risk';
  return 'text-critical';
}

function healthTier(score: number | null): string {
  if (score === null) return '';
  if (score >= 70) return 'healthy';
  if (score >= 45) return 'at_risk';
  return 'critical';
}

function rowTintClass(deal: PipelineDeal): string {
  const tier = healthTier(deal.health_score);
  if (tier === 'critical') return 'bg-critical-light/40';
  if (tier === 'at_risk') return 'bg-at-risk-light/30';
  return '';
}

export const dealColumns: ColumnDef<PipelineDeal>[] = [
  {
    accessorKey: 'account_name',
    header: 'Account',
    cell: ({ row }) => {
      const deal = row.original;
      return (
        <div className="min-w-[160px]">
          <a
            href={`/deals/${deal.account_id}`}
            className="font-medium text-foreground hover:text-primary hover:underline"
          >
            {deal.account_name}
          </a>
          {deal.ae_owner && (
            <div className="text-xs text-muted-foreground">{deal.ae_owner}</div>
          )}
        </div>
      );
    },
    size: 200,
  },
  {
    accessorKey: 'mrr_estimate',
    header: 'MRR',
    cell: ({ getValue }) => (
      <span className="font-mono tabular-nums text-right">
        {formatMrr(getValue() as number | null)}
      </span>
    ),
    size: 90,
  },
  {
    accessorKey: 'deal_type',
    header: 'Type',
    cell: ({ getValue }) => {
      const val = getValue() as string | null;
      if (!val) return <span className="text-muted-foreground">—</span>;
      return (
        <span className={cn(
          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
          val.toLowerCase() === 'expansion'
            ? 'bg-brand-100 text-brand-700'
            : 'bg-muted text-muted-foreground'
        )}>
          {val}
        </span>
      );
    },
    size: 80,
  },
  {
    accessorKey: 'stage_name',
    header: 'Stage',
    cell: ({ getValue, row }) => {
      const name = getValue() as string | null;
      const num = row.original.inferred_stage;
      return (
        <span className="text-sm">
          {name || (num ? `S${num}` : '—')}
        </span>
      );
    },
    size: 100,
  },
  {
    id: 'forecast',
    header: 'Forecast',
    cell: ({ row }) => {
      const deal = row.original;
      const ai = deal.ai_forecast_category;
      const ic = deal.ic_forecast_category;
      const divergent = deal.divergence_flag;

      return (
        <div className={cn(
          'flex flex-col gap-0.5',
          divergent && 'rounded px-1.5 py-0.5 bg-at-risk-light/50'
        )}>
          <ForecastBadge category={ai} />
          {divergent && ic && (
            <span className="text-[10px] text-at-risk">
              IC: {ic}
            </span>
          )}
        </div>
      );
    },
    size: 120,
  },
  {
    accessorKey: 'health_score',
    header: 'Health',
    cell: ({ getValue }) => (
      <HealthBadge score={getValue() as number | null} />
    ),
    size: 80,
  },
  {
    accessorKey: 'momentum_direction',
    header: 'Momentum',
    cell: ({ getValue }) => (
      <MomentumIndicator direction={getValue() as string | null} />
    ),
    size: 90,
  },
  {
    accessorKey: 'overall_confidence',
    header: 'Conf.',
    cell: ({ getValue }) => {
      const val = getValue() as number | null;
      if (val === null || val === undefined) return <span className="text-muted-foreground">—</span>;
      return (
        <span className="font-mono tabular-nums text-sm">
          {(val * 100).toFixed(0)}%
        </span>
      );
    },
    size: 60,
  },
  {
    accessorKey: 'last_call_date',
    header: 'Last Call',
    cell: ({ getValue }) => {
      const val = getValue() as string | null;
      return (
        <span className={cn('text-sm', daysAgoColor(val))}>
          {daysAgo(val)}
        </span>
      );
    },
    size: 80,
  },
];

interface DataTableProps {
  deals: PipelineDeal[];
  pageSize?: number;
}

export function DataTable({ deals, pageSize = 25 }: DataTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'mrr_estimate', desc: true },
  ]);

  const table = useReactTable({
    data: deals,
    columns: dealColumns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize },
    },
  });

  return (
    <div>
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/30">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap cursor-pointer select-none hover:bg-muted/50"
                    onClick={header.column.getToggleSortingHandler()}
                    style={{ width: header.getSize() }}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      <ArrowUpDown className="size-3 text-muted-foreground/50" />
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={dealColumns.length} className="h-24 text-center text-muted-foreground">
                  No deals found
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row, idx) => (
                <TableRow
                  key={row.id}
                  className={cn(
                    'transition-colors hover:bg-brand-50/50',
                    idx % 2 === 1 && 'bg-muted/15',
                    rowTintClass(row.original),
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="whitespace-normal align-top py-2.5">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between px-2 py-3">
          <span className="text-xs text-muted-foreground">
            Showing {table.getState().pagination.pageIndex * pageSize + 1}–
            {Math.min(
              (table.getState().pagination.pageIndex + 1) * pageSize,
              deals.length,
            )}{' '}
            of {deals.length} deals
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronLeft className="size-4" />
            </Button>
            <span className="text-sm font-medium">
              {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

**Step 3: Commit**

```bash
git add frontend/src/components/data-table.tsx
git commit -m "feat(ui): add TanStack Table-based DataTable with sort, pagination, urgency tinting"
```

---

### Task 14: Build the Pipeline Command Center page

**Files:**
- Modify: `frontend/src/app/pipeline/page.tsx` — complete rewrite

**Step 1: Rewrite the pipeline page**

This is the main assembly — it wires the Number Line, Filter Chips, and DataTable together using the Command Center hook.

```tsx
// frontend/src/app/pipeline/page.tsx
'use client';

import { useState, useMemo, useCallback } from 'react';
import { useCommandCenter } from '@/lib/hooks/use-command-center';
import { usePermissions } from '@/lib/permissions';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { NumberLine } from '@/components/number-line';
import {
  FilterChips,
  type ForecastFilter,
  type HealthFilter,
  type FlagFilter,
} from '@/components/filter-chips';
import { DataTable } from '@/components/data-table';
import type { PipelineDeal } from '@/lib/pipeline-types';

// ---------------------------------------------------------------------------
// Quarter helper
// ---------------------------------------------------------------------------

function currentQuarter(): string {
  const m = new Date().getMonth(); // 0-indexed
  if (m < 3) return 'Q1';
  if (m < 6) return 'Q2';
  if (m < 9) return 'Q3';
  return 'Q4';
}

const QUARTER_OPTIONS = [
  { value: 'Q1', label: 'Q1 2026' },
  { value: 'Q2', label: 'Q2 2026' },
  { value: 'Q3', label: 'Q3 2026' },
  { value: 'Q4', label: 'Q4 2026' },
  { value: 'FY', label: 'Full Year 2026' },
];

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-32 animate-pulse rounded-xl bg-muted" />
      <div className="flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 w-20 animate-pulse rounded-full bg-muted" />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-lg bg-muted" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Deal filtering logic
// ---------------------------------------------------------------------------

function healthTier(score: number | null): 'healthy' | 'at_risk' | 'critical' | null {
  if (score === null) return null;
  if (score >= 70) return 'healthy';
  if (score >= 45) return 'at_risk';
  return 'critical';
}

function isStale(deal: PipelineDeal): boolean {
  if (!deal.last_call_date) return true;
  const d = new Date(deal.last_call_date);
  const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  return diff >= 14;
}

function filterDeals(
  deals: PipelineDeal[],
  forecastFilter: ForecastFilter,
  healthFilters: HealthFilter[],
  flagFilters: FlagFilter[],
): PipelineDeal[] {
  return deals.filter((d) => {
    // Forecast filter
    if (forecastFilter !== 'all') {
      const cat = (d.ai_forecast_category || '').toLowerCase().replace(' ', '_').replace('at_risk', 'risk');
      if (cat !== forecastFilter) return false;
    }

    // Health filter (intersection — any selected must match)
    if (healthFilters.length > 0) {
      const tier = healthTier(d.health_score);
      if (!tier || !healthFilters.includes(tier)) return false;
    }

    // Flag filters (intersection — all selected must match)
    if (flagFilters.length > 0) {
      for (const flag of flagFilters) {
        if (flag === 'divergent' && !d.divergence_flag) return false;
        if (flag === 'declining' && d.momentum_direction !== 'declining') return false;
        if (flag === 'stale' && !isStale(d)) return false;
      }
    }

    return true;
  });
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PipelineCommandCenter() {
  const [quarter, setQuarter] = useState(currentQuarter());
  const [team, setTeam] = useState<string | undefined>(undefined);
  const [forecastFilter, setForecastFilter] = useState<ForecastFilter>('all');
  const [healthFilters, setHealthFilters] = useState<HealthFilter[]>([]);
  const [flagFilters, setFlagFilters] = useState<FlagFilter[]>([]);

  const { isVpOrAbove } = usePermissions();

  const { data, isLoading, isError, error } = useCommandCenter({
    quarter: quarter === 'FY' ? undefined : quarter,
    team,
  });

  // Compute health & flag counts from all deals (before filtering)
  const counts = useMemo(() => {
    if (!data) return { health: { healthy: 0, at_risk: 0, critical: 0 }, flags: { divergent: 0, stale: 0, declining: 0 } };
    const deals = data.deals;
    return {
      health: {
        healthy: deals.filter((d) => healthTier(d.health_score) === 'healthy').length,
        at_risk: deals.filter((d) => healthTier(d.health_score) === 'at_risk').length,
        critical: deals.filter((d) => healthTier(d.health_score) === 'critical').length,
      },
      flags: {
        divergent: deals.filter((d) => d.divergence_flag).length,
        stale: deals.filter((d) => isStale(d)).length,
        declining: deals.filter((d) => d.momentum_direction === 'declining').length,
      },
    };
  }, [data]);

  // Filtered deals for the table
  const filteredDeals = useMemo(() => {
    if (!data) return [];
    return filterDeals(data.deals, forecastFilter, healthFilters, flagFilters);
  }, [data, forecastFilter, healthFilters, flagFilters]);

  const handleHealthToggle = useCallback((h: HealthFilter) => {
    setHealthFilters((prev) =>
      prev.includes(h) ? prev.filter((x) => x !== h) : [...prev, h]
    );
  }, []);

  const handleFlagToggle = useCallback((f: FlagFilter) => {
    setFlagFilters((prev) =>
      prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]
    );
  }, []);

  const clearAllFilters = useCallback(() => {
    setForecastFilter('all');
    setHealthFilters([]);
    setFlagFilters([]);
  }, []);

  return (
    <div className="p-6 space-y-5 max-w-[1400px] mx-auto">
      {/* ── Header ── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pipeline Command Center</h1>
          <p className="text-sm text-muted-foreground">
            {data
              ? `${data.pipeline.total_deals} deals across your pipeline`
              : 'Loading...'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Quarter filter */}
          <Select value={quarter} onValueChange={setQuarter}>
            <SelectTrigger className="w-[140px] bg-brand-50 border-brand-200">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {QUARTER_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Team / VP filter */}
          <Select
            value={team ?? 'all'}
            onValueChange={(v) => setTeam(v === 'all' ? undefined : v)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Teams" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Teams</SelectItem>
              {/* TODO: populate from backend team hierarchy */}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* ── Loading ── */}
      {isLoading && <LoadingSkeleton />}

      {/* ── Error ── */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load pipeline data</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* ── Data ── */}
      {data && !isLoading && (
        <>
          {/* Number Line */}
          <NumberLine
            quota={data.quota}
            pipeline={data.pipeline}
            forecast={data.forecast_breakdown}
          />

          {/* Filter Chips */}
          <FilterChips
            forecast={data.forecast_breakdown}
            totalDeals={data.pipeline.total_deals}
            activeForecast={forecastFilter}
            activeHealth={healthFilters}
            activeFlags={flagFilters}
            onForecastChange={setForecastFilter}
            onHealthToggle={handleHealthToggle}
            onFlagToggle={handleFlagToggle}
            onClearAll={clearAllFilters}
            healthCounts={counts.health}
            flagCounts={counts.flags}
          />

          {/* Deal Table */}
          <DataTable deals={filteredDeals} />
        </>
      )}
    </div>
  );
}
```

**Step 2: Verify the app loads**

Run: `cd frontend && npm run dev`
Navigate to `/pipeline`
Expected: Command Center page loads with Number Line, Filter Chips, and DataTable. If backend is running, real data populates. If not, loading/error state shows.

**Step 3: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): rewrite Pipeline page as Command Center with Number Line, filters, DataTable"
```

---

## Phase 2 — Intelligence Layer

### Task 15: Build the Attention Strip component

**Files:**
- Create: `frontend/src/components/attention-strip.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/attention-strip.tsx
'use client';

import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AttentionItem } from '@/lib/pipeline-types';

interface AttentionStripProps {
  items: AttentionItem[];
}

function formatMrr(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function typeIcon(type: string): string {
  switch (type) {
    case 'declining': return '↓';
    case 'divergent': return '⇄';
    case 'stale': return '⏸';
    default: return '•';
  }
}

export function AttentionStrip({ items }: AttentionStripProps) {
  const [expanded, setExpanded] = useState(items.length > 0);

  if (items.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-healthy/30 bg-healthy-light/30 px-4 py-3">
        <CheckCircle className="size-4 text-healthy" />
        <span className="text-sm font-medium text-healthy">All clear — no deals need immediate attention</span>
      </div>
    );
  }

  const totalAtRisk = items.reduce((sum, i) => sum + i.mrr_estimate, 0);

  return (
    <div className="rounded-lg border-l-4 border-l-at-risk border bg-card">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="size-4 text-at-risk" />
          <span className="text-sm font-semibold">
            {items.length} {items.length === 1 ? 'deal needs' : 'deals need'} attention
          </span>
          <span className="text-sm text-muted-foreground">
            ({formatMrr(totalAtRisk)} at risk)
          </span>
        </div>
        {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
      </button>

      {/* Items */}
      {expanded && (
        <div className="border-t divide-y">
          {items.map((item) => (
            <div key={item.account_id} className="flex items-center gap-3 px-4 py-2.5">
              <span className="text-sm">{typeIcon(item.type)}</span>
              <a
                href={`/deals/${item.account_id}`}
                className="text-sm font-medium hover:text-primary hover:underline"
              >
                {item.account_name}
              </a>
              <span className="font-mono text-sm tabular-nums text-muted-foreground">
                {formatMrr(item.mrr_estimate)}
              </span>
              <span className="text-xs text-muted-foreground flex-1">
                — {item.reason}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Wire into the Command Center page**

Add to `frontend/src/app/pipeline/page.tsx`, between the Number Line and Filter Chips:

```tsx
import { AttentionStrip } from '@/components/attention-strip';

// Inside the data section, after NumberLine:
<AttentionStrip items={data.attention_items} />
```

**Step 3: Verify it renders**

Run: `cd frontend && npm run dev`
Expected: Attention strip shows between Number Line and Filter Chips.

**Step 4: Commit**

```bash
git add frontend/src/components/attention-strip.tsx frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): add Attention Strip component for deals needing VP action"
```

---

### Task 16: Build the Pipeline Changes strip

**Files:**
- Create: `frontend/src/components/pipeline-changes.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/pipeline-changes.tsx
'use client';

import { TrendingUp, TrendingDown, ArrowRight, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WeeklyChanges } from '@/lib/pipeline-types';

interface PipelineChangesProps {
  changes: WeeklyChanges;
}

function formatDollar(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function Metric({
  label,
  value,
  icon: Icon,
  colorClass,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  colorClass: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className={cn('size-3.5', colorClass)} />
      <span className={cn('text-sm font-semibold tabular-nums', colorClass)}>{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function PipelineChanges({ changes }: PipelineChangesProps) {
  const allZero = Object.values(changes).every((v) => v === 0);
  if (allZero) return null;

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        This week
      </span>
      <Metric label="added" value={`+${formatDollar(changes.added)}`} icon={TrendingUp} colorClass="text-healthy" />
      <Metric label="dropped" value={`-${formatDollar(changes.dropped)}`} icon={TrendingDown} colorClass="text-critical" />
      <Metric
        label="net"
        value={`${changes.net >= 0 ? '+' : ''}${formatDollar(changes.net)}`}
        icon={ArrowRight}
        colorClass={changes.net >= 0 ? 'text-healthy' : 'text-critical'}
      />
      <span className="text-border">|</span>
      <span className="text-xs text-muted-foreground">
        {changes.stage_advances} advances · {changes.forecast_flips} flips · {changes.new_risks} new risks
      </span>
    </div>
  );
}
```

**Step 2: Wire into the Command Center page**

Add between Attention Strip and Filter Chips:

```tsx
import { PipelineChanges } from '@/components/pipeline-changes';

// After AttentionStrip:
<PipelineChanges changes={data.changes_this_week} />
```

**Step 3: Verify and commit**

```bash
git add frontend/src/components/pipeline-changes.tsx frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): add Pipeline Changes strip showing weekly delta metrics"
```

---

### Task 17: Build the Team Forecast Grid (VP+ only)

**Files:**
- Create: `frontend/src/components/team-forecast-grid.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/team-forecast-grid.tsx
'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import type { PipelineDeal } from '@/lib/pipeline-types';

interface TeamForecastGridProps {
  deals: PipelineDeal[];
  onTeamClick?: (teamLead: string) => void;
}

interface TeamRow {
  team_lead: string;
  commit: number;
  realistic: number;
  upside: number;
  risk: number;
  total: number;
  deals: number;
}

function formatMrr(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function buildTeamRows(deals: PipelineDeal[]): TeamRow[] {
  const map = new Map<string, TeamRow>();

  for (const deal of deals) {
    const lead = deal.team_lead || 'Unassigned';
    if (!map.has(lead)) {
      map.set(lead, {
        team_lead: lead,
        commit: 0,
        realistic: 0,
        upside: 0,
        risk: 0,
        total: 0,
        deals: 0,
      });
    }
    const row = map.get(lead)!;
    const mrr = deal.mrr_estimate || 0;
    const cat = (deal.ai_forecast_category || '').toLowerCase().replace(' ', '_').replace('at_risk', 'risk');

    if (cat === 'commit') row.commit += mrr;
    else if (cat === 'realistic') row.realistic += mrr;
    else if (cat === 'upside') row.upside += mrr;
    else row.risk += mrr;

    row.total += mrr;
    row.deals += 1;
  }

  return Array.from(map.values()).sort((a, b) => b.total - a.total);
}

export function TeamForecastGrid({ deals, onTeamClick }: TeamForecastGridProps) {
  const rows = buildTeamRows(deals);

  if (rows.length === 0) return null;

  // Totals row
  const totals = rows.reduce(
    (acc, r) => ({
      commit: acc.commit + r.commit,
      realistic: acc.realistic + r.realistic,
      upside: acc.upside + r.upside,
      risk: acc.risk + r.risk,
      total: acc.total + r.total,
      deals: acc.deals + r.deals,
    }),
    { commit: 0, realistic: 0, upside: 0, risk: 0, total: 0, deals: 0 },
  );

  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Team Forecast
      </h2>
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap">Team</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Commit</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Realistic</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Upside</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Risk</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Total</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Deals</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={row.team_lead}
                className={cn(
                  'transition-colors',
                  onTeamClick && 'cursor-pointer hover:bg-brand-50/50',
                )}
                onClick={() => onTeamClick?.(row.team_lead)}
              >
                <TableCell className="font-medium whitespace-nowrap">{row.team_lead}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-commit">{formatMrr(row.commit)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-realistic">{formatMrr(row.realistic)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-upside">{formatMrr(row.upside)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-risk">{formatMrr(row.risk)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums font-semibold">{formatMrr(row.total)}</TableCell>
                <TableCell className="text-right text-muted-foreground">{row.deals}</TableCell>
              </TableRow>
            ))}
            {/* Totals */}
            <TableRow className="bg-muted/20 font-semibold border-t-2">
              <TableCell>Total</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.commit)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.realistic)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.upside)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.risk)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.total)}</TableCell>
              <TableCell className="text-right">{totals.deals}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
```

**Step 2: Wire into the Command Center page (VP+ only)**

Add after the DataTable:

```tsx
import { TeamForecastGrid } from '@/components/team-forecast-grid';

// Inside the data section, after DataTable:
{isVpOrAbove && (
  <TeamForecastGrid deals={data.deals} />
)}
```

**Step 3: Verify and commit**

```bash
git add frontend/src/components/team-forecast-grid.tsx frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): add Team Forecast Grid for VP+ with forecast × team matrix"
```

---

### Task 18: Final assembly — wire all sections into Command Center page

**Files:**
- Modify: `frontend/src/app/pipeline/page.tsx` — ensure all imports and section ordering match the design

**Step 1: Verify the final page has all sections in order**

The final section order should be:
1. Header with Quarter + Team filters
2. Number Line (quota, pipeline, coverage, weighted, gap, distribution bar)
3. Attention Strip (collapsible, amber border)
4. Pipeline Changes (weekly delta metrics)
5. Filter Chips (forecast + health + flags)
6. DataTable (TanStack Table with sort, pagination)
7. Team Forecast Grid (VP+ only)

Make sure all imports are present and the sections are rendered in this order. The previous tasks may have added sections incrementally — this task ensures the final ordering is correct.

**Step 2: Run the full app**

Start both backend and frontend:
```bash
# Terminal 1: Backend
cd /Users/roylevierez/Documents/Sales/SIS && python -m uvicorn sis.api.main:app --reload --port 8000

# Terminal 2: Frontend
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run dev
```

**Step 3: Test the complete flow**

1. Login as admin → navigate to `/pipeline`
2. Verify Number Line shows quota, pipeline, coverage, weighted, gap
3. Verify Attention Strip shows deals needing attention (or "All clear")
4. Verify Pipeline Changes shows this week's metrics
5. Verify Filter Chips work: click Commit → table filters to Commit deals only
6. Verify DataTable: sort by MRR, paginate, check urgency tinting
7. Verify Team Forecast Grid shows at bottom (VP+ users only)
8. Change Quarter dropdown → all sections update
9. Change Team dropdown → data scopes to that team

**Step 4: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

**Step 5: Commit**

```bash
git add frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): finalize Command Center page with all sections wired"
```

---

### Task 19: Polish — sticky Number Line and clean up old components

**Files:**
- Modify: `frontend/src/app/pipeline/page.tsx` — make Number Line sticky
- Delete content from: `frontend/src/components/pipeline-movers.tsx` — no longer used

**Step 1: Make Number Line sticky on scroll**

Wrap the NumberLine in a sticky container. In the pipeline page, change:

```tsx
{/* Number Line — sticky on scroll */}
<div className="sticky top-0 z-10">
  <NumberLine
    quota={data.quota}
    pipeline={data.pipeline}
    forecast={data.forecast_breakdown}
  />
</div>
```

Note: On mobile (with the `pt-16` padding for hamburger), adjust the sticky top offset:
```tsx
<div className="sticky top-0 lg:top-0 z-10">
```

**Step 2: Mark pipeline-movers.tsx as deprecated**

Replace the content of `frontend/src/components/pipeline-movers.tsx` with a simple redirect note, or just leave it unused (the new pipeline page no longer imports it):

```tsx
// frontend/src/components/pipeline-movers.tsx
// DEPRECATED: Replaced by attention-strip.tsx and pipeline-changes.tsx
// Safe to delete once verified.
export function PipelineMovers() {
  return null;
}
```

**Step 3: Verify and commit**

```bash
git add frontend/src/app/pipeline/page.tsx frontend/src/components/pipeline-movers.tsx
git commit -m "feat(ui): sticky Number Line on scroll, deprecate pipeline-movers"
```

---

### Task 20: Implement weekly changes backend logic

**Files:**
- Modify: `sis/services/dashboard_service.py` — replace `_compute_weekly_changes` stub with real logic

**Step 1: Implement the real weekly changes computation**

Replace the stub `_compute_weekly_changes` function with:

```python
def _compute_weekly_changes(db, visible_user_ids: set[str] | None) -> dict:
    """Compare current vs previous-week assessments for weekly pipeline movement."""
    from sis.db.models import Account, DealAssessment, AnalysisRun
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta

    one_week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    # Get all completed runs
    runs_query = db.query(AnalysisRun).filter(AnalysisRun.status == "completed")

    # Current: latest run per account
    latest_sq = (
        db.query(
            AnalysisRun.account_id,
            func.max(AnalysisRun.completed_at).label("max_c"),
        )
        .filter(AnalysisRun.status == "completed")
        .group_by(AnalysisRun.account_id)
        .subquery()
    )

    # Previous: latest run completed before 1 week ago
    prev_sq = (
        db.query(
            AnalysisRun.account_id,
            func.max(AnalysisRun.completed_at).label("max_c"),
        )
        .filter(
            AnalysisRun.status == "completed",
            AnalysisRun.completed_at < one_week_ago,
        )
        .group_by(AnalysisRun.account_id)
        .subquery()
    )

    # Fetch current assessments
    current = {}
    for run, assessment in (
        db.query(AnalysisRun, DealAssessment)
        .join(DealAssessment, AnalysisRun.id == DealAssessment.run_id)
        .join(latest_sq, and_(
            AnalysisRun.account_id == latest_sq.c.account_id,
            AnalysisRun.completed_at == latest_sq.c.max_c,
        ))
        .all()
    ):
        current[run.account_id] = {
            "mrr": db.query(Account.mrr_estimate).filter(Account.id == run.account_id).scalar() or 0,
            "stage": assessment.inferred_stage,
            "forecast": assessment.ai_forecast_category,
            "health": assessment.health_score,
        }

    # Fetch previous week assessments
    previous = {}
    for run, assessment in (
        db.query(AnalysisRun, DealAssessment)
        .join(DealAssessment, AnalysisRun.id == DealAssessment.run_id)
        .join(prev_sq, and_(
            AnalysisRun.account_id == prev_sq.c.account_id,
            AnalysisRun.completed_at == prev_sq.c.max_c,
        ))
        .all()
    ):
        previous[run.account_id] = {
            "stage": assessment.inferred_stage,
            "forecast": assessment.ai_forecast_category,
            "health": assessment.health_score,
        }

    # Compute deltas
    added = sum(d["mrr"] for aid, d in current.items() if aid not in previous)
    dropped = 0  # Would need tracking "lost" deals — placeholder
    stage_advances = 0
    forecast_flips = 0
    new_risks = 0

    for aid, cur in current.items():
        prev = previous.get(aid)
        if not prev:
            continue
        if cur["stage"] and prev["stage"] and cur["stage"] > prev["stage"]:
            stage_advances += 1
        if cur["forecast"] != prev["forecast"]:
            forecast_flips += 1
        cur_health = cur.get("health") or 100
        prev_health = prev.get("health") or 100
        if cur_health < 45 and prev_health >= 45:
            new_risks += 1

    return {
        "added": round(added, 0),
        "dropped": round(dropped, 0),
        "net": round(added - dropped, 0),
        "stage_advances": stage_advances,
        "forecast_flips": forecast_flips,
        "new_risks": new_risks,
    }
```

**Step 2: Test**

Run: `curl -s http://localhost:8000/api/dashboard/command-center -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['changes_this_week'], indent=2))"`

Expected: Real numbers instead of all zeros.

**Step 3: Commit**

```bash
git add sis/services/dashboard_service.py
git commit -m "feat(api): implement real weekly pipeline changes computation"
```

---

### Task 21: Populate the Team / VP filter dropdown from backend

**Files:**
- Modify: `frontend/src/app/pipeline/page.tsx` — fetch team hierarchy for dropdown

**Step 1: Fetch the team list and build hierarchical dropdown**

Use the existing `api.teams.list()` endpoint to populate the dropdown. Replace the `TODO` comment in the Select with:

```tsx
// At the top of PipelineCommandCenter, add:
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

// Inside PipelineCommandCenter function:
const { data: teamsData } = useQuery({
  queryKey: ['teams'],
  queryFn: () => api.teams.list(),
});

// In the Team Select's SelectContent, replace the TODO:
<SelectContent>
  <SelectItem value="all">All Teams</SelectItem>
  {teamsData && teamsData.length > 0 && (
    <>
      {/* VP-level groups */}
      <SelectGroup>
        <SelectLabel className="text-[10px] uppercase tracking-wider">VPs</SelectLabel>
        {teamsData
          .filter((t: any) => t.level === 'division')
          .map((t: any) => (
            <SelectItem key={t.id} value={t.id}>
              {t.leader_name || t.name}
            </SelectItem>
          ))}
      </SelectGroup>
      {/* Team-level */}
      <SelectGroup>
        <SelectLabel className="text-[10px] uppercase tracking-wider">Teams</SelectLabel>
        {teamsData
          .filter((t: any) => t.level === 'team')
          .map((t: any) => (
            <SelectItem key={t.id} value={t.id}>
              {t.leader_name || t.name}
            </SelectItem>
          ))}
      </SelectGroup>
    </>
  )}
</SelectContent>
```

**Step 2: Verify the dropdown populates**

Run: `cd frontend && npm run dev`
Navigate to `/pipeline`, open the team dropdown.
Expected: Shows "VPs" section with Roy/Gili, "Teams" section with Lisa L/Lachlan/Bar Barda/Ying.

**Step 3: Commit**

```bash
git add frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): populate Team/VP filter dropdown from backend hierarchy"
```

---

## Summary

| Phase | Tasks | Key Deliverables |
|-------|-------|-----------------|
| **Phase 0** | 1–5 | Inter font, Riskified green palette, dark sidebar, branded logo, simplified nav, semantic tokens, /deals redirect |
| **Phase 1** | 6–14 | Quota DB + API, Command Center endpoint, TypeScript types + hook, TanStack Table install, Number Line, Filter Chips, DataTable, Pipeline page rewrite |
| **Phase 2** | 15–21 | Attention Strip, Pipeline Changes, Team Forecast Grid, sticky Number Line, real weekly changes backend, hierarchical team dropdown |

**Total: 21 tasks, ~50 commits**

Each task is 2-10 minutes of focused work. The page is shippable after each phase:
- After Phase 0: App looks branded (green sidebar, Inter font) but pipeline page is still old layout
- After Phase 1: Pipeline Command Center is live with Number Line, filters, and new table
- After Phase 2: Full intelligence layer with attention queue, changes strip, and team grid
