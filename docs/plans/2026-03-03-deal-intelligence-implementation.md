# Deal Intelligence Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Role-adaptive deal intelligence — VPs get a 30-second scannable blunt advisor brief; TLs get full narrative with per-agent key findings by dimension. Persist `manager_brief` and 2 new Agent 10 fields end-to-end.

**Architecture:** Agent 10 gets 2 new output fields (deal_memo_sections, attention_level) and a rewritten manager_brief prompt. 3 new DB columns on `deal_assessments`. Backend persists all new fields through both persistence paths. Frontend replaces DealMemo + ManagerActionsPanel with role-aware components (VPBrief, KeyMetricsRow, DealNarrative, KeyFindings, RepActionPlan). Pipeline table gets attention_level column. Backfill top 5 accounts by CP.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 + SQLite, Alembic, Pydantic v2, Next.js 16, React 19, Tailwind CSS 4, shadcn/ui

**Design Doc:** `docs/plans/2026-03-03-deal-intelligence-redesign.md`

---

## Task 1: Agent 10 — New Pydantic Models

**Files:**
- Modify: `sis/agents/synthesis.py` (lines 31-161)

**Step 1: Add DealMemoSection model after SFGapAnalysis (after line 97)**

```python
class DealMemoSection(BaseModel):
    """One section of the structured deal memo."""
    section_id: str = Field(
        description="Stable ID: bottom_line, deal_situation, people_power, "
        "commercial_competitive, why_now, momentum, technical, red_flags, expansion_dynamics"
    )
    title: str = Field(description="Section display title")
    content: str = Field(description="The section content (1-2 paragraphs)")
    health_signal: str = Field(
        description="green (strength area, related health components >= 70% of max), "
        "amber (watch area, 45-69% of max), red (concern, < 45% of max)"
    )
    related_components: list[str] = Field(
        description="Health breakdown component names this section relates to"
    )
```

**Step 2: Add 2 new fields to SynthesisOutput (after `manager_brief`, line 123)**

```python
    # 2c. Structured deal memo sections (for TL view)
    deal_memo_sections: list[DealMemoSection] = Field(
        default_factory=list,
        description="Structured deal memo broken into labeled sections with health signals. "
        "Must cover: bottom_line, deal_situation, people_power, commercial_competitive, "
        "why_now, momentum, technical, red_flags. Add expansion_dynamics for expansion deals.",
    )

    # 2d. VP attention level
    attention_level: str = Field(
        default="none",
        description="VP attention signal: 'act' (VP intervention needed this week), "
        "'watch' (emerging risk, monitor), 'none' (tracking to forecast, no VP action needed)",
    )
```

**Step 3: Verify syntax**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "from sis.agents.synthesis import SynthesisOutput; print('OK:', [f for f in SynthesisOutput.model_fields if f in ('deal_memo_sections', 'attention_level', 'manager_brief')])"`
Expected: Prints OK with the 3 field names

**Step 4: Commit**

```bash
git add sis/agents/synthesis.py
git commit -m "feat: add DealMemoSection model, deal_memo_sections, attention_level to Agent 10 output"
```

---

## Task 2: Agent 10 — Prompt Changes

**Files:**
- Modify: `sis/agents/synthesis.py` (SYSTEM_PROMPT, lines 166-399)

**Step 1: Rewrite Step 2b MANAGER BRIEF (replace lines 192-196)**

Replace the existing Step 2b block:
```
### Step 2b: MANAGER BRIEF
Write 3-5 sentences directly to the VP Sales in the `manager_brief` field:
- The ONE thing to know about this deal right now
- The biggest forecast risk
- What should happen this week
```

With this new block:
```
### Step 2b: MANAGER BRIEF
Write the manager_brief as if you are a trusted, experienced sales executive who has listened to every call on this deal and is now briefing the VP/TL in the hallway. Your tone is direct, practical, and blunt.

Rules:
- DO NOT mention health scores, forecast categories, momentum labels, or any metric the dashboard already shows
- DO focus on: real sales process risks, oversights, delays, silences, and positive signals
- Call out specific people, specific meetings, specific timelines — be concrete
- Include at least one positive signal or bright spot if it exists
- Write 3-5 sentences maximum
- Use the present tense and address the reader directly

