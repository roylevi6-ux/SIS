# Signal Clarity — UI Overhaul Design

**Date**: 2026-03-03
**Direction**: Signal Clarity (dark command center, precision typography, green-on-dark)
**Scope**: Visual + layout restructure (no new features)
**Branch**: `ui/signal-clarity-overhaul`
**Priority pages**: Pipeline Command Center, Deal Detail

## Design Decisions

### What We're Keeping
- Green sidebar + green brand identity (Riskified colors)
- TeamForecastGrid with clickable cells that filter the deals table
- Cross-filtering flow: Quarter selector → Team selector → TeamForecastGrid cell → FilterChips → DataTable
- All existing routes and features — this is a visual overhaul, not a rewrite
- shadcn/ui primitives (Button, Card, Table, etc.)
- Recharts for charts, TanStack Table for the deal table, dnd-kit for widget ordering
- Widget visibility system from Display Settings

### What We're Changing

#### 1. Color System — Dark-First with Green Brand
Replace the current light-mode token system with a dark-first theme that makes the Riskified green electric.

**Root (default = dark)**:
```css
--background: oklch(0.06 0.015 165);     /* Near-black, green-tinted canvas */
--foreground: oklch(0.93 0.01 165);      /* Warm white with green undertone */
--card: oklch(0.10 0.02 165);            /* Dark forest card surface */
--card-foreground: oklch(0.93 0.01 165);
--muted: oklch(0.14 0.02 165);           /* Subtle surface variation */
--muted-foreground: oklch(0.55 0.03 165);
--border: oklch(0.18 0.03 165);          /* Green-tinted border */
--primary: oklch(0.70 0.17 165);         /* Brand-400 (unchanged) */
--accent: oklch(0.16 0.025 165);         /* Slightly elevated surface */
--ring: oklch(0.70 0.17 165);            /* Brand focus ring */
```

**Sidebar tokens** stay as-is — already dark green.

**Semantic health/forecast colors** stay hex-based but with added dark-mode backgrounds:
```css
--color-healthy-bg: rgba(16, 185, 129, 0.12);
--color-neutral-bg: rgba(251, 191, 36, 0.12);
--color-needs-attention-bg: rgba(248, 113, 113, 0.12);
```

#### 2. Typography — DM Sans + DM Mono
Replace Inter with DM Sans for body/headlines. Replace Geist Mono with DM Mono for KPIs and financial numbers.

- **layout.tsx**: Import `DM_Sans` and `DM_Mono` from `next/font/google`
- **globals.css**: `--font-sans: var(--font-dm-sans)`, `--font-mono: var(--font-dm-mono)`
- KPI numbers scale up: `text-2xl sm:text-3xl` → `text-3xl sm:text-4xl`
- Page titles: `text-2xl font-bold` → `text-xl font-semibold` (DM Sans has more presence, needs less weight)

#### 3. KPI Command Zone — NumberLine Upgrade
The NumberLine component becomes a dark, elevated panel:

- Container: `bg-card border rounded-xl p-6` (uses new dark card token)
- Top accent bar: 2px `bg-brand-500` at top of card
- KPI values: `text-3xl sm:text-4xl font-mono font-medium` (bigger, DM Mono)
- Distribution bar: height from `h-3` → `h-2.5`, with `rounded-full`
- **Count-up animation**: Numbers animate from 0 to their value over 600ms on initial load using `requestAnimationFrame` + ease-out cubic

#### 4. TeamForecastGrid — Dark Theme Adaptation
Keep the existing component structure and behavior. Visual changes only:

- Table background: `bg-card` (dark surface)
- Header cells: `bg-muted` with `text-muted-foreground`
- Active cell highlight: `bg-brand-500/15` with `ring-1 ring-brand-500/30`
- Hover cells: `bg-brand-500/8`
- Dollar values in cells: `font-mono` (DM Mono)
- Drill-down chevron: unchanged behavior, green highlight on active

#### 5. DataTable — Visual Hierarchy Upgrade
- Row hover: `bg-brand-500/5` (subtle green glow on dark)
- Row tinting for health: increase opacity — `bg-needs-attention/10` (was `/40` of `-light`)
- Score badges: dark backgrounds with colored text (e.g., green score = `bg-brand-500/15 text-brand-400`)
- Forecast badges: same pattern (colored text on subtle dark background)
- Momentum arrows: keep current, ensure `text-brand-400` for improving, `text-red-400` for declining
- Table header row: `bg-muted` with `text-[10.5px] uppercase tracking-wider`
- **Row stagger animation**: On initial load, rows fade in with 20ms stagger delay

#### 6. AttentionStrip — Red Alert Enhancement
- Left border: `border-l-3 border-red-400` (was `border-l-2`)
- Background: `bg-red-500/5` (subtle red tint on dark)
- Pulse indicator on high-priority items (CSS `animation: pulse 2s infinite`)
- Collapse/expand remains unchanged

