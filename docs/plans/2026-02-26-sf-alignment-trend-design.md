# SF Alignment Trend Chart — Design Doc

**Date**: 2026-02-26
**Status**: Approved

## Problem

The "AI vs IC Divergence Trend" chart on the Trends page shows flat zero. It reads from `Account.ic_forecast_category` (never populated) instead of the SF Gap fields on `DealAssessment` that Agent 10 computes during pipeline execution.

## Solution

Replace the broken divergence computation with one that uses `DealAssessment.stage_gap_direction` and `DealAssessment.forecast_gap_direction` — the same data the pipeline page's SF Gap column displays successfully.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chart layout | Stacked bars + % line | Total misalignment at a glance, breakdown secondary |
| KPI card | One combined card, both %s | Saves space, shows which gap type matters |
| Chart title | "Salesforce Alignment Trend" | Clear for sales audience, positive framing |
| Direction | Misaligned only on chart, direction in tooltip | Keeps chart scannable, detail on demand |
| KPI label | "Pipeline Alignment" | Matches VP Sales mental model |
| Gap threshold | Any mismatch counts | Simple, transparent |

## Data Shape

### Backend Response (per week)

```json
{
  "week": "2026-W08",
  "total_deals": 22,
  "stage_gap_count": 5,
  "stage_sf_ahead": 3,
  "stage_sis_ahead": 2,
  "forecast_gap_count": 3,
  "forecast_sf_optimistic": 2,
  "forecast_sis_optimistic": 1,
  "any_gap_count": 7,
  "alignment_pct": 68.2
}
```

### Frontend Chart

- **Stacked bars**: orange (stage gap) + purple (forecast gap) on left Y-axis
- **Red dashed line**: alignment % on right Y-axis (inverted — shows alignment not divergence)
- **Tooltip**: shows directional breakdown on hover
- **KPI card**: "Pipeline Alignment" with Stage % and Forecast % sub-metrics + week-over-week delta

## Files Changed

1. `sis/services/trend_service.py` — `get_forecast_migration()` divergence computation
2. `frontend/src/lib/api-types.ts` — `DivergenceTrendPoint` type
3. `frontend/src/components/trends/forecast-movement-tab.tsx` — chart + KPI card
