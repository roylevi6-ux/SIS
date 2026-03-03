# Signal Clarity UI Overhaul — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the SIS frontend from a generic light-mode shadcn template into a dark, premium "Signal Clarity" command center while keeping all existing features, routes, and cross-filtering behavior intact.

**Architecture:** Pure visual overhaul — change CSS tokens, fonts, and component classNames. No new routes, no API changes, no state management changes. Everything cascades from the dark-first token system in globals.css. A custom `useCountUp` hook provides the only new JS behavior (KPI animation).

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4, shadcn/ui (new-york), DM Sans + DM Mono (Google Fonts)

**Branch:** `ui/signal-clarity-overhaul`

**Design doc:** `docs/plans/2026-03-03-signal-clarity-ui-overhaul-design.md`

---

## Pre-Flight

### Task 0: Create feature branch

**Files:** None

**Step 1: Create and switch to the feature branch**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git checkout -b ui/signal-clarity-overhaul
```

**Step 2: Verify you're on the new branch**

```bash
git branch --show-current
```

Expected: `ui/signal-clarity-overhaul`

---

## Phase 1: Theme Foundation

Everything cascades from these two files. Get them right and 70% of the app already looks different.

### Task 1: Dark-first token system in globals.css

**Files:**
- Modify: `frontend/src/app/globals.css`

**Step 1: Replace the `:root` light-mode tokens with dark-first tokens**

In `globals.css`, replace the entire `:root { ... }` block (lines 89–125) with:

```css
:root {
  --radius: 0.625rem;
  --background: oklch(0.06 0.015 165);
  --foreground: oklch(0.93 0.01 165);
  --card: oklch(0.10 0.02 165);
  --card-foreground: oklch(0.93 0.01 165);
  --popover: oklch(0.12 0.025 165);
  --popover-foreground: oklch(0.93 0.01 165);
  --primary: oklch(0.70 0.17 165);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.14 0.02 165);
  --secondary-foreground: oklch(0.93 0.01 165);
  --muted: oklch(0.14 0.02 165);
  --muted-foreground: oklch(0.55 0.03 165);
  --accent: oklch(0.16 0.025 165);
  --accent-foreground: oklch(0.93 0.01 165);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(0.18 0.03 165);
  --input: oklch(0.20 0.03 165);
  --ring: oklch(0.70 0.17 165);
  --chart-1: oklch(0.70 0.17 165);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.6 0.15 250);
  --chart-5: oklch(0.645 0.246 16.439);

  /* Sidebar stays as-is — already dark green */
  --sidebar: oklch(0.20 0.04 165);
  --sidebar-foreground: oklch(0.92 0.01 165);
  --sidebar-primary: oklch(0.70 0.17 165);
  --sidebar-primary-foreground: oklch(1 0 0);
  --sidebar-accent: oklch(0.26 0.05 165);
  --sidebar-accent-foreground: oklch(0.95 0.01 165);
  --sidebar-border: oklch(0.28 0.04 165);
  --sidebar-ring: oklch(0.70 0.17 165);
  --sidebar-muted: oklch(0.55 0.03 165);
}
```

**Step 2: Remove the `.dark` block entirely** (lines 127–159)

The app is now dark-first by default. Delete the entire `.dark { ... }` block.

**Step 3: Add dark-mode semantic background tokens to the `@theme inline` block**

After `--color-brand-900: #064e3b;` (line 46), add:

```css
  /* Dark-mode semantic backgrounds */
  --color-healthy-bg: rgba(16, 185, 129, 0.12);
  --color-neutral-bg: rgba(251, 191, 36, 0.12);
  --color-needs-attention-bg: rgba(248, 113, 113, 0.12);
  --color-forecast-commit-bg: rgba(5, 150, 105, 0.15);
  --color-forecast-realistic-bg: rgba(37, 99, 235, 0.15);
  --color-forecast-upside-bg: rgba(217, 119, 6, 0.15);
  --color-forecast-risk-bg: rgba(220, 38, 38, 0.15);
```

**Step 4: Update the semantic health colors for dark mode visibility**