Example tone: "Champion went dark after the pricing call two weeks ago — that's your biggest risk right now. The EB hasn't been on a call since discovery, and nobody's pushing for that meeting. If you don't force the EB conversation this week, this deal slides into Q3. Bright spot: procurement joined the last call unprompted — someone internally is moving this forward even if your champion isn't."

Also set attention_level based on the sales process reality you just described:
- "act": Deal requires VP intervention this week — something is broken, stuck, or at risk of dying
- "watch": Emerging concern that doesn't need VP action yet but could escalate
- "none": Deal is progressing, no intervention needed
```

**Step 2: Add structured deal memo instruction (insert after "Explain what the data MEANS for the forecast." — line 190)**

Insert after the existing Step 2 deal memo content:

```
In addition to the flat deal_memo string, populate deal_memo_sections with each paragraph as a separate section object. Use these section_ids in order:
- bottom_line, deal_situation, people_power, commercial_competitive, why_now, momentum, technical, red_flags
- Add expansion_dynamics for expansion deals
For each section, assign a health_signal based on related health score components:
- "green" if related components score >= 70% of their max
- "amber" if 45-69%
- "red" if < 45%
Section-to-component mapping: people_power → champion_strength + multithreading, commercial_competitive → buyer_validated_pain + competitive_position, why_now → urgency_compelling_event, momentum → momentum_quality, technical → technical_path_clarity, deal_situation → stage_appropriateness, red_flags → use lowest-scoring component.
```

**Step 3: Verify prompt loads**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "from sis.agents.synthesis import SYSTEM_PROMPT; print(f'Prompt length: {len(SYSTEM_PROMPT)} chars, ~{len(SYSTEM_PROMPT)//4} tokens'); assert 'attention_level' in SYSTEM_PROMPT; assert 'deal_memo_sections' in SYSTEM_PROMPT; assert 'blunt' in SYSTEM_PROMPT.lower() or 'trusted' in SYSTEM_PROMPT.lower(); print('All sections found')"`
Expected: Prompt length, "All sections found"

**Step 4: Commit**

```bash
git add sis/agents/synthesis.py
git commit -m "feat: rewrite manager_brief to blunt advisor tone, add structured sections + attention level to Agent 10 prompt"
```

---

## Task 3: DB Migration — 3 New Columns

**Files:**
- Modify: `sis/db/models.py` (line 240, after `deal_memo`)
- Create: `alembic/versions/a1b2c3d4e5f6_add_intelligence_columns.py`

**Step 1: Add 3 columns to DealAssessment model (after `deal_memo` at line 240)**

```python
    manager_brief = Column(Text, nullable=True)           # VP-targeted blunt advisor brief
    attention_level = Column(Text, nullable=True)          # "act" / "watch" / "none"
    deal_memo_sections = Column(Text, nullable=True)       # JSON: structured sections with health signals
```

**Step 2: Create Alembic migration**

Create file `alembic/versions/a1b2c3d4e5f6_add_intelligence_columns.py`:

```python
"""add deal intelligence columns

Revision ID: a1b2c3d4e5f6
Revises: f8a2b3c4d5e6
Create Date: 2026-03-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f8a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deal_assessments", sa.Column("manager_brief", sa.Text(), nullable=True))
    op.add_column("deal_assessments", sa.Column("attention_level", sa.Text(), nullable=True))
    op.add_column("deal_assessments", sa.Column("deal_memo_sections", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("deal_assessments", "deal_memo_sections")
    op.drop_column("deal_assessments", "attention_level")
    op.drop_column("deal_assessments", "manager_brief")
```

**Step 3: Run migration**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m alembic upgrade head`
Expected: "Running upgrade f8a2b3c4d5e6 -> a1b2c3d4e5f6, add deal intelligence columns"

**Step 4: Verify columns exist**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "from sis.db.session import get_session; s = next(get_session().__iter__()); cols = [r[1] for r in s.execute(__import__('sqlalchemy').text('PRAGMA table_info(deal_assessments)')).fetchall()]; print('manager_brief' in cols, 'attention_level' in cols, 'deal_memo_sections' in cols)"`
Expected: `True True True`

**Step 5: Commit**

```bash
git add sis/db/models.py alembic/versions/a1b2c3d4e5f6_add_intelligence_columns.py
git commit -m "feat: add manager_brief, attention_level, deal_memo_sections columns to deal_assessments"
```

