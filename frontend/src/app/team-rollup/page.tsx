'use client';

import { useState, useMemo } from 'react';
import { useTeamRollup } from '@/lib/hooks/use-dashboard';
import { useForecastTeams } from '@/lib/hooks/use-admin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TeamRollupItem {
  team_name: string;
  total_deals: number;
  scored_deals: number;
  avg_health_score: number | null;
  healthy_count: number;
  at_risk_count: number;
  critical_count: number;
  total_mrr: number | null;
  divergent_count: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMrr(value: number | null): string {
  if (value === null || value === undefined) return '--';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function formatScore(value: number | null): string {
  if (value === null || value === undefined) return '--';
  return value.toFixed(1);
}

// ---------------------------------------------------------------------------
// Loading skeletons
// ---------------------------------------------------------------------------

function SkeletonChart() {
  return (
    <div className="h-64 w-full animate-pulse rounded-lg bg-muted" />
  );
}

function SkeletonTableRow() {
  return (
    <TableRow>
      {Array.from({ length: 7 }).map((_, i) => (
        <TableCell key={i}>
          <div className="h-4 animate-pulse rounded bg-muted" style={{ width: `${50 + i * 8}px` }} />
        </TableCell>
      ))}
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// Chart colors matching the brand palette
// ---------------------------------------------------------------------------

const CHART_COLORS = {
  healthy: '#059669',
  at_risk: '#d97706',
  critical: '#dc2626',
};

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function TeamRollupPage() {
  const [team, setTeam] = useState<string | undefined>(undefined);

  const { data: rawData, isLoading, isError, error } = useTeamRollup(team);
  const { data: teams = [] } = useForecastTeams();

  const items = useMemo<TeamRollupItem[]>(() => {
    if (!rawData) return [];
    return rawData as TeamRollupItem[];
  }, [rawData]);

  // Transform data for Recharts stacked bar chart
  const chartData = useMemo(() => {
    return items.map((item) => ({
      name: item.team_name,
      Healthy: item.healthy_count,
      'At Risk': item.at_risk_count,
      Critical: item.critical_count,
    }));
  }, [items]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Team Performance</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading
              ? 'Loading team data...'
              : `${items.length} team${items.length !== 1 ? 's' : ''} in view`}
          </p>
        </div>

        {teams.length > 0 && (
          <Select
            value={team ?? 'all'}
            onValueChange={(v) => setTeam(v === 'all' ? undefined : v)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Teams" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Teams</SelectItem>
              {teams.map((t: string) => (
                <SelectItem key={t} value={t}>
                  {t}
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
            <p className="text-destructive font-medium">Failed to load team data</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Stacked bar chart */}
      {!isError && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Deal Health by Team</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <SkeletonChart />
            ) : items.length === 0 ? (
              <div className="flex h-48 items-center justify-center text-muted-foreground">
                No team data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={chartData}
                  margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: '12px',
                      borderRadius: '6px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="Healthy" stackId="a" fill={CHART_COLORS.healthy} isAnimationActive={false} />
                  <Bar dataKey="At Risk" stackId="a" fill={CHART_COLORS.at_risk} isAnimationActive={false} />
                  <Bar dataKey="Critical" stackId="a" fill={CHART_COLORS.critical} radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* Summary table */}
      {!isError && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Team Summary</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Team</TableHead>
                    <TableHead className="text-right">Total Deals</TableHead>
                    <TableHead className="text-right">Avg Health</TableHead>
                    <TableHead className="text-right text-healthy">Healthy</TableHead>
                    <TableHead className="text-right text-at-risk">At Risk</TableHead>
                    <TableHead className="text-right text-critical">Critical</TableHead>
                    <TableHead className="text-right">Total MRR</TableHead>
                    <TableHead className="text-right">Divergent</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading && (
                    <>
                      <SkeletonTableRow />
                      <SkeletonTableRow />
                      <SkeletonTableRow />
                    </>
                  )}

                  {!isLoading && items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8}>
                        <div className="flex items-center justify-center py-10 text-muted-foreground">
                          No team data available
                        </div>
                      </TableCell>
                    </TableRow>
                  )}

                  {!isLoading &&
                    items.map((item) => (
                      <TableRow key={item.team_name}>
                        <TableCell className="font-medium">{item.team_name}</TableCell>
                        <TableCell className="text-right tabular-nums">{item.total_deals}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatScore(item.avg_health_score)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-healthy">
                          {item.healthy_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-at-risk">
                          {item.at_risk_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-critical">
                          {item.critical_count}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMrr(item.total_mrr)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {item.divergent_count}
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