Replace lines 14–19 (the hex health colors):

```css
  --color-healthy: #34d399;
  --color-healthy-light: rgba(16, 185, 129, 0.12);
  --color-neutral: #fbbf24;
  --color-neutral-light: rgba(251, 191, 36, 0.12);
  --color-needs-attention: #f87171;
  --color-needs-attention-light: rgba(248, 113, 113, 0.12);
```

**Step 5: Update momentum colors for dark mode**

Replace lines 22–24:

```css
  --color-improving: #34d399;
  --color-stable: #6b7280;
  --color-declining: #f87171;
```

**Step 6: Update forecast text colors for dark mode**

Replace lines 27–34:

```css
  --color-forecast-commit: #34d399;
  --color-forecast-commit-bg: rgba(5, 150, 105, 0.15);
  --color-forecast-realistic: #60a5fa;
  --color-forecast-realistic-bg: rgba(37, 99, 235, 0.15);
  --color-forecast-upside: #fbbf24;
  --color-forecast-upside-bg: rgba(217, 119, 6, 0.15);
  --color-forecast-risk: #f87171;
  --color-forecast-risk-bg: rgba(220, 38, 38, 0.15);
```

**Step 7: Add a pulse keyframe for attention indicators**

At the bottom of the file, after the `@layer base` block, add:

```css
@keyframes pulse-attention {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

**Step 8: Verify the app builds**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

Expected: Build succeeds (warnings OK, no errors).

**Step 9: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/globals.css
git commit -m "feat(ui): dark-first token system for Signal Clarity overhaul"
```

---

### Task 2: DM Sans + DM Mono typography

**Files:**
- Modify: `frontend/src/app/layout.tsx`

**Step 1: Replace font imports**

Replace lines 2 and 10–19 (the Inter and Geist_Mono imports + declarations):

```tsx
import { DM_Sans, DM_Mono } from 'next/font/google';
```

And replace the font declarations:

```tsx
const dmSans = DM_Sans({
  variable: '--font-dm-sans',
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500', '600', '700'],
});

const dmMono = DM_Mono({
  variable: '--font-dm-mono',
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500'],
});
```

**Step 2: Update the body className**

Replace `${inter.variable} ${geistMono.variable}` with `${dmSans.variable} ${dmMono.variable}`.

**Step 3: Update globals.css font references**

In the `@theme inline` block, replace:

```css
  --font-sans: var(--font-dm-sans);
  --font-mono: var(--font-dm-mono);
```

**Step 4: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

**Step 5: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/layout.tsx frontend/src/app/globals.css
git commit -m "feat(ui): replace Inter/Geist Mono with DM Sans/DM Mono"
```

---

## Phase 2: Pipeline Command Center

### Task 3: NumberLine — dark KPI zone + count-up animation

**Files:**
- Create: `frontend/src/lib/hooks/use-count-up.ts`
- Modify: `frontend/src/components/number-line.tsx`

**Step 1: Create the useCountUp hook**

Create `frontend/src/lib/hooks/use-count-up.ts`:

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';

export function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (target === prevTarget.current) return;
    prevTarget.current = target;

    const start = performance.now();
    const from = 0;

    function update(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(from + (target - from) * eased));
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }, [target, duration]);

  return current;
}
```

**Step 2: Rewrite the NumberLine component**

Replace the entire contents of `frontend/src/components/number-line.tsx`:

