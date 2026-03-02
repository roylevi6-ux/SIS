# Manager Actions Panel + Widget Config Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface manager_insight from agent findings as a consolidated panel, then make all deal page widgets toggleable and reorderable per user.

**Architecture:** Frontend-only extraction for manager insights (data already in API response). New `user_preferences` DB table + API endpoints for widget config. Deal page refactored from hardcoded layout to dynamic widget registry. Config page at `/settings/display` with drag-and-drop + toggles.

**Tech Stack:** Next.js 16, React 19, shadcn/ui, @dnd-kit/sortable, FastAPI, SQLAlchemy, Alembic, SQLite

---

## Task 1: Manager Actions Panel Component

**Files:**
- Create: `frontend/src/components/manager-actions-panel.tsx`

**Step 1: Create the ManagerActionsPanel component**

This component receives the agent analyses array (already fetched by the deal page) and extracts `manager_insight` from each agent's `findings` object.

```tsx
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { AgentAnalysis } from '@/components/agent-card';

// Friendly display names for agent IDs
const AGENT_LABELS: Record<string, string> = {
  agent_0e_account_health: 'Account Health',
  agent_1_stage_progress: 'Stage & Progress',
  agent_2_relationship: 'Relationship',
  agent_3_commercial_risk: 'Commercial',
  agent_4_momentum: 'Momentum',
  agent_5_technical: 'Technical',
  agent_6_economic_buyer: 'Economic Buyer',
  agent_7_msp_next_steps: 'Next Steps',
  agent_8_competitive: 'Competitive',
};

interface ManagerActionsPanelProps {
  agents: AgentAnalysis[];
}

export function ManagerActionsPanel({ agents }: ManagerActionsPanelProps) {
  const insights = agents
    .filter((a) => a.findings && typeof a.findings === 'object' && (a.findings as Record<string, unknown>).manager_insight)
    .map((a) => ({
      agentId: a.agent_id ?? a.id,
      agentLabel: AGENT_LABELS[a.agent_id ?? ''] ?? a.agent_name,
      insight: String((a.findings as Record<string, unknown>).manager_insight),
    }));

  if (insights.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Manager Actions This Week</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {insights.map((item) => (
            <li key={item.agentId} className="flex items-start gap-2 text-sm">
              <Badge variant="outline" className="shrink-0 mt-0.5 text-xs">
                {item.agentLabel}
              </Badge>
              <span className="leading-relaxed">{item.insight}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Verify it compiles**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx next build --no-lint 2>&1 | tail -5`
