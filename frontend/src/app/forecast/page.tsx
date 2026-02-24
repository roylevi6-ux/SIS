'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { useForecastData, useForecastTeams } from '@/lib/hooks/use-admin';
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
import { HealthBadge } from '@/components/health-badge';
import { ForecastBadge } from '@/components/forecast-badge';
import { MomentumIndicator } from '@/components/momentum-indicator';
import { DivergenceBadge } from '@/components/divergence-badge';
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

interface ForecastDataItem {
  account_id: string;
  account_name: string;
  mrr: number | null;
  team_name: string | null;
  ae_owner: string | null;
  ai_forecast: string | null;
  ic_forecast: string | null;
  health_score: number | null;
  momentum: string | null;
  divergence: boolean;
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

function formatPipelineTotal(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

const FORECAST_CATEGORIES = [
  'Commit',
  'Realistic',
  'Upside',
  'At Risk',
];

// ---------------------------------------------------------------------------
// Build grouped bar chart data: count of AI vs IC per category
// ---------------------------------------------------------------------------

function buildChartData(items: ForecastDataItem[]) {
  return FORECAST_CATEGORIES.map((cat) => ({
    category: cat,
    AI: items.filter((d) => d.ai_forecast === cat).length,
    IC: items.filter((d) => d.ic_forecast === cat).length,
  })).filter((row) => row.AI > 0 || row.IC > 0);
}

// ---------------------------------------------------------------------------
// Loading skeletons
// ---------------------------------------------------------------------------

function SkeletonChart() {
  return <div className="h-64 w-full animate-pulse rounded-lg bg-muted" />;
}

function SkeletonRow() {
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
// Summary stat card
// ---------------------------------------------------------------------------

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tabular-nums">{value}</div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ForecastPage() {
  const [team, setTeam] = useState<string | undefined>(undefined);

  const { data: rawData, isLoading, isError, error } = useForecastData(team);
  const { data: teams = [] } = useForecastTeams();

  const items = useMemo<ForecastDataItem[]>(() => {
    if (!rawData) return [];
    return rawData as unknown as ForecastDataItem[];
  }, [rawData]);

  const chartData = useMemo(() => buildChartData(items), [items]);

  const divergentCount = useMemo(() => items.filter((d) => d.divergence).length, [items]);

  const weightedPipelineTotal = useMemo(
    () => items.reduce((sum, d) => sum + (d.mrr ?? 0), 0),
    [items],
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI vs IC Forecast</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading ? 'Loading forecast data...' : `${items.length} deals in view`}
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
            <p className="text-destructive font-medium">Failed to load forecast data</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Summary stats */}
      {!isError && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <StatCard label="Total Deals" value={isLoading ? '...' : items.length} />
          <StatCard label="Divergent" value={isLoading ? '...' : divergentCount} />
          <StatCard
            label="Weighted Pipeline"
            value={isLoading ? '...' : formatPipelineTotal(weightedPipelineTotal)}
          />
        </div>
      )}

      {/* Grouped bar chart: AI vs IC category distribution */}
      {!isError && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Forecast Category Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <SkeletonChart />
            ) : chartData.length === 0 ? (
              <div className="flex h-48 items-center justify-center text-muted-foreground">
                No forecast data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={chartData}
                  margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis
                    dataKey="category"
                    tick={{ fontSize: 11 }}
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
                  <Bar dataKey="AI" fill="#6366f1" name="AI Forecast" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  <Bar dataKey="IC" fill="#0ea5e9" name="IC Forecast" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* Deal table */}
      {!isError && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Deal Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Account</TableHead>
                    <TableHead className="text-right">MRR</TableHead>
                    <TableHead>AI Forecast</TableHead>
                    <TableHead>IC Forecast</TableHead>
                    <TableHead>Health</TableHead>
                    <TableHead>Momentum</TableHead>
                    <TableHead>Divergence</TableHead>
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
                      <TableCell colSpan={7}>
                        <div className="flex items-center justify-center py-12 text-muted-foreground">
                          No forecast data available
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
                          {formatMrr(item.mrr)}
                        </TableCell>
                        <TableCell>
                          <ForecastBadge category={item.ai_forecast} />
                        </TableCell>
                        <TableCell>
                          <ForecastBadge category={item.ic_forecast} />
                        </TableCell>
                        <TableCell>
                          <HealthBadge score={item.health_score} />
                        </TableCell>
                        <TableCell>
                          <MomentumIndicator
                            direction={
                              item.momentum as 'Improving' | 'Stable' | 'Declining' | null
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <DivergenceBadge divergence={item.divergence} />
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
