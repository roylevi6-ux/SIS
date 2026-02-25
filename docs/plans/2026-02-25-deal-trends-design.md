# Deal Trends Page — Design Document

**Date:** 2026-02-25
**Status:** Approved
**Approach:** B — Full 5-Tab Analytics Hub

## Overview

Replace the existing basic `/trends` page (health score lines only) with a comprehensive 5-tab deal trends analytics hub. The page serves both VP Sales (pipeline-level insights) and sales managers (coaching-level insights).

**Product goal:** Transform SIS from a "deal assessment tool" (point-in-time) into a "pipeline management system" (temporal). The trends page answers the questions sales leaders ask every week: "Are we going to hit the number?", "What changed?", "Where do I intervene?"

**Key differentiator:** Unlike Gong/Clari (which trend CRM fields and activity metadata), SIS trends are transcript-evidence-backed — every data point links to what actually happened in conversations.

---

## Page Layout & Navigation

### Sidebar Placement
- Add "Trends" to sidebar under **Analytics** section (alongside Pipeline, Team Rollup, Rep Scorecard)
- Icon: `TrendingUp` (Lucide)
- Visible to **all roles**

### Global Controls (shared across all tabs)
- **Time window:** `4 weeks` | `8 weeks` | `12 weeks` | `This Quarter`
- **Team filter** dropdown (VP+ roles only)
- **Deal type filter:** `All` | `New Logo` | `Expansion`

### Role-Based Behavior

| Role | Default Tab | Data Scope | Team Filter |
|------|------------|------------|-------------|
| IC | Deal Health | Own deals only | Hidden |
| Team Lead | Deal Health | Team's deals | Hidden (fixed to own team) |
| VP / GM | Pipeline Flow | All teams | Visible |
| Admin | Pipeline Flow | All teams | Visible |

### Tab State
Managed via URL query parameter (`/trends?tab=pipeline-flow`) for deep linking and shareability.

---

## Tab 1: Pipeline Flow

**Audience:** VP Sales / CRO
**Answers:** "Are we going to hit the number?"

### Visualizations

#### A. Pipeline Waterfall (Hero Chart)
- **Type:** Horizontal waterfall bar chart (Recharts BarChart with floating bars)
- **Segments:** Starting Pipeline → +New Deals → +Upgrades → -Downgrades → -Lost Deals → Ending Pipeline
- **Colors:** Green (additions), Red (removals), Blue (net)
- **Interaction:** Each segment clickable → shows specific deals

#### B. Coverage Ratio Trend Line
- **Type:** Recharts ComposedChart (Line + ReferenceLine)
- **Y-axis:** Coverage ratio (pipeline ÷ quota)
- **X-axis:** Week
- **Reference lines:** Dashed at 1.0x (bare minimum) and 3.0x (healthy)

#### C. Pipeline Value by Forecast Category
- **Type:** Recharts AreaChart (stacked)
- **Bands:** Commit (green), Realistic (blue), Upside (amber), At Risk (red)
- **X-axis:** Week, **Y-axis:** Cumulative MRR

### Summary Cards (4)
| Card | Value |
|------|-------|
| Total Pipeline Value | Sum of mrr_estimate for active deals |
| Net Change This Week | Ending - Starting pipeline value |
| Coverage Ratio | Current pipeline ÷ quota |
| Active Deals | Count |

### Data Sources
- `DealAssessment.created_at` + `Account.mrr_estimate` (grouped by week)
- `Account.ic_forecast_category` / `DealAssessment.ai_forecast_category`
- `Quota.amount` for coverage ratio

### Backend Endpoint
`GET /api/dashboard/trends/pipeline-flow?weeks=N&team=&deal_type=`

Returns: `{ waterfall, coverage_trend[], pipeline_by_category[] }`

---

## Tab 2: Forecast Movement

**Audience:** VP + Managers
**Answers:** "What shifted in the forecast this week?"

### Visualizations