Expected: Build succeeds (component isn't imported yet, just check for syntax errors)

**Step 3: Commit**

```bash
git add frontend/src/components/manager-actions-panel.tsx
git commit -m "feat: add ManagerActionsPanel component"
```

---

## Task 2: Wire Manager Actions into Deal Page

**Files:**
- Modify: `frontend/src/app/deals/[id]/page.tsx` (lines 346-383 for AgentAnalysesSection, lines 679-765 for assessment content)

**Step 1: Import the component and expose agent data**

At the top of `page.tsx`, add the import:
```tsx
import { ManagerActionsPanel } from '@/components/manager-actions-panel';
```

**Step 2: Extract agents from AgentAnalysesSection for the panel**

The challenge: agents are fetched inside `AgentAnalysesSection` but `ManagerActionsPanel` needs them at the parent level. Lift the agent fetch to the deal page level.

Add a new hook call in the main `DealDetailPage` component (around line 500-505), right after the existing hooks:

```tsx
// Fetch agent analyses for Manager Actions panel
const { data: historyData } = useAnalysisHistory(id);
const historyRuns = (historyData ?? []) as AnalysisRun[];
const latestCompletedRun = historyRuns.find((r) => r.status === 'completed') ?? historyRuns[0];
const { data: agentData } = useAgentAnalyses(latestCompletedRun?.run_id ?? '');
const agentList = (agentData ?? []) as AgentAnalysis[];
```

Note: `AgentAnalysesSection` already does this same fetch internally. We'll refactor it to accept agents as props instead. Update `AgentAnalysesSection` to accept optional pre-fetched agents:

```tsx
function AgentAnalysesSection({ agents, healthBreakdown }: { agents: AgentAnalysis[]; healthBreakdown?: unknown }) {
  if (agents.length === 0) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Per-Agent Analysis</h2>
      <div className="space-y-2">
        {agents.map((agent) => (
          <AgentCard key={agent.agent_id} analysis={agent} healthBreakdown={healthBreakdown as HealthBreakdownEntry[] | null} />
        ))}
      </div>
    </div>
  );
}
```

**Step 3: Add ManagerActionsPanel to the assessment section**

Insert after `<DealMemo>` (around line 682):

```tsx
{/* Manager Actions */}
<ManagerActionsPanel agents={agentList} />
```

Update the `AgentAnalysesSection` call (around line 763):
```tsx
<AgentAnalysesSection agents={agentList} healthBreakdown={assessment.health_breakdown} />
```

**Step 4: Verify it works**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/src/app/deals/\\[id\\]/page.tsx
git commit -m "feat: wire ManagerActionsPanel into deal detail page"
```

---

## Task 3: Backend — UserPreference Model + Migration

**Files:**
- Modify: `sis/db/models.py` (add UserPreference class after User class, around line 52)
- Create: `alembic/versions/d6f8a0b2c4e7_add_user_preferences.py`

**Step 1: Add UserPreference model to models.py**

Insert after the User class `__table_args__` (after line 52):

```python
# ─── user_preferences ─────────────────────────────────────────────────


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    preference_key = Column(Text, nullable=False)
    preference_value = Column(Text, nullable=False)  # JSON string
    updated_at = Column(Text, nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "preference_key", name="uq_user_preference"),
        Index("ix_user_preferences_user", "user_id"),
    )
```

**Step 2: Create Alembic migration**

Create file `alembic/versions/d6f8a0b2c4e7_add_user_preferences.py`:

```python
"""add_user_preferences

Revision ID: d6f8a0b2c4e7
Revises: c5e7f9a1b3d6
Create Date: 2026-03-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6f8a0b2c4e7'
down_revision: Union[str, Sequence[str], None] = 'c5e7f9a1b3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('preference_key', sa.Text(), nullable=False),
        sa.Column('preference_value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'preference_key', name='uq_user_preference'),
    )
    op.create_index('ix_user_preferences_user', 'user_preferences', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_preferences_user', table_name='user_preferences')
    op.drop_table('user_preferences')
```

**Step 3: Run migration**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Verify table exists**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "from sis.db.session import get_session; s = next(get_session().__iter__()); print(s.execute(__import__('sqlalchemy').text('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"user_preferences\"')).fetchone())"`
Expected: `('user_preferences',)`

**Step 5: Commit**

```bash
git add sis/db/models.py alembic/versions/d6f8a0b2c4e7_add_user_preferences.py
git commit -m "feat: add user_preferences table with Alembic migration"
```

---

## Task 4: Backend — Preferences API Endpoints

**Files:**
- Create: `sis/api/routes/preferences.py`
- Modify: `sis/api/main.py` (add router include, line ~72)

**Step 1: Create preferences route**

```python
"""User preferences API routes."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sis.api.deps import get_current_user, get_db
from sis.db.models import UserPreference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


