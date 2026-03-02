'use client';

import { useState, useMemo, useCallback, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useCommandCenter } from '@/lib/hooks/use-command-center';
import { usePermissions } from '@/lib/permissions';
import { usePipelineWidgets, type WidgetConfig } from '@/lib/hooks/use-preferences';
import { api } from '@/lib/api';
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
import { AttentionStrip } from '@/components/attention-strip';
import { PipelineChanges } from '@/components/pipeline-changes';
import {
  FilterChips,
  type ForecastFilter,
  type HealthFilter,
  type FlagFilter,
} from '@/components/filter-chips';
import { DataTable } from '@/components/data-table';
import { TeamForecastGrid } from '@/components/team-forecast-grid';
import type { PipelineDeal } from '@/lib/pipeline-types';

// ---------------------------------------------------------------------------
// Quarter helper
// ---------------------------------------------------------------------------

function currentQuarter(): string {
  const m = new Date().getMonth();
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

function healthTier(score: number | null): 'healthy' | 'neutral' | 'needs_attention' | null {
  if (score === null) return null;
  if (score >= 70) return 'healthy';
  if (score >= 40) return 'neutral';
  return 'needs_attention';
}

function isStale(deal: PipelineDeal): boolean {
  if (!deal.last_call_date) return true;
  const d = new Date(deal.last_call_date);
  const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  return diff >= 30;
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

    // Health filter (any selected must match)
    if (healthFilters.length > 0) {
      const tier = healthTier(d.health_score);
      if (!tier || !healthFilters.includes(tier)) return false;
    }

    // Flag filters (all selected must match)
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

function getVisiblePipelineWidgets(widgets: WidgetConfig[]): WidgetConfig[] {
  return widgets
    .filter((w) => w.visible)
    .sort((a, b) => a.order - b.order);
}

export default function PipelineCommandCenter() {
  const [quarter, setQuarter] = useState('FY');
  const [team, setTeam] = useState<string | undefined>(undefined);
  const [teamLeadFilter, setTeamLeadFilter] = useState<string | undefined>(undefined);
  const [forecastFilter, setForecastFilter] = useState<ForecastFilter>('all');
  const [healthFilters, setHealthFilters] = useState<HealthFilter[]>([]);
  const [flagFilters, setFlagFilters] = useState<FlagFilter[]>([]);

  const { isVpOrAbove } = usePermissions();
  const { data: widgetPrefs } = usePipelineWidgets();

  const { data: teamsData } = useQuery<{ id: string; name: string; level: string; leader_name: string | null }[]>({
    queryKey: ['teams'],
    queryFn: () => api.teams.list(),
    staleTime: 5 * 60_000,
  });

  const { data, isLoading, isError, error } = useCommandCenter({
    quarter: quarter === 'FY' ? undefined : quarter,
    team,
  });

  // Compute health & flag counts from all deals (before filtering)
  const counts = useMemo(() => {
    if (!data) return { health: { healthy: 0, neutral: 0, needs_attention: 0 }, flags: { divergent: 0, stale: 0, declining: 0 } };
    const deals = data.deals;
    return {
      health: {
        healthy: deals.filter((d) => healthTier(d.health_score) === 'healthy').length,
        neutral: deals.filter((d) => healthTier(d.health_score) === 'neutral').length,
        needs_attention: deals.filter((d) => healthTier(d.health_score) === 'needs_attention').length,
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
    let deals = filterDeals(data.deals, forecastFilter, healthFilters, flagFilters);
    if (teamLeadFilter) {
      deals = deals.filter((d) => d.team_lead === teamLeadFilter);
    }
    return deals;
  }, [data, forecastFilter, healthFilters, flagFilters, teamLeadFilter]);

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
    setTeamLeadFilter(undefined);
  }, []);

  const handleGridCellClick = useCallback((teamLead: string | null, category: string | null) => {
    // Toggle: if clicking same combination, clear both
    if (teamLead === (teamLeadFilter ?? null) && category === (forecastFilter === 'all' ? null : forecastFilter)) {
      setTeamLeadFilter(undefined);
      setForecastFilter('all');
      return;
    }
    setTeamLeadFilter(teamLead ?? undefined);
    setForecastFilter(category ? (category as ForecastFilter) : 'all');
  }, [teamLeadFilter, forecastFilter]);

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

          {/* Team filter */}
          <Select
            value={team ?? 'all'}
            onValueChange={(v) => setTeam(v === 'all' ? undefined : v)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Teams" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Teams</SelectItem>
              {teamsData && teamsData.length > 0 && (
                <>
                  {teamsData.filter((t) => t.level === 'division').length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-[10px] uppercase tracking-wider">VPs</SelectLabel>
                      {teamsData
                        .filter((t) => t.level === 'division')
                        .map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.leader_name || t.name}
                          </SelectItem>
                        ))}
                    </SelectGroup>
                  )}
                  {teamsData.filter((t) => t.level === 'team').length > 0 && (
                    <SelectGroup>
                      <SelectLabel className="text-[10px] uppercase tracking-wider">Teams</SelectLabel>
                      {teamsData
                        .filter((t) => t.level === 'team')
                        .map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.leader_name || t.name}
                          </SelectItem>
                        ))}
                    </SelectGroup>
                  )}
                </>
              )}
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
          {/* Number Line — always sticky at top (structural) */}
          <div className="sticky top-0 z-10 bg-background pb-2">
            <NumberLine
              quota={data.quota}
              pipeline={data.pipeline}
              forecast={data.forecast_breakdown}
            />
          </div>

          {/* Dynamic widgets from user preferences */}
          {(() => {
            const visibleWidgets = getVisiblePipelineWidgets(widgetPrefs ?? []);
            const filterChipsVisible = visibleWidgets.some((w) => w.id === 'filter_chips');

            const renderWidget = (id: string): ReactNode => {
              switch (id) {
                case 'number_line':
                  return null; // rendered sticky above
                case 'attention_strip':
                  return <AttentionStrip key={id} items={data.attention_items} />;
                case 'pipeline_changes':
                  return <PipelineChanges key={id} changes={data.changes_this_week} />;
                case 'filter_chips':
                  return (
                    <FilterChips
                      key={id}
                      activeHealth={healthFilters}
                      activeFlags={flagFilters}
                      onHealthToggle={handleHealthToggle}
                      onFlagToggle={handleFlagToggle}
                      onClearAll={clearAllFilters}
                      healthCounts={counts.health}
                      flagCounts={counts.flags}
                      hasExternalFilters={forecastFilter !== 'all' || !!teamLeadFilter}
                    />
                  );
                case 'deal_table':
                  return <DataTable key={id} deals={filterChipsVisible ? filteredDeals : data.deals} />;
                case 'team_forecast_grid':
                  return isVpOrAbove ? (
                    <TeamForecastGrid
                      key={id}
                      deals={data.deals}
                      onCellClick={handleGridCellClick}
                      activeTeamLead={teamLeadFilter ?? null}
                      activeForecastCategory={forecastFilter === 'all' ? null : forecastFilter}
                    />
                  ) : null;
                default:
                  return null;
              }
            };

            return visibleWidgets.map((w) => renderWidget(w.id));
          })()}
        </>
      )}
    </div>
  );
}