#### A. Forecast Category Migration Table
- **Type:** shadcn Table (not Sankey — too sparse at 10-20 deals)
- **Columns:** Account, MRR, Previous Category, → Arrow, Current Category, Date
- **Row colors:** Green for upgrades (toward Commit), Red for downgrades (toward At Risk)
- **Sorted by:** MRR descending (highest-impact migrations first)
- **Click:** Row navigates to deal detail page

#### B. AI vs IC Divergence Trend
- **Type:** Recharts ComposedChart
- **Bar:** Divergent deal count per week (amber)
- **Line:** Divergence percentage per week (red dashed)
- **Clickable:** Points link to list of divergent deals

### Summary Cards (4)
| Card | Value |
|------|-------|
| Deals Moved This Week | Count of migrations |
| Positive Migrations | Upgrades count + value |
| Negative Migrations | Downgrades count + value |
| AI-IC Agreement Rate | % of deals where AI = IC forecast |

### Backend Endpoint
`GET /api/dashboard/trends/forecast-migration?weeks=N&team=&deal_type=`

Returns: `{ migrations[], migration_summary, divergence_trend[] }`

---

## Tab 3: Deal Health

**Audience:** Managers + ICs
**Answers:** "Which deals need attention?"

### Visualizations

#### A. Health Distribution Over Time
- **Type:** Recharts AreaChart (stacked)
- **Bands:** Healthy (green, ≥70), At Risk (amber, 45-69), Critical (red, <45)
- **Toggle:** Count vs percentage view

#### B. Biggest Movers Table
- **Type:** shadcn Table + inline Sparkline components
- **Columns:** Deal Name, MRR, Current Score, Delta, Sparkline (80x24px), Direction Badge, Last Call Date
- **Top 10** by absolute delta, sorted descending
- **Click:** Deal name → `/deals/[id]`

#### C. Component Averages
- **Type:** Recharts BarChart (horizontal)
- **Bars:** One per health dimension (8-10 components from `health_breakdown`)
- **Color:** By health zone (green/amber/red)
- **Delta annotation:** Small trend indicator on each bar

### Summary Cards (4)
| Card | Value |
|------|-------|
| Weighted Pipeline Health | (health_score/100 × mrr) summed |
| Avg Health Score | Portfolio mean + WoW delta |
| Deals in Critical | Count + MRR of score <45 |
| Biggest Mover | Deal name with largest absolute delta |

### Backend Endpoint
`GET /api/dashboard/trends/deal-health?weeks=N&team=&deal_type=`

Returns: `{ distribution_over_time[], biggest_movers[], component_averages[], weighted_health }`

---

## Tab 4: Velocity

**Audience:** Managers
**Answers:** "Which deals stopped moving?"

### Visualizations

#### A. Average Days per Stage
- **Type:** Recharts BarChart (grouped)
- **Two bars per stage:** avg_days (filled) + median_days (outline)
- **X-axis:** Stage name (7 stages), **Y-axis:** Days
- **Annotation:** Deal count above each group

#### B. Stalled Deals Table
- **Type:** shadcn Table
- **Columns:** Deal, MRR, Current Stage, Days in Stage, Median for Stage, Excess Days (Progress bar), Health Score
- **Stalled threshold:** 1.5x median for that stage
- **Highlight:** Rows >2x median get red left border (urgent)
- **Sorted by:** Excess days descending
- **Click:** Deal name → detail page

#### C. Stage Progression Events
- **Type:** Compact shadcn Table
- **Columns:** Date, Account, From Stage → To Stage, Direction badge
- **Direction:** "advance" (green ↑), "regression" (red ↓)
- **Sorted by:** Most recent first

### Summary Cards (4)
| Card | Value |
|------|-------|
| Avg Cycle Time | Weighted avg days from Stage 1 to current |
| Stalled Deals | Count exceeding 1.5x median |
| Stalled MRR | Sum of mrr_estimate for stalled deals |
| Bottleneck Stage | Stage with highest median duration |

### Backend Endpoint
`GET /api/dashboard/trends/velocity?weeks=N&team=&deal_type=`

Returns: `{ stage_durations[], stalled_deals[], stage_events[] }`