# Default widget configuration
DEFAULT_DEAL_WIDGETS = [
    {"id": "status_strip", "label": "Status Strip", "description": "Health, stage, forecast, and confidence badges", "visible": True, "order": 0},
    {"id": "call_timeline", "label": "Call Timeline", "description": "Chronological view of all calls", "visible": True, "order": 1},
    {"id": "what_changed", "label": "What Changed", "description": "Metric deltas between latest and previous run", "visible": True, "order": 2},
    {"id": "deal_memo", "label": "Deal Memo", "description": "TL Insider Brief and Leadership Summary", "visible": True, "order": 3},
    {"id": "manager_actions", "label": "Manager Actions", "description": "Consolidated weekly action items from all agents", "visible": True, "order": 4},
    {"id": "health_breakdown", "label": "Health Breakdown", "description": "Radar chart and score table for health components", "visible": True, "order": 5},
    {"id": "actions_risks", "label": "Actions & Risks", "description": "Recommended actions and risk signals", "visible": True, "order": 6},
    {"id": "positive_contradictions", "label": "Signals & Contradictions", "description": "Positive signals and contradiction map", "visible": True, "order": 7},
    {"id": "forecast_divergence", "label": "Forecast Divergence", "description": "AI vs IC forecast divergence explanation", "visible": True, "order": 8},
    {"id": "key_unknowns", "label": "Key Unknowns", "description": "Outstanding questions and unknowns", "visible": True, "order": 9},
    {"id": "forecast_rationale", "label": "Forecast Rationale", "description": "Reasoning behind the AI forecast", "visible": True, "order": 10},
    {"id": "sf_gap", "label": "SF Gap Analysis", "description": "SIS vs Salesforce stage and forecast comparison", "visible": True, "order": 11},
    {"id": "agent_analyses", "label": "Per-Agent Analysis", "description": "Collapsible cards for each agent's findings", "visible": True, "order": 12},
    {"id": "deal_timeline", "label": "Deal Timeline", "description": "Assessment history trend chart", "visible": True, "order": 13},
    {"id": "analysis_history", "label": "Analysis History", "description": "List of past analysis runs", "visible": True, "order": 14},
    {"id": "transcript_list", "label": "Transcripts", "description": "All uploaded transcripts for this account", "visible": True, "order": 15},
]


class PreferenceUpdate(BaseModel):
    value: dict | list


def _get_user_id_from_token(user: dict, db) -> str | None:
    """Resolve JWT sub (username) to users.id."""
    from sis.db.models import User
    row = db.query(User).filter(User.name == user["sub"]).first()
    return row.id if row else None


@router.get("/{key}")
def get_preference(key: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = _get_user_id_from_token(user, db)
    if not user_id:
        # Return default for unknown users
        if key == "deal_page_widgets":
            return {"widgets": DEFAULT_DEAL_WIDGETS}
        return {"value": None}

    pref = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.preference_key == key,
    ).first()

    if not pref:
        if key == "deal_page_widgets":
            return {"widgets": DEFAULT_DEAL_WIDGETS}
        return {"value": None}

    return json.loads(pref.preference_value)


@router.put("/{key}")
def save_preference(key: str, body: PreferenceUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = _get_user_id_from_token(user, db)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    pref = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.preference_key == key,
    ).first()

    value_json = json.dumps(body.value)

    if pref:
        pref.preference_value = value_json
        pref.updated_at = datetime.now(timezone.utc).isoformat()
    else:
        pref = UserPreference(
            user_id=user_id,
            preference_key=key,
            preference_value=value_json,
        )
        db.add(pref)

    db.commit()
    return json.loads(pref.preference_value)
```

**Step 2: Register router in main.py**

Add import and include_router in `sis/api/main.py`:

```python
from sis.api.routes import preferences
# ...
app.include_router(preferences.router)
```

**Step 3: Test the endpoint manually**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m uvicorn sis.api.main:app --port 8000 &`
Then: `curl -s http://localhost:8000/api/preferences/deal_page_widgets -H "Authorization: Bearer $(python -c 'from sis.api.auth import create_token; print(create_token("Roy Levi", "admin"))')" | python -m json.tool | head -10`
Expected: Returns default widget config JSON

**Step 4: Commit**

```bash
git add sis/api/routes/preferences.py sis/api/main.py
git commit -m "feat: add preferences API endpoints (GET/PUT)"
```

---

## Task 5: Frontend — Preferences Hook + API Client

**Files:**
- Modify: `frontend/src/lib/api.ts` (add preferences endpoints, around line 267)
- Create: `frontend/src/lib/hooks/use-preferences.ts`

**Step 1: Add preferences to API client**

Add after the `gdrive` section in `api.ts` (around line 267):