#### 7. Page Header Pattern
Create a consistent header pattern used across all pages:
- Title: `text-xl font-semibold tracking-tight`
- Subtitle: `text-sm text-muted-foreground`
- Selectors (quarter, team) right-aligned on desktop, stacked on mobile
- No background — title floats on the dark canvas

#### 8. Card Elevation System
Introduce depth via border + subtle background variation:
- **Level 0** (page): `bg-background` — the canvas
- **Level 1** (cards): `bg-card border` — primary content containers
- **Level 2** (elevated): `bg-accent` — dropdowns, popovers, hover states
- Cards get a subtle top-border accent: `border-t-2 border-brand-500/20` (optional, per card)

#### 9. Motion — Three Rules Only
1. **KPI count-up**: Numbers animate 0 → value, 600ms, ease-out cubic
2. **Row stagger**: Table rows fade in at 20ms intervals on mount
3. **Badge transitions**: Health/forecast badge color changes get `transition-colors duration-200`

No page transitions. No parallax. No heavy animation libraries.

#### 10. Deal Detail Page
Apply the same dark theme. Key changes:
- Sticky status header: Account name + health badge + forecast — stays visible on scroll
- Agent cards: `bg-card` with `border-l-3 border-brand-500` accent
- Deal memo tabs: dark tab bar, green active indicator
- Confidence meter: existing component, just re-skinned with dark tokens
- Manager Actions panel: `bg-card` with subtle green header accent

#### 11. Sidebar — Minor Polish
Sidebar is already dark green. Minor adjustments:
- Logo glow: `box-shadow: 0 0 16px rgba(16, 185, 129, 0.2)` on the logo icon
- Active nav item: add `box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.15)`
- Group labels: `text-[10px]` → `text-[9.5px]` tighter tracking

#### 12. All Other Pages
Every page inherits the dark theme via the token system. Page-specific elements:
- **Trends**: Recharts colors use CSS variables (already configured via `chart-1` through `chart-5`)
- **Forecast**: Replace off-brand indigo/sky chart colors with brand token colors
- **Team Rollup / Rep Scorecard**: Re-skin table and cards
- **Chat**: Dark message bubbles, green user messages
- **Login**: Dark card with green gradient logo

## Files Changed

### Core Theme (affects everything)
1. `frontend/src/app/globals.css` — New dark-first token values
2. `frontend/src/app/layout.tsx` — DM Sans + DM Mono font imports

### Pipeline Command Center
3. `frontend/src/components/number-line.tsx` — Dark KPI zone, count-up animation, larger numbers
4. `frontend/src/components/team-forecast-grid.tsx` — Dark theme class updates
5. `frontend/src/components/data-table.tsx` — Row hover, stagger animation, badge colors
6. `frontend/src/components/filter-chips.tsx` — Dark chip styling
7. `frontend/src/components/attention-strip.tsx` — Red alert enhancement, pulse
8. `frontend/src/components/pipeline-changes.tsx` — Dark theme
9. `frontend/src/app/pipeline/page.tsx` — Header pattern, spacing

### Deal Detail
10. `frontend/src/app/deals/[id]/page.tsx` — Sticky status header, dark theme
11. `frontend/src/components/deal-memo.tsx` — Dark tabs
12. `frontend/src/components/agent-card.tsx` — Dark card with green accent border
13. `frontend/src/components/manager-actions-panel.tsx` — Dark theme
14. `frontend/src/components/health-badge.tsx` — Dark background badges
15. `frontend/src/components/forecast-badge.tsx` — Dark background badges
16. `frontend/src/components/momentum-indicator.tsx` — Color adjustments

### Sidebar
17. `frontend/src/components/sidebar.tsx` — Logo glow, active item polish

### Secondary Pages (cascade from theme)
18. `frontend/src/app/forecast/page.tsx` — Fix off-brand chart colors
19. `frontend/src/app/chat/page.tsx` — Dark message bubbles
20. `frontend/src/app/login/page.tsx` — Dark login card

## Implementation Order

1. **Theme foundation** (globals.css + layout.tsx) — everything cascades from here
2. **Pipeline page** (NumberLine + TeamForecastGrid + DataTable + FilterChips + AttentionStrip)
3. **Deal Detail page** (sticky header + components)
4. **Sidebar polish**
5. **Secondary pages** (Forecast chart colors, Chat, Login)

## What NOT to Change
- No new npm dependencies (count-up animation is vanilla JS/React)
- No changes to API calls, data fetching, or state management
- No changes to routing or page structure
- No feature additions
- Keep widget ordering/visibility system intact
- Keep all cross-filtering behavior exactly as-is