### Stage Duration Calculation
- Deal "enters" a stage when an assessment first assigns that `inferred_stage`
- Deal "exits" when a later assessment assigns a different stage
- Deals currently in a stage use today's date as the exit
- Stage regression: counts as a fresh entry; prior duration finalized

---

## Tab 5: Team Comparison

**Audience:** VP Sales
**Answers:** "Which teams need help?"
**Access:** VP / GM / Admin only. Team Leads see own team vs portfolio average.

### Visualizations

#### A. Team Pipeline Value Trend
- **Type:** Recharts LineChart (multi-line, one per team)
- **Colors:** Distinct color per team from existing `LINE_COLORS` palette
- **Legend:** Below chart, clickable to toggle teams

#### B. Cross-Team Benchmarking Table
- **Type:** shadcn Table (sortable columns)
- **Columns:** Team, Deals, Pipeline $, Avg Health, Weighted Health, Coverage, Velocity (avg days), Improving/Stable/Declining counts
- **Conditional formatting:** Cells colored green/amber/red by thresholds
- **Team Lead view:** Own team row + "Portfolio Average" comparison row

#### C. Team Momentum Distribution
- **Type:** Recharts BarChart (stacked, horizontal)
- **One bar per team:** Improving (green) / Stable (gray) / Declining (red) segments

### Summary Cards (4)
| Card | Value |
|------|-------|
| Top Pipeline Team | Highest pipeline value |
| Healthiest Team | Highest avg health |
| Most Improved | Biggest positive health delta |
| Needs Attention | Most stalled deals or lowest health |

### Backend Endpoint
`GET /api/dashboard/trends/team-comparison?weeks=N&deal_type=`

Returns: `{ team_pipeline_trend[], benchmark_table[], momentum_distribution[] }`

---

## Technical Architecture

### New Backend Endpoints (5)

All under `/api/dashboard/trends/`. All accept `weeks`, `team`, `deal_type` params. All apply role-based scoping via `_resolve_scoping()`.

| Endpoint | Service Function |
|----------|-----------------|
| `GET /trends/pipeline-flow` | `get_pipeline_flow()` |
| `GET /trends/forecast-migration` | `get_forecast_migration()` |
| `GET /trends/deal-health` | `get_deal_health()` |
| `GET /trends/velocity` | `get_velocity()` |
| `GET /trends/team-comparison` | `get_team_comparison()` |

### Shared Backend Helpers (in trend_service.py)

```
_get_assessments_in_window(session, weeks, visible_user_ids)
    → Single query: JOIN DealAssessment + Account, filtered by time + scope
    → Returns list of (DealAssessment, Account) tuples

_iso_week(dt) → "YYYY-WNN" string for weekly grouping

_latest_per_account(assessments) → Dict[account_id, DealAssessment]

FORECAST_RANK = {"Commit": 4, "Realistic": 3, "Upside": 2, "At Risk": 1}
```

### Frontend Component Tree

```
frontend/src/
  app/trends/page.tsx                              # REWRITE — 5-tab shell
  components/trends/
    pipeline-flow-tab.tsx                           # NEW
    forecast-movement-tab.tsx                       # NEW
    deal-health-tab.tsx                             # NEW
    velocity-tab.tsx                                # NEW
    team-comparison-tab.tsx                         # NEW
    sparkline.tsx                                   # NEW — reusable 80x24px line
    waterfall-chart.tsx                             # NEW — Recharts BarChart wrapper
    migration-table.tsx                             # NEW — forecast migration table
    stalled-deals-table.tsx                         # NEW — stalled deals with progress bars
  lib/
    hooks/use-trends.ts                             # NEW — React Query hooks (5)
    api.ts                                          # MODIFY — add 5 API methods
    api-types.ts                                    # MODIFY — add ~20 interfaces
```

### Data Fetching Strategy
- Each tab fetches independently via its own React Query hook
- No prefetch-all — users view one tab at a time, queries are <100ms
- `queryKey` includes `weeks` so changing the selector auto-refetches
- `staleTime` default (0) — data refreshes on each tab switch