---

## Task 4: Backend — Persist New Fields

**Files:**
- Modify: `sis/services/analysis_service.py` (lines 303-321 and 797-813)
- Modify: `sis/api/schemas/accounts.py` (lines 68-102)
- Modify: `sis/services/account_service.py` (lines 344-373)

**Step 1: Add new fields to primary persistence block (after line 320)**

In the `DealAssessment(...)` constructor (line 298-321), add after `recommended_actions` (line 320):

```python
                manager_brief=syn.get("manager_brief", ""),
                attention_level=syn.get("attention_level", "none"),
                deal_memo_sections=json.dumps(syn.get("deal_memo_sections", [])),
```

**Step 2: Add new fields to resynthesize persistence block (after line 813)**

After `assessment.recommended_actions = ...` (line 813), add:

```python
        assessment.manager_brief = syn.get("manager_brief", "")
        assessment.attention_level = syn.get("attention_level", "none")
        assessment.deal_memo_sections = json.dumps(syn.get("deal_memo_sections", []))
```

**Step 3: Add fields to AssessmentDetail schema (after line 101)**

In `sis/api/schemas/accounts.py`, add after `sf_gap_interpretation` (line 101):

```python
    manager_brief: Optional[str] = None
    attention_level: Optional[str] = None
    deal_memo_sections: List[Any] = []
```

**Step 4: Add fields to account_service.py detail dict (after line 371)**

In `sis/services/account_service.py`, add after `sf_gap_interpretation` (line 371):

```python
                "manager_brief": latest_assessment.manager_brief,
                "attention_level": latest_assessment.attention_level,
                "deal_memo_sections": json.loads(latest_assessment.deal_memo_sections) if latest_assessment.deal_memo_sections else [],
```

**Step 5: Verify API returns new fields**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "
from sis.api.schemas.accounts import AssessmentDetail
fields = AssessmentDetail.model_fields
assert 'manager_brief' in fields
assert 'attention_level' in fields
assert 'deal_memo_sections' in fields
print('All 3 fields present in AssessmentDetail')
"`
Expected: "All 3 fields present in AssessmentDetail"

**Step 6: Commit**

```bash
git add sis/services/analysis_service.py sis/api/schemas/accounts.py sis/services/account_service.py
git commit -m "feat: persist and expose manager_brief, attention_level, deal_memo_sections"
```

---

## Task 5: Pipeline — Add attention_level to Dashboard + DataTable

**Files:**
- Modify: `sis/services/dashboard_service.py` (lines 77-89 and 608-624)
- Modify: `frontend/src/lib/pipeline-types.ts` (line 22)
- Modify: `frontend/src/components/data-table.tsx` (line 64)

**Step 1: Add attention_level to dashboard deal dicts**

In `dashboard_service.py`, in the first deal-building block (line 77-89), add after `forecast_gap_direction` (line 88):

```python
                    "attention_level": latest.attention_level or "none",
```

And in the "else" block (line 91-103), add after `forecast_gap_direction` (line 102):

```python
                    "attention_level": None,
```

Repeat in the second deal-building block (lines 608-624 and 626-638) — same pattern.

**Step 2: Add to PipelineDeal TypeScript interface**

In `frontend/src/lib/pipeline-types.ts`, add after `forecast_gap_direction` (line 21):

```typescript
  attention_level?: string | null;
```

**Step 3: Add column to DataTable**

In `frontend/src/components/data-table.tsx`, add a new column after the `account_name` column (after line 85):

```typescript
  {
    accessorKey: 'attention_level',
    header: '',
    cell: ({ getValue }) => {
      const level = getValue() as string | null;
      if (!level || level === 'none') return null;
      if (level === 'act')
        return (
          <span className="inline-flex size-2.5 rounded-full bg-red-500" title="VP action needed" />
        );
      return (
        <span className="inline-flex size-2.5 rounded-full bg-amber-400" title="Watch" />
      );
    },
    size: 32,
    enableSorting: true,
  },
```

