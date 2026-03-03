'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { useDivergence } from '@/lib/hooks/use-dashboard';
import { useHierarchyTeams } from '@/lib/hooks/use-admin';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { HealthBadge } from '@/components/health-badge';
import { ForecastBadge } from '@/components/forecast-badge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DivergenceItem {
  account_id: string;
  account_name: string;
  cp_estimate: number | null;
  team_lead: string | null;
  ai_forecast_category: string | null;
  sf_forecast_category: string | null;
  health_score: number | null;
  divergence_explanation: string | null;
  forecast_rationale: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMrr(value: number | null): string {
  if (value === null || value === undefined) return '--';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toLocaleString()}`;
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function SkeletonRow() {
  return (
    <TableRow>
      {Array.from({ length: 6 }).map((_, i) => (
        <TableCell key={i}>
          <div className="h-4 animate-pulse rounded bg-muted" style={{ width: `${60 + i * 10}px` }} />
        </TableCell>
      ))}
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DivergencePage() {
  const [teamId, setTeamId] = useState<string | undefined>(undefined);

  const { data: rawData, isLoading, isError, error } = useDivergence(teamId);
  const { data: teams = [] } = useHierarchyTeams();

  const items = useMemo<DivergenceItem[]>(() => {
    if (!rawData) return [];
    const list = rawData as DivergenceItem[];
    // Sort by MRR descending — highest value impact first
    return [...list].sort((a, b) => (b.cp_estimate ?? 0) - (a.cp_estimate ?? 0));
  }, [rawData]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Forecast Alignment Check</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading
              ? 'Loading divergence data...'
              : `${items.length} deal${items.length !== 1 ? 's' : ''} where AI and SF forecasts differ`}
          </p>
        </div>

        {teams.length > 0 && (
          <Select
            value={teamId ?? 'all'}
            onValueChange={(v) => setTeamId(v === 'all' ? undefined : v)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Teams" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Teams</SelectItem>
              {teams.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Error state */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load divergence data</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      {!isError && (
        <Card>
          <CardContent className="p-0">
            {/* Horizontal scroll wrapper for mobile */}
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Account</TableHead>
                    <TableHead className="text-right">MRR</TableHead>
                    <TableHead>AI Forecast</TableHead>
                    <TableHead>SF Forecast</TableHead>
                    <TableHead>Health</TableHead>
                    <TableHead>Explanation</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading && (
                    <>
                      <SkeletonRow />
                      <SkeletonRow />
                      <SkeletonRow />
                      <SkeletonRow />
                      <SkeletonRow />
                    </>
                  )}

                  {!isLoading && items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <div className="flex items-center justify-center py-12 text-muted-foreground">
                          All forecasts are aligned
                        </div>
                      </TableCell>
                    </TableRow>
                  )}

                  {!isLoading &&
                    items.map((item) => (
                      <TableRow key={item.account_id}>
                        <TableCell className="font-medium">
                          <Link
                            href={`/deals/${item.account_id}`}
                            className="hover:underline"
                          >
                            {item.account_name}
                          </Link>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMrr(item.cp_estimate)}
                        </TableCell>
                        <TableCell>
                          <ForecastBadge category={item.ai_forecast_category} />
                        </TableCell>
                        <TableCell>
                          <ForecastBadge category={item.sf_forecast_category} />
                        </TableCell>
                        <TableCell>
                          <HealthBadge score={item.health_score} />
                        </TableCell>
                        <TableCell className="max-w-xs text-sm text-muted-foreground">
                          {item.divergence_explanation ?? '--'}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