### Chart Library
Continue using **Recharts 3.7** (already in project):
- `BarChart` — waterfall (floating bars), stage duration, momentum distribution
- `AreaChart` — health distribution, pipeline by category (stacked)
- `LineChart` — coverage ratio, team pipeline, sparklines
- `ComposedChart` — divergence trend (bar + line overlay)
- **Custom**: Waterfall (Recharts `[start, end]` stacked bar pattern)
- **Custom**: Sparkline (Recharts LineChart at 80x24px, no chrome)
- **Custom**: Migration matrix (HTML table with conditional coloring)

### Performance (SQLite at 20 deals × ~200 rows)
- All queries use existing index `ix_deal_assessments_account (account_id, created_at)`
- `health_breakdown` JSON parsing done in Python — negligible at this scale
- No materialized views, no SSR, no virtualization, no WebSocket needed
- Recommended future index: `Index("ix_accounts_owner", "owner_id")` if >50 deals

---

## Empty State Design

| Scenario | Message | CTA |
|----------|---------|-----|
| No deals at all | "No deals in your pipeline" | "Go to Import" → /upload |
| Deals but no assessments | "Deals found, but no analysis yet" | "Analyze Deals" → /upload |
| Only 1 assessment per deal | "Building your trend history — re-analyze weekly" | Informational |
| No data in time window | "No data in this time range" | "Reset to 4 weeks" |
| Sparse data (<5 deals) | Banner: "Showing N deals over M weeks. Trends become more reliable with more data." | None |
| Team Lead on Team Comparison | Own team row + Portfolio Average comparison | None |

---

## Implementation Phasing

| Phase | Tabs | Effort | Why This Order |
|-------|------|--------|----------------|
| 1 | Shared helpers + Deal Health (Tab 3) | ~1.5 days | Closest to existing code — validates new pattern |
| 2 | Pipeline Flow (Tab 1) | ~1.5 days | Highest product value — the "killer" waterfall |
| 3 | Forecast Movement (Tab 2) | ~1 day | Builds on migration logic |
| 4 | Velocity (Tab 4) | ~1 day | Independent computation — can parallel with Phase 3 |
| 5 | Team Comparison (Tab 5) | ~1 day | Leverages existing hierarchy |
| 6 | Page shell rewrite + sidebar wiring | ~0.5 day | Wire all 5 tabs together |
| 7 | Polish: empty states, edge cases, cleanup | ~0.5 day | Final pass |

**Total estimated effort: ~7 days**

Phases 3 and 4 can run in parallel.

---

## Edge Cases

### Data Sparsity
- Box plots with N<3 degrade to individual data points
- Sparklines with 1 data point show a single dot, delta shows "--"
- Coverage ratio returns `null` when quota is 0 or missing → shows "--"

### Stage Handling
- Stage regression counts as a fresh entry; prior duration finalized
- Deals with only 1 assessment: excluded from velocity box plot, included in stalled table based on time since assessment
- Both new_logo (7 stages) and expansion stage models supported

### Health Breakdown
- Handles both array and object JSON formats (matching existing HealthBreakdown component)
- Missing/malformed `health_breakdown`: skip in component heatmap, use top-level `health_score` for tier distribution

### Team Comparison with Few Teams
- 1 team (TL view): show team row + "Portfolio Average" row
- Team with 0 deals: row appears with "--" values
- >8 teams: auto-limit chart to top 8 by pipeline value, "Show all" toggle

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Weekly active users on /trends | 80% of VP + Manager users visit 1x/week within 4 weeks |
| Time on page | >3 minutes avg (meaningful analysis, not confusion) |
| Tab distribution | No tab <10% of visits |
| Pipeline review prep time | Qualitative: managers report faster prep |
| Forecast divergence rate | Decreases over 8 weeks (managers acting on data) |

---

## Files Referenced

- Current trends page: `frontend/src/app/trends/page.tsx`
- Trend service: `sis/services/trend_service.py`
- Dashboard routes: `sis/api/routes/dashboard.py`
- DB models: `sis/db/models.py`
- Sidebar: `frontend/src/components/sidebar.tsx`
- API client: `frontend/src/lib/api.ts`
- API types: `frontend/src/lib/api-types.ts`