**Step 4: Build frontend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add sis/services/dashboard_service.py frontend/src/lib/pipeline-types.ts frontend/src/components/data-table.tsx
git commit -m "feat: add attention_level to pipeline table with color dot indicator"
```

---

## Task 6: Frontend — VPBrief + KeyMetricsRow Components

**Files:**
- Create: `frontend/src/components/vp-brief.tsx`
- Create: `frontend/src/components/key-metrics-row.tsx`

**Step 1: Create VPBrief component**

```tsx
'use client';

import { AlertTriangle, Eye } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface VPBriefProps {
  brief: string | null;
  attentionLevel: string | null;
  fallbackMemo?: string | null;
}

function truncateFallback(text: string): string {
  const sentences = text.match(/[^.!?]+[.!?]+/g);
  if (sentences && sentences.length >= 3) return sentences.slice(0, 3).join('').trim();
  return text.slice(0, 500);
}

export function VPBrief({ brief, attentionLevel, fallbackMemo }: VPBriefProps) {
  const level = attentionLevel ?? 'none';
  const text = brief || (fallbackMemo ? truncateFallback(fallbackMemo) : null);

  if (!text) return null;

  const isFallback = !brief && !!fallbackMemo;

  return (
    <Card
      className={cn(
        'transition-colors',
        level === 'act' && 'border-red-500/60 bg-red-50/50 dark:bg-red-950/20',
        level === 'watch' && 'border-amber-400/60 bg-amber-50/50 dark:bg-amber-950/20',
      )}
    >
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-3">
          {level === 'act' && <AlertTriangle className="size-5 text-red-500 shrink-0 mt-0.5" />}
          {level === 'watch' && <Eye className="size-5 text-amber-500 shrink-0 mt-0.5" />}
          <div className="space-y-1.5 min-w-0">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              VP Brief
            </h3>
            <p className="text-sm leading-relaxed">{text}</p>
            {isFallback && (
              <p className="text-xs text-muted-foreground italic">
                Auto-generated summary — re-run analysis for full VP brief
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Create KeyMetricsRow component**

```tsx
'use client';

import { AlertTriangle, Zap, HelpCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface KeyMetricsRowProps {
  topRisk: { risk?: string; text?: string; severity?: string } | string | null;
  topAction: { action?: string; text?: string; priority?: string; owner?: string } | string | null;
  keyUnknown: string | null;
}

function getText(item: unknown): string | null {
  if (!item) return null;
  if (typeof item === 'string') return item;
  if (typeof item === 'object') {
    const obj = item as Record<string, unknown>;
    return (obj.risk ?? obj.action ?? obj.text ?? obj.description ?? '') as string;
  }
  return null;
}

export function KeyMetricsRow({ topRisk, topAction, keyUnknown }: KeyMetricsRowProps) {
  const riskText = getText(topRisk);
  const actionText = getText(topAction);
  const actionOwner = typeof topAction === 'object' && topAction
    ? (topAction as Record<string, unknown>).owner as string | undefined
    : undefined;
  const actionPriority = typeof topAction === 'object' && topAction
    ? (topAction as Record<string, unknown>).priority as string | undefined
    : undefined;

  if (!riskText && !actionText && !keyUnknown) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {riskText && (
        <Card className="py-0">
          <CardContent className="pt-3 pb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlertTriangle className="size-3.5 text-red-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">Top Risk</span>
            </div>
            <p className="text-sm leading-snug line-clamp-3">{riskText}</p>
          </CardContent>
        </Card>
      )}
      {actionText && (
        <Card className="py-0">
          <CardContent className="pt-3 pb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Zap className="size-3.5 text-blue-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">Top Action</span>
              {actionPriority && <Badge variant="outline" className="text-[10px] px-1 py-0">{actionPriority}</Badge>}
              {actionOwner && <Badge variant="secondary" className="text-[10px] px-1 py-0">{actionOwner}</Badge>}
            </div>
            <p className="text-sm leading-snug line-clamp-3">{actionText}</p>
          </CardContent>
        </Card>
      )}
      {keyUnknown && (
        <Card className="py-0">
          <CardContent className="pt-3 pb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <HelpCircle className="size-3.5 text-purple-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">Key Unknown</span>
            </div>
            <p className="text-sm leading-snug line-clamp-3">{keyUnknown}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

**Step 3: Build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/components/vp-brief.tsx frontend/src/components/key-metrics-row.tsx
git commit -m "feat: add VPBrief and KeyMetricsRow components"
```

---

## Task 7: Frontend — DealNarrative Component

**Files:**
- Create: `frontend/src/components/deal-narrative.tsx`

**Step 1: Create DealNarrative component**

```tsx
'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

interface DealMemoSection {
  section_id: string;
  title: string;
  content: string;
  health_signal: string;
  related_components: string[];
}

interface DealNarrativeProps {
  memo: string | null;
  sections: DealMemoSection[];
}

const SIGNAL_STYLES: Record<string, string> = {
  green: 'border-l-emerald-500',
  amber: 'border-l-amber-400',
  red: 'border-l-red-500',
};

function parseFallbackSections(memo: string): DealMemoSection[] {
  const paragraphs = memo.split(/\n\n+/).filter((p) => p.trim());
  const sectionIds = [
    'bottom_line', 'deal_situation', 'people_power', 'commercial_competitive',
    'why_now', 'momentum', 'technical', 'red_flags', 'expansion_dynamics',
  ];
  const titles = [
    'The Bottom Line', 'Deal Situation & Stage', 'People & Power',
    'Commercial & Competitive', 'Why Now?', 'Momentum & Advancement',
    'Technical & Integration', 'Red Flags & Silence Signals', 'Expansion Dynamics',
  ];
  return paragraphs.slice(0, sectionIds.length).map((content, i) => ({
    section_id: sectionIds[i] ?? `section_${i}`,
    title: titles[i] ?? `Section ${i + 1}`,
    content: content.trim(),
    health_signal: 'amber',
    related_components: [],
  }));
}

export function DealNarrative({ memo, sections }: DealNarrativeProps) {
  const [expandedAll, setExpandedAll] = useState(true);

  const displaySections = sections.length > 0
    ? sections
    : memo
      ? parseFallbackSections(memo)
      : [];

  if (displaySections.length === 0) return null;

  const bottomLine = displaySections.find((s) => s.section_id === 'bottom_line');
  const rest = displaySections.filter((s) => s.section_id !== 'bottom_line');

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Deal Narrative
          </h3>
          <button
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setExpandedAll(!expandedAll)}
          >
            {expandedAll ? 'Collapse all' : 'Expand all'}
          </button>
        </div>

        {bottomLine && (
          <div className="border-l-4 border-l-foreground/20 pl-4 py-1">
            <p className="text-sm font-medium leading-relaxed">{bottomLine.content}</p>
          </div>
        )}

        <div className="space-y-1">
          {rest.map((section) => (
            <NarrativeSection key={section.section_id} section={section} defaultOpen={expandedAll} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function NarrativeSection({ section, defaultOpen }: { section: DealMemoSection; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="w-full text-left">
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors border-l-3',
            SIGNAL_STYLES[section.health_signal] ?? 'border-l-muted',
          )}
        >
          <ChevronRight
            className={cn(
              'size-3.5 shrink-0 text-muted-foreground transition-transform duration-200',
              open && 'rotate-90',
            )}
          />
          <span className="text-sm font-medium">{section.title}</span>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className={cn('pl-9 pr-3 pb-3 border-l-3', SIGNAL_STYLES[section.health_signal] ?? 'border-l-muted')}>
          {section.content.split(/\n+/).filter(Boolean).map((para, i) => (
            <p key={i} className="text-sm leading-relaxed text-muted-foreground mt-1.5">
              {para}
            </p>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
```

**Step 2: Build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/deal-narrative.tsx
git commit -m "feat: add DealNarrative component with section health indicators"
```

---

## Task 8: Frontend — KeyFindings + RepActionPlan Components

**Files:**
- Create: `frontend/src/components/key-findings.tsx`
- Create: `frontend/src/components/rep-action-plan.tsx`

**Context:** KeyFindings replaces the old ManagerActionsPanel. It extracts `manager_insight` from each agent's `findings` JSON and presents them as a flat, scannable list of practical sales findings grouped by dimension — no nested collapsibles, no coaching framing.

**Step 1: Create KeyFindings component**

```tsx
'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface AgentAnalysis {
  id?: string;
  agent_id?: string;
  findings?: Record<string, unknown> | null;
}

const DIMENSION_MAP: Record<string, { label: string; color: string }> = {
  agent_1_stage_progress: { label: 'Stage & Progress', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  agent_2_relationship: { label: 'Relationship', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
  agent_3_commercial_risk: { label: 'Commercial', color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  agent_4_momentum: { label: 'Momentum', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
  agent_5_technical: { label: 'Technical', color: 'bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300' },
  agent_6_economic_buyer: { label: 'Economic Buyer', color: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' },
  agent_7_msp_next_steps: { label: 'Next Steps', color: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300' },
  agent_8_competitive: { label: 'Competitive', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' },
  agent_0e_account_health: { label: 'Account Health', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' },
};

function getInsight(agent: AgentAnalysis): string | null {
  if (!agent.findings || typeof agent.findings !== 'object') return null;
  const insight = agent.findings.manager_insight;
  return insight ? String(insight) : null;
}

function getAgentId(agent: AgentAnalysis): string {
  return agent.agent_id ?? agent.id ?? '';
}

interface KeyFindingsProps {
  agents: AgentAnalysis[];
}

export function KeyFindings({ agents }: KeyFindingsProps) {
  const findings = agents
    .map((agent) => ({
      agentId: getAgentId(agent),
      insight: getInsight(agent),
    }))
    .filter((f): f is { agentId: string; insight: string } => !!f.insight);

  if (findings.length === 0) return null;

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Key Findings by Dimension
        </h3>
        <div className="space-y-2.5">
          {findings.map(({ agentId, insight }) => {
            const dim = DIMENSION_MAP[agentId];
            return (
              <div key={agentId} className="flex items-start gap-2.5">
                <Badge
                  variant="secondary"
                  className={`text-[10px] px-1.5 py-0.5 shrink-0 mt-0.5 ${dim?.color ?? ''}`}
                >
                  {dim?.label ?? agentId}
                </Badge>
                <p className="text-sm leading-relaxed text-foreground">{insight}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Create RepActionPlan component**

```tsx
'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

type ActionItem = string | {
  action?: string; text?: string; description?: string;
  priority?: string; owner?: string; rationale?: string;
  [key: string]: unknown;
};

interface RepActionPlanProps {
  actions: ActionItem[];
}

function getActionText(item: ActionItem): string {
  if (typeof item === 'string') return item;
  return (item.action ?? item.text ?? item.description ?? JSON.stringify(item)) as string;
}

function getOwner(item: ActionItem): string | null {
  return typeof item === 'object' ? (item.owner as string | null) ?? null : null;
}

function getPriority(item: ActionItem): string | null {
  return typeof item === 'object' ? (item.priority as string | null) ?? null : null;
}

const PRIORITY_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2 };
const OWNER_GROUPS = ['AE', 'SE', 'Manager', 'Other'];

export function RepActionPlan({ actions }: RepActionPlanProps) {
  if (!actions || actions.length === 0) return null;

  const sorted = [...actions].sort((a, b) => {
    const pa = PRIORITY_ORDER[getPriority(a) ?? ''] ?? 99;
    const pb = PRIORITY_ORDER[getPriority(b) ?? ''] ?? 99;
    return pa - pb;
  });

  const grouped: Record<string, ActionItem[]> = {};
  for (const action of sorted) {
    const owner = getOwner(action) ?? 'Other';
    const group = OWNER_GROUPS.includes(owner) ? owner : 'Other';
    (grouped[group] ??= []).push(action);
  }

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Rep Action Plan
        </h3>
        {OWNER_GROUPS.filter((g) => grouped[g]?.length).map((group) => (
          <div key={group} className="space-y-1.5">
            <p className="text-xs font-semibold text-muted-foreground">{group}</p>
            <ul className="space-y-1">
              {grouped[group]!.map((action, i) => {
                const priority = getPriority(action);
                return (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    {priority && (
                      <Badge
                        variant={priority === 'P0' ? 'destructive' : 'outline'}
                        className="text-[10px] px-1 py-0 shrink-0 mt-0.5"
                      >
                        {priority}
                      </Badge>
                    )}
                    <span className="leading-relaxed">{getActionText(action)}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

**Step 3: Build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/components/key-findings.tsx frontend/src/components/rep-action-plan.tsx
git commit -m "feat: add KeyFindings (per-agent insights by dimension) and RepActionPlan components"
```

---

## Task 9: Frontend — Role-Aware Deal Page Refactor

**Files:**
- Modify: `frontend/src/app/deals/[id]/page.tsx`

This is the major refactor: wire new components, add role detection, change default widget order and collapsed states per role.

**Step 1: Add new imports at top of file**

Add these imports (after existing imports):

```tsx
import { usePermissions } from '@/lib/permissions';
import { VPBrief } from '@/components/vp-brief';
import { KeyMetricsRow } from '@/components/key-metrics-row';
import { DealNarrative } from '@/components/deal-narrative';
import { KeyFindings } from '@/components/key-findings';
import { RepActionPlan } from '@/components/rep-action-plan';
```

**Step 2: Extend the Assessment interface (after line 79)**

Add 3 new fields:

```tsx
  manager_brief: string | null;
  attention_level: string | null;
  deal_memo_sections: Array<{
    section_id: string;
    title: string;
    content: string;
    health_signal: string;
    related_components: string[];
  }>;
```

**Step 3: Add role detection in DealDetailPage component**

Inside the main component function (after the existing hooks, around line 510):

```tsx
const { isVpOrAbove } = usePermissions();
```

**Step 4: Replace the `renderWidget` function**

Add these new cases to the renderWidget switch:
```tsx
    case 'vp_brief':
      return assessment ? (
        <VPBrief
          key={widgetId}
          brief={assessment.manager_brief}
          attentionLevel={assessment.attention_level}
          fallbackMemo={assessment.deal_memo}
        />
      ) : null;
    case 'key_metrics':
      return assessment ? (
        <KeyMetricsRow
          key={widgetId}
          topRisk={assessment.top_risks?.[0] ?? null}
          topAction={assessment.recommended_actions?.[0] ?? null}
          keyUnknown={assessment.key_unknowns?.[0] ?? null}
        />
      ) : null;
    case 'deal_narrative':
      return assessment ? (
        <DealNarrative
          key={widgetId}
          memo={assessment.deal_memo}
          sections={assessment.deal_memo_sections ?? []}
        />
      ) : null;
    case 'key_findings':
      return assessment ? (
        <KeyFindings key={widgetId} agents={agentList} />
      ) : null;
    case 'rep_action_plan':
      return assessment ? (
        <RepActionPlan key={widgetId} actions={assessment.recommended_actions ?? []} />
      ) : null;
```

**Step 5: Update getVisibleWidgets default order**

Replace the default widget array in `getVisibleWidgets` to be role-aware:

```tsx
function getVisibleWidgets(prefs: WidgetConfig[] | undefined, vpMode: boolean): string[] {
  if (prefs) {
    return prefs
      .filter((w) => w.visible)
      .sort((a, b) => a.order - b.order)
      .map((w) => w.id);
  }

  if (vpMode) {
    return [
      'status_strip', 'vp_brief', 'what_changed', 'key_metrics',
      'deal_memo', 'health_breakdown', 'actions_risks',
      'agent_analyses', 'deal_timeline', 'analysis_history',
    ];
  }

  return [
    'status_strip', 'deal_narrative', 'key_findings', 'what_changed',
    'rep_action_plan', 'health_breakdown', 'actions_risks',
    'positive_contradictions', 'forecast_divergence', 'key_unknowns',
    'forecast_rationale', 'sf_gap', 'agent_analyses', 'deal_timeline',
    'analysis_history', 'transcript_list',
  ];
}
```

Update the call site to pass `isVpOrAbove`:

```tsx
{getVisibleWidgets(widgetPrefs, isVpOrAbove).map((widgetId) => renderWidget(widgetId))}
```

**Step 6: Build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Build succeeds

**Step 7: Commit**

```bash
git add frontend/src/app/deals/\\[id\\]/page.tsx
git commit -m "feat: role-aware deal page with VP brief and TL narrative + key findings layouts"
```

---

## Task 10: Verify Agent 10 Token Budget

**Files:**
- None (verification only)

**Step 1: Verify current budget is sufficient**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "from sis.config import MAX_OUTPUT_TOKENS_SYNTHESIS; print(f'Current Agent 10 budget: {MAX_OUTPUT_TOKENS_SYNTHESIS:,} tokens')"`
Expected: "Current Agent 10 budget: 12,000 tokens"

The current budget is 12,000 tokens — already higher than the 10,000 originally discussed. The new fields add ~200 tokens (deal_memo_sections metadata + attention_level). No change needed.

No commit needed for this task.

---

## Task 11: Backfill Top 5 Accounts by CP

**Files:**
- None (operational task)

**Step 1: Find top 5 accounts by CP**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "
from sis.db.session import get_session
import sqlalchemy as sa
session = next(get_session().__iter__())
rows = session.execute(sa.text(
    'SELECT id, account_name, cp_estimate FROM accounts WHERE cp_estimate IS NOT NULL ORDER BY cp_estimate DESC LIMIT 5'
)).fetchall()
for r in rows:
    print(f'{r[1]}: \${r[2]:,.0f} (id: {r[0]})')
"`
Expected: List of top 5 accounts by CP estimate

**Step 2: Re-run analysis for each account**

For each account_id from Step 1, trigger a resynthesize (re-runs Agent 10 only with updated prompt):

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "
import asyncio
from sis.services.analysis_service import resynthesize_latest
from sis.db.session import get_session

ACCOUNT_IDS = []  # Fill with IDs from Step 1

async def backfill():
    for aid in ACCOUNT_IDS:
        print(f'Resynthesizing {aid}...')
        result = await resynthesize_latest(aid)
        print(f'  Done: {result}')

asyncio.run(backfill())
"`

Note: Replace `ACCOUNT_IDS` with the actual IDs from Step 1.

**Step 3: Verify new fields are populated**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -c "
from sis.db.session import get_session
import sqlalchemy as sa
session = next(get_session().__iter__())
rows = session.execute(sa.text(
    'SELECT a.account_name, d.manager_brief IS NOT NULL, d.attention_level, d.deal_memo_sections IS NOT NULL '
    'FROM deal_assessments d JOIN accounts a ON d.account_id = a.id '
    'WHERE d.manager_brief IS NOT NULL '
    'ORDER BY d.created_at DESC LIMIT 5'
)).fetchall()
for r in rows:
    print(f'{r[0]}: brief={r[1]}, attention={r[2]}, sections={r[3]}')
"`
Expected: 5 rows showing populated fields

**Step 4: Commit (if any scripts were created)**

No code changes — this is a data operation.

---

## Task 12: Smoke Test — End-to-End Verification

**Files:** None (verification only)

**Step 1: Start backend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m uvicorn sis.api.main:app --port 8000`

**Step 2: Start frontend**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run dev`

**Step 3: Verify VP view**

1. Log in as a VP-level user
2. Open a backfilled deal
3. Confirm: VP Brief card shows with attention color (red/amber/none), blunt advisor tone text (no metrics rehash)
4. Confirm: What Changed appears second, Key Metrics Row shows top risk/action/unknown
5. Confirm: Deal Memo and other sections are collapsed by default
6. Expand Deal Memo — confirm full text appears

**Step 4: Verify TL view**

1. Log in as a TL-level user
2. Open the same deal
3. Confirm: Deal Narrative shows with section headers and health signal colors (green/amber/red left borders)
4. Confirm: Key Findings by Dimension shows a flat list of per-agent insights with dimension badges (Relationship, Commercial, Momentum, etc.)
5. Confirm: No nested collapsibles — findings are directly visible
6. Confirm: Rep Action Plan shows actions grouped by owner (AE/SE/Manager)

**Step 5: Verify pipeline table**

1. Navigate to /pipeline
2. Confirm attention dot appears next to backfilled accounts (red or amber)
3. Confirm non-backfilled accounts show no dot

**Step 6: Verify fallback for old data**

1. Open a deal that was NOT backfilled
2. VP: Confirm "Auto-generated summary" note appears below truncated brief
3. TL: Confirm deal memo renders as unsectioned paragraphs with amber (neutral) borders
4. Confirm Key Findings shows whatever per-agent manager_insight data exists from original runs

**Step 7: Final build**

Run: `cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build`
Expected: Clean build

**Step 8: Run backend tests**

Run: `cd /Users/roylevierez/Documents/Sales/SIS && .venv/bin/python -m pytest tests/ -x -q`
Expected: All tests pass

**Step 9: Commit any fixes**

```bash
git add -A
git commit -m "fix: address smoke test findings"
```