```tsx
'use client';

import { useCountUp } from '@/lib/hooks/use-count-up';
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

function AnimatedKpi({
  label,
  rawValue,
  subtext,
  colorClass,
}: {
  label: string;
  rawValue: number;
  subtext?: string;
  colorClass?: string;
}) {
  const animated = useCountUp(rawValue);
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className={`text-3xl font-medium font-mono tabular-nums sm:text-4xl ${colorClass ?? 'text-foreground'}`}>
        {formatDollar(animated)}
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
    <div className="space-y-2 pt-4 mt-4 border-t border-border">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full">
        {segments.map((seg) => {
          const pct = (seg.value / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={seg.key}
              className={`${seg.color} transition-all duration-700`}
              style={{ width: `${pct}%` }}
              title={`${seg.label}: ${formatDollar(seg.value)} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        {segments.map((seg) => (
          <span key={seg.key} className="flex items-center gap-1.5">
            <span className={`inline-block size-2 rounded-full ${seg.color}`} />
            {seg.label} <span className="font-mono tabular-nums">{formatDollar(seg.value)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export function NumberLine({ quota, pipeline, forecast }: NumberLineProps) {
  const gapColor = pipeline.gap >= 0 ? 'text-healthy' : 'text-needs-attention';
  const coverageColor =
    pipeline.coverage >= 3 ? 'text-healthy' :
    pipeline.coverage >= 2 ? 'text-neutral' :
    'text-needs-attention';

  const coverageAnimated = useCountUp(Math.round(pipeline.coverage * 10));

  return (
    <div className="relative rounded-xl border bg-card p-6 space-y-4 overflow-hidden">
      {/* Top accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-brand-500" />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <AnimatedKpi label="Quota" rawValue={quota.amount} subtext={quota.period} />
        <AnimatedKpi label="Pipeline" rawValue={pipeline.total_value} subtext={`${pipeline.total_deals} deals`} />
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
            Coverage
          </span>
          <span className={`text-3xl font-medium font-mono tabular-nums sm:text-4xl ${coverageColor}`}>
            {(coverageAnimated / 10).toFixed(1)}x
          </span>
        </div>
        <AnimatedKpi label="Weighted" rawValue={pipeline.weighted_value} />
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
            Gap
          </span>
          <AnimatedKpi
            label=""
            rawValue={Math.abs(pipeline.gap)}
            colorClass={gapColor}
          />
          <span className="text-xs text-muted-foreground">
            {pipeline.gap >= 0 ? 'above quota' : 'below quota'}
          </span>
        </div>
      </div>
      <DistributionBar forecast={forecast} />
    </div>
  );
}
```

**Step 3: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/lib/hooks/use-count-up.ts frontend/src/components/number-line.tsx
git commit -m "feat(ui): dark KPI command zone with count-up animation"
```

---

### Task 4: TeamForecastGrid — dark theme adaptation

**Files:**
- Modify: `frontend/src/components/team-forecast-grid.tsx`

**Step 1: Update active/hover classes from light to dark**

In `team-forecast-grid.tsx`, make these replacements (use find-and-replace):

| Find | Replace |
|------|---------|
| `bg-brand-50/50` | `bg-brand-500/10` |
| `bg-brand-50/60` | `bg-brand-500/12` |
| `bg-brand-50` (exact, in ring cell) | `bg-brand-500/15` |
| `ring-2 ring-brand-500 bg-brand-50` | `ring-1 ring-brand-500/30 bg-brand-500/15` |
| `text-brand-700` | `text-brand-400` |
| `hover:text-brand-700` | `hover:text-brand-400` |
| `hover:bg-muted/50` | `hover:bg-brand-500/8` |
| `hover:bg-muted/60` | `hover:bg-brand-500/10` |
| `bg-muted/30` (in TableHeader) | `bg-muted/50` |
| `bg-muted/20` (in totals row) | `bg-muted/30` |
| `bg-muted/10` (in rep rows) | `bg-muted/20` |

**Step 2: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

**Step 3: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/team-forecast-grid.tsx
git commit -m "feat(ui): TeamForecastGrid dark theme adaptation"
```

---

### Task 5: HealthBadge + ForecastBadge — dark background badges

**Files:**
- Modify: `frontend/src/components/health-badge.tsx`
- Modify: `frontend/src/components/forecast-badge.tsx`

**Step 1: Rewrite HealthBadge for dark mode**

Replace the `getHealthTier` function in `health-badge.tsx`:

```tsx
function getHealthTier(score: number | null) {
  if (score === null || score === undefined) {
    return { label: 'N/A', colorClass: 'bg-muted text-muted-foreground' };
  }
  if (score >= 70) {
    return { label: String(score), colorClass: 'bg-healthy-bg text-healthy' };
  }
  if (score >= 40) {
    return { label: String(score), colorClass: 'bg-neutral-bg text-neutral' };
  }
  return { label: String(score), colorClass: 'bg-needs-attention-bg text-needs-attention' };
}
```

**Step 2: Rewrite ForecastBadge for dark mode**

Replace the `categoryColors` map in `forecast-badge.tsx`:

```tsx
const categoryColors: Record<string, string> = {
  'Commit': 'bg-forecast-commit-bg text-forecast-commit',
  'Realistic': 'bg-forecast-realistic-bg text-forecast-realistic',
  'Upside': 'bg-forecast-upside-bg text-forecast-upside',
  'At Risk': 'bg-forecast-risk-bg text-forecast-risk',
};
```

And update the fallback in the component:

```tsx
const colorClass = categoryColors[category] ?? 'bg-muted text-muted-foreground';
```

**Step 3: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/health-badge.tsx frontend/src/components/forecast-badge.tsx
git commit -m "feat(ui): dark mode health and forecast badges"
```

---

### Task 6: DataTable — dark theme + row stagger

**Files:**
- Modify: `frontend/src/components/data-table.tsx`

**Step 1: Update the rowTintClass function**

Replace the `rowTintClass` function (lines 57–62):

```tsx
function rowTintClass(deal: PipelineDeal): string {
  const tier = healthTier(deal.health_score);
  if (tier === 'needs_attention') return 'bg-needs-attention-bg';
  if (tier === 'neutral') return 'bg-neutral-bg';
  return '';
}
```

**Step 2: Update table row hover and alternating row colors**

In the TableRow render (lines 307–313), replace:

```tsx
<TableRow
  key={row.id}
  className={cn(
    'transition-colors hover:bg-brand-500/5',
    idx % 2 === 1 && 'bg-muted/10',
    rowTintClass(row.original),
  )}
  style={{ animationDelay: `${idx * 20}ms` }}
>
```

**Step 3: Update hover on table header**

In TableHeader className (line 279), replace `bg-muted/30` with `bg-muted/50`.

In TableHead className (line 285), replace `hover:bg-muted/50` with `hover:bg-brand-500/8`.

**Step 4: Update the deal link hover style**

In the account_name column cell (line 91), replace `hover:text-primary` with `hover:text-brand-400`.

**Step 5: Update the deal type badge for dark mode**

In the deal_type column cell (lines 122–126), replace:

```tsx
val.toLowerCase() === 'expansion'
  ? 'bg-brand-500/15 text-brand-400'
  : 'bg-muted text-muted-foreground'
```

**Step 6: Update divergent forecast cell background**

In the forecast column cell (line 155), replace `bg-neutral-light/50` with `bg-neutral-bg`.

**Step 7: Add row stagger animation CSS**

In `globals.css`, add after the `pulse-attention` keyframe:

```css
@keyframes row-reveal {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-row-reveal {
  animation: row-reveal 0.3s ease-out forwards;
  opacity: 0;
}
```

Then add the `animate-row-reveal` class to each TableRow in the data table, alongside the existing classes. The `style={{ animationDelay }}` from Step 2 handles the stagger.

**Step 8: Verify build**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

**Step 9: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/data-table.tsx frontend/src/app/globals.css
git commit -m "feat(ui): dark DataTable with row stagger animation"
```

---

### Task 7: FilterChips — dark theme

**Files:**
- Modify: `frontend/src/components/filter-chips.tsx`

**Step 1: Update the Chip inactive state**

In the Chip component (line 41), replace:

```
'bg-muted text-muted-foreground hover:bg-muted/80'
```

with:

```
'bg-muted/50 text-muted-foreground border border-border hover:bg-brand-500/8 hover:border-brand-500/30'
```

**Step 2: Update the chip count inactive state**

In the count span (line 47), replace:

```
'bg-background text-foreground'
```

with:

```
'bg-background/50 text-foreground'
```

**Step 3: Verify build and commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/filter-chips.tsx
git commit -m "feat(ui): dark mode filter chips"
```

---

### Task 8: AttentionStrip — dark red alert enhancement

**Files:**
- Modify: `frontend/src/components/attention-strip.tsx`

**Step 1: Update the all-clear state**

Replace the all-clear div (line 26–29):

```tsx
<div className="flex items-center gap-2 rounded-lg border border-healthy/20 bg-healthy-bg px-4 py-3">
  <CheckCircle className="size-4 text-healthy" />
  <span className="text-sm font-medium text-healthy">All clear — no deals need immediate attention</span>
</div>
```

**Step 2: Update the attention container**

Replace line 36 container class:

```tsx
<div className="rounded-lg border-l-[3px] border-l-needs-attention border bg-card">
```

**Step 3: Update item hover**

Replace line 39 hover class: `hover:bg-muted/30` → `hover:bg-brand-500/5`

**Step 4: Update the attention item rows**

Replace line 56 item class:

```tsx
<div key={`${item.account_id}-${item.type}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-brand-500/5 transition-colors">
```

**Step 5: Verify build and commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/attention-strip.tsx
git commit -m "feat(ui): dark mode attention strip"
```

---

### Task 9: PipelineChanges — dark theme

**Files:**
- Modify: `frontend/src/components/pipeline-changes.tsx`

**Step 1:** No structural changes needed — this component already uses semantic tokens (`text-healthy`, `text-needs-attention`, `bg-card`). Just update the separator:

Replace `text-border` with `text-muted-foreground/30` on line 54.

**Step 2: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/pipeline-changes.tsx
git commit -m "feat(ui): pipeline changes dark theme tweak"
```

---

### Task 10: Pipeline page header

**Files:**
- Modify: `frontend/src/app/pipeline/page.tsx`

**Step 1: Update the page title**

Replace `text-2xl font-bold tracking-tight` (line 227) with `text-xl font-semibold tracking-tight`.

**Step 2: Update the quarter selector trigger**

Replace `bg-brand-50 border-brand-200` (line 238) with `bg-card border-border`.

**Step 3: Verify build and commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/pipeline/page.tsx
git commit -m "feat(ui): pipeline page header dark theme"
```

---

## Phase 3: Sidebar Polish

### Task 11: Sidebar — logo glow + active item

**Files:**
- Modify: `frontend/src/components/sidebar.tsx`

**Step 1: Add logo glow**

In `SidebarLogo` (line 179), add to the logo div's className after `shadow-brand-500/25`:

Add an inline style to the logo div:

```tsx
style={{ boxShadow: '0 0 20px rgba(16, 185, 129, 0.2)' }}
```

**Step 2: Update active nav item**

In `NavLink` (line 119), update the active state class:

Replace:
```
'bg-sidebar-accent text-sidebar-accent-foreground'
```

With:
```
'bg-sidebar-accent text-sidebar-accent-foreground shadow-[inset_0_0_0_1px_rgba(16,185,129,0.15)]'
```

**Step 3: Verify build and commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/components/sidebar.tsx
git commit -m "feat(ui): sidebar logo glow and active item polish"
```

---

## Phase 4: Deal Detail Page

### Task 12: Deal Detail — dark theme components

**Files:**
- Modify: `frontend/src/app/deals/[id]/page.tsx`
- Modify: `frontend/src/components/agent-card.tsx`
- Modify: `frontend/src/components/deal-memo.tsx`
- Modify: `frontend/src/components/manager-actions-panel.tsx`

This task requires reading each file and making the same systematic replacements as the pipeline components. The changes are all className swaps:

**Pattern for all deal detail components:**

| Find (light mode) | Replace (dark mode) |
|---|---|
| `bg-brand-50` | `bg-brand-500/10` |
| `bg-brand-100` | `bg-brand-500/15` |
| `text-brand-700` | `text-brand-400` |
| `text-brand-800` | `text-brand-400` |
| `text-brand-600` | `text-brand-400` |
| `border-brand-200` | `border-brand-500/20` |
| `bg-emerald-50` | `bg-brand-500/10` |
| `text-emerald-700` | `text-brand-400` |
| `bg-emerald-600` | `bg-brand-500` |
| `hover:bg-muted/50` | `hover:bg-brand-500/8` |
| `bg-gray-100` | `bg-muted` |
| `text-gray-600` | `text-muted-foreground` |
| `bg-amber-50` | `bg-neutral-bg` |
| `bg-red-50` | `bg-needs-attention-bg` |

Additionally, in `deals/[id]/page.tsx`:
- Update the page title: `text-2xl font-bold` → `text-xl font-semibold`
- Add `border-l-[3px] border-l-brand-500` to each agent card wrapper

**Step: Verify build and commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/deals/[id]/page.tsx frontend/src/components/agent-card.tsx frontend/src/components/deal-memo.tsx frontend/src/components/manager-actions-panel.tsx
git commit -m "feat(ui): deal detail page dark theme"
```

---

## Phase 5: Secondary Pages

### Task 13: Login page — dark card

**Files:**
- Modify: `frontend/src/app/login/page.tsx`

**Step 1:** Update the login page background and card. Replace any `bg-white` or light-mode specific classes with the semantic tokens (`bg-card`, `text-foreground`). Update the "S" logo to use `bg-gradient-to-br from-brand-400 to-brand-600`.

**Step 2: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/login/page.tsx
git commit -m "feat(ui): dark login page"
```

---

### Task 14: Forecast page — fix off-brand chart colors

**Files:**
- Modify: `frontend/src/app/forecast/page.tsx`

**Step 1:** Search for any hardcoded color values like `#6366f1` (indigo) or `#0ea5e9` (sky blue) and replace with CSS variable references or brand token hex values (`#34d399` for green, `#60a5fa` for blue).

**Step 2: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/forecast/page.tsx
git commit -m "feat(ui): forecast chart colors aligned to brand tokens"
```

---

### Task 15: Remaining pages — bulk dark theme sweep

**Files:**
- All remaining page files under `frontend/src/app/`

**Step 1:** For every page that has the header pattern `text-2xl font-bold`, update to `text-xl font-semibold`.

**Step 2:** For any light-mode specific classes found across remaining pages, apply the same replacement table from Task 12.

**Step 3: Full build verification**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run build 2>&1 | tail -20
```

**Step 4: Commit**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add frontend/src/app/
git commit -m "feat(ui): dark theme sweep across all remaining pages"
```

---

## Phase 6: Final Verification

### Task 16: Visual verification + final commit

**Step 1: Start the dev server**

```bash
cd /Users/roylevierez/Documents/Sales/SIS/frontend && npm run dev
```

**Step 2: Manual check these pages in the browser:**

- [ ] `/pipeline` — KPIs animate, TeamForecastGrid clicking works, table rows stagger, badges are readable
- [ ] `/deals/<any-id>` — Dark theme, badges readable, agent cards have green accent
- [ ] `/login` — Dark card, logo visible
- [ ] `/trends` — Charts render with correct colors
- [ ] `/forecast` — No off-brand colors
- [ ] `/chat` — Messages readable on dark background

**Step 3: Create a summary commit if any final tweaks are needed**

```bash
cd /Users/roylevierez/Documents/Sales/SIS
git add -A
git commit -m "fix(ui): final visual polish tweaks after verification"
```

---

## Summary

| Phase | Tasks | Files | What Changes |
|-------|-------|-------|-------------|
| 1. Theme Foundation | 1–2 | 2 | Dark tokens + DM Sans/Mono fonts |
| 2. Pipeline | 3–10 | 9 | NumberLine, Grid, Table, Chips, Alerts |
| 3. Sidebar | 11 | 1 | Logo glow, active item polish |
| 4. Deal Detail | 12 | 4 | Dark theme class swaps |
| 5. Secondary Pages | 13–15 | ~6 | Login, Forecast, remaining pages |
| 6. Verification | 16 | 0 | Browser check + polish |

**Total: ~22 files modified, 1 file created (useCountUp hook)**