```typescript
preferences: {
  get: (key: string) => apiFetch<any>(`/api/preferences/${key}`),
  save: (key: string, value: any) =>
    apiFetch<any>(`/api/preferences/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    }),
},
```

**Step 2: Create the preferences hook**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export interface WidgetConfig {
  id: string;
  label: string;
  description: string;
  visible: boolean;
  order: number;
}

export function useDealPageWidgets() {
  return useQuery({
    queryKey: ['preferences', 'deal_page_widgets'],
    queryFn: async () => {
      const data = await api.preferences.get('deal_page_widgets');
      return (data.widgets ?? []) as WidgetConfig[];
    },
    staleTime: 5 * 60 * 1000, // 5 min — prefs don't change often
  });
}

export function useSaveDealPageWidgets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (widgets: WidgetConfig[]) =>
      api.preferences.save('deal_page_widgets', { widgets }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['preferences', 'deal_page_widgets'] }),
  });
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/hooks/use-preferences.ts
git commit -m "feat: add preferences API client and React hook"
```

---

## Task 6: Frontend — Display Settings Page

**Files:**
- Create: `frontend/src/app/settings/display/page.tsx`
- Modify: `frontend/src/components/sidebar.tsx` (add nav item, line ~93)

**Step 1: Install @dnd-kit dependencies**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities`

**Step 2: Install shadcn Switch component**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npx shadcn@latest add switch`

**Step 3: Create the settings page**

Create `frontend/src/app/settings/display/page.tsx`:

```tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, RotateCcw, Check } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { useDealPageWidgets, useSaveDealPageWidgets, type WidgetConfig } from '@/lib/hooks/use-preferences';

function SortableWidget({
  widget,
  onToggle,
}: {
  widget: WidgetConfig;
  onToggle: (id: string, visible: boolean) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3"
    >
      <button
        className="cursor-grab touch-none text-muted-foreground hover:text-foreground"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="size-4" />
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{widget.label}</p>
        <p className="text-xs text-muted-foreground">{widget.description}</p>
      </div>
      <Switch
        checked={widget.visible}
        onCheckedChange={(checked) => onToggle(widget.id, checked)}
      />
    </div>
  );
}

export default function DisplaySettingsPage() {
  const { data: serverWidgets, isLoading } = useDealPageWidgets();
  const saveMutation = useSaveDealPageWidgets();
  const [widgets, setWidgets] = useState<WidgetConfig[]>([]);
  const [saved, setSaved] = useState(false);

  // Sync server data to local state
  useEffect(() => {
    if (serverWidgets && widgets.length === 0) {
      setWidgets([...serverWidgets].sort((a, b) => a.order - b.order));
    }
  }, [serverWidgets, widgets.length]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const save = useCallback(
    (updated: WidgetConfig[]) => {
      const reordered = updated.map((w, i) => ({ ...w, order: i }));
      setWidgets(reordered);
      saveMutation.mutate(reordered, {
        onSuccess: () => {
          setSaved(true);
          setTimeout(() => setSaved(false), 2000);
        },
      });
    },
    [saveMutation],
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = widgets.findIndex((w) => w.id === active.id);
    const newIndex = widgets.findIndex((w) => w.id === over.id);
    const moved = arrayMove(widgets, oldIndex, newIndex);
    save(moved);
  };

  const handleToggle = (id: string, visible: boolean) => {
    const updated = widgets.map((w) =>
      w.id === id ? { ...w, visible } : w,
    );
    save(updated);
  };

  const handleReset = () => {
    if (serverWidgets) {
      // Re-fetch defaults from server by saving null — or just use original order
      const defaults = serverWidgets.map((w, i) => ({
        ...w,
        visible: true,
        order: i,
      }));
      save(defaults);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 w-48 rounded bg-muted" />
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg border bg-muted/20" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Display Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Customize which widgets appear on deal pages and their order.
          Drag to reorder, toggle to show or hide.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-base">Deal Page Widgets</CardTitle>
          <div className="flex items-center gap-2">
            {saved && (
              <span className="text-xs text-emerald-600 flex items-center gap-1">
                <Check className="size-3" /> Saved
              </span>
            )}
            <Button variant="outline" size="sm" onClick={handleReset}>
              <RotateCcw className="size-3.5 mr-1" />
              Reset
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={widgets.map((w) => w.id)}
              strategy={verticalListSortingStrategy}
            >
              {widgets.map((widget) => (
                <SortableWidget
                  key={widget.id}
                  widget={widget}
                  onToggle={handleToggle}
                />
              ))}
            </SortableContext>
          </DndContext>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 4: Add sidebar navigation item**

In `frontend/src/components/sidebar.tsx`, add to the Admin group items (after line 93, the Team Management item):

```tsx
{ label: 'Display Settings', href: '/settings/display', icon: Settings },
```

Note: This item has no `minRole` so it's visible to all roles (everyone can customize their own view).

**Step 5: Build and verify**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 6: Commit**

```bash
git add frontend/src/app/settings/display/page.tsx frontend/src/components/sidebar.tsx
git commit -m "feat: add /settings/display page with drag-and-drop widget config"
```

---

## Task 7: Refactor Deal Page to Dynamic Widget Rendering

**Files:**
- Modify: `frontend/src/app/deals/[id]/page.tsx`

This is the key refactor: change the deal page from a hardcoded sequence of widgets to a dynamic loop based on user preferences.

**Step 1: Add the widget registry and dynamic renderer**

Import the preferences hook:
```tsx
import { useDealPageWidgets, type WidgetConfig } from '@/lib/hooks/use-preferences';
```

Add the preferences hook call inside `DealDetailPage` (after existing hooks):
```tsx
const { data: widgetPrefs } = useDealPageWidgets();
```

Create a helper to get visible, ordered widget IDs:
```tsx
function getVisibleWidgets(prefs: WidgetConfig[] | undefined): string[] {
  if (!prefs) {
    // Default order when preferences haven't loaded
    return [
      'status_strip', 'call_timeline', 'what_changed', 'deal_memo',
      'manager_actions', 'health_breakdown', 'actions_risks',
      'positive_contradictions', 'forecast_divergence', 'key_unknowns',
      'forecast_rationale', 'sf_gap', 'agent_analyses', 'deal_timeline',
      'analysis_history', 'transcript_list',
    ];
  }
  return prefs
    .filter((w) => w.visible)
    .sort((a, b) => a.order - b.order)
    .map((w) => w.id);
}
```

**Step 2: Create a renderWidget function**

Inside `DealDetailPage`, create a function that maps widget IDs to their JSX. Each widget checks its own prerequisites (e.g., assessment must exist):

```tsx
function renderWidget(widgetId: string) {
  switch (widgetId) {
    case 'status_strip':
      // Status strip is part of the header — always rendered there, not in the dynamic section
      return null;
    case 'call_timeline':
      return account.transcripts?.length > 0 ? (
        <CallTimeline key={widgetId} transcripts={account.transcripts} />
      ) : null;
    case 'what_changed':
      return <WhatChangedCard key={widgetId} accountId={id} />;
    case 'deal_memo':
      return assessment ? <DealMemo key={widgetId} memo={assessment.deal_memo} /> : null;
    case 'manager_actions':
      return assessment ? <ManagerActionsPanel key={widgetId} agents={agentList} /> : null;
    case 'health_breakdown':
      return assessment ? (
        <HealthBreakdown key={widgetId} breakdown={assessment.health_breakdown} healthScore={assessment.health_score} />
      ) : null;
    case 'actions_risks':
      return assessment ? (
        <div key={widgetId} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ActionsList actions={assessment.recommended_actions} />
          <SignalsList title="Risk Signals" items={assessment.top_risks} icon={<AlertTriangle className="size-3.5 text-amber-500" />} emptyText="No risks identified." />
        </div>
      ) : null;
    case 'positive_contradictions':
      return assessment ? (
        <div key={widgetId} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SignalsList title="Positive Signals" items={assessment.top_positive_signals} icon={<span className="text-emerald-500">+</span>} emptyText="No positive signals." />
          <SignalsList title="Contradictions" items={assessment.contradiction_map} icon={<Zap className="size-3.5 text-purple-500" />} emptyText="No contradictions detected." />
        </div>
      ) : null;
    case 'forecast_divergence':
      return assessment?.divergence_flag && assessment.divergence_explanation ? (
        <Card key={widgetId} className="border-amber-200 dark:border-amber-800">
          <CardHeader><CardTitle className="text-base flex items-center gap-2"><AlertTriangle className="size-4 text-amber-500" />Forecast Divergence</CardTitle></CardHeader>
          <CardContent><p className="text-sm">{assessment.divergence_explanation}</p></CardContent>
        </Card>
      ) : null;
    case 'key_unknowns':
      return assessment?.key_unknowns?.length > 0 ? (
        <Card key={widgetId}>
          <CardHeader><CardTitle className="text-base">Key Unknowns</CardTitle></CardHeader>
          <CardContent><ul className="list-disc list-inside text-sm space-y-1">{assessment.key_unknowns.map((u, i) => <li key={i}>{u}</li>)}</ul></CardContent>
        </Card>
      ) : null;
    case 'forecast_rationale':
      return assessment?.forecast_rationale ? (
        <Card key={widgetId}>
          <CardHeader><CardTitle className="text-base">Forecast Rationale</CardTitle></CardHeader>
          <CardContent><p className="text-sm leading-relaxed">{assessment.forecast_rationale}</p></CardContent>
        </Card>
      ) : null;
    case 'sf_gap':
      return assessment ? <SFGapCard key={widgetId} assessment={assessment} /> : null;
    case 'agent_analyses':
      return assessment ? (
        <AgentAnalysesSection key={widgetId} agents={agentList} healthBreakdown={assessment.health_breakdown} />
      ) : null;
    case 'deal_timeline':
      return <DealTimeline key={widgetId} accountId={id} />;
    case 'analysis_history':
      return <AnalysisHistorySection key={widgetId} accountId={id} />;
    case 'transcript_list':
      return <TranscriptListSection key={widgetId} transcripts={account.transcripts ?? []} />;
    default:
      return null;
  }
}
```

**Step 3: Replace the hardcoded layout with the dynamic loop**

Replace the entire return block (lines 541-779) — everything after the header and separator stays. The header (Back link, title, status strip, meta info, feedback button) stays hardcoded since it's essential context. The `{!assessment && <NoAssessmentState>}` stays too.

Replace the section from `{/* ---- Call Timeline ---- */}` through the end with:

```tsx
{/* ---- Dynamic widget layout ---- */}
{!assessment && <NoAssessmentState accountName={account.account_name} />}
{getVisibleWidgets(widgetPrefs).map((widgetId) => renderWidget(widgetId))}
```

**Step 4: Build and verify**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 5: Manually verify in browser**

Run backend + frontend, open a deal page, confirm all widgets appear in default order. Then go to `/settings/display`, hide one widget, return to the deal page, and confirm it's gone.

**Step 6: Commit**

```bash
git add frontend/src/app/deals/\\[id\\]/page.tsx
git commit -m "feat: refactor deal page to dynamic widget layout from user preferences"
```

---

## Task 8: Smoke Test — End-to-End Verification

**Files:** None (verification only)

**Step 1: Start backend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m uvicorn sis.api.main:app --port 8000`

**Step 2: Start frontend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run dev`

**Step 3: Verify Manager Actions**

1. Open any deal with a completed analysis
2. Confirm "Manager Actions This Week" card appears after Deal Memo
3. Confirm each item shows an agent badge + insight text
4. If no insights exist (old analysis), confirm the card doesn't render

**Step 4: Verify Display Settings**

1. Navigate to `/settings/display`
2. Confirm all 16 widgets are listed with toggles
3. Toggle one widget off (e.g., "Key Unknowns")
4. Drag "Manager Actions" above "Deal Memo"
5. Navigate to a deal page
6. Confirm Key Unknowns is gone and Manager Actions appears before Deal Memo
7. Refresh the page — confirm preferences persist

**Step 5: Verify Reset**

1. Go to `/settings/display`
2. Click "Reset"
3. Confirm all widgets are back to default order and all visible
4. Check deal page reflects the reset

**Step 6: Run frontend build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Clean build with no errors

**Step 7: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address smoke test findings"
```
