'use client';

import { useState, useMemo } from 'react';
import { useDealTrends, useTeamTrends, usePortfolioSummary } from '@/lib/hooks/use-dashboard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DealTrend {
  account_id: string;
  account_name: string;
  weeks: Array<{ week: string; score: number | null }>;
  delta: number | null;
  direction: string | null;
}

interface TeamTrend {
  team_name: string;
  weeks: Array<{ week: string; avg_score: number | null }>;
  delta: number | null;
  direction: string | null;
  deal_count: number;
}

interface PortfolioSummary {
  improving: number;
  stable: number;
  declining: number;
  avg_delta: number | null;
  biggest_mover: { account_name: string; delta: number } | null;
  weeks_analyzed: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const LINE_COLORS = [
  '#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
];

function DirectionBadge({ direction }: { direction: string | null }) {
  if (!direction) return <span className="text-muted-foreground text-sm">--</span>;

  const normalized = direction.toLowerCase();
  if (normalized === 'improving') {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-emerald-600 dark:text-emerald-400">
        <TrendingUp className="size-3.5" />
        Improving
      </span>
    );
  }
  if (normalized === 'declining') {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-red-600 dark:text-red-400">
        <TrendingDown className="size-3.5" />
        Declining
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
      <Minus className="size-3.5" />
      Stable
    </span>
  );
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-muted-foreground">--</span>;
  const sign = delta > 0 ? '+' : '';
  const colorClass =
    delta > 0
      ? 'text-emerald-600 dark:text-emerald-400'
      : delta < 0
        ? 'text-red-600 dark:text-red-400'
        : 'text-muted-foreground';
  return (
    <span className={`tabular-nums font-medium ${colorClass}`}>
      {sign}{Math.round(delta * 10) / 10}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return <div className="h-32 rounded-xl border bg-muted/20 animate-pulse" />;
}

function SkeletonChart() {
  return <div className="h-64 w-full animate-pulse rounded-lg bg-muted" />;
}

// ---------------------------------------------------------------------------
// Portfolio tab
// ---------------------------------------------------------------------------

function PortfolioTab({ weeks }: { weeks: number }) {
  const { data: rawSummary, isLoading, isError, error } = usePortfolioSummary(weeks);
  const summary = rawSummary as PortfolioSummary | undefined;

  if (isError) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive font-medium">Failed to load portfolio summary</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Improving</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                  {summary?.improving ?? '--'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Stable</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">{summary?.stable ?? '--'}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Declining</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400 tabular-nums">
                  {summary?.declining ?? '--'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Avg Delta</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold tabular-nums">
                  {summary?.avg_delta !== null && summary?.avg_delta !== undefined
                    ? `${summary.avg_delta > 0 ? '+' : ''}${Math.round(summary.avg_delta * 10) / 10}`
                    : '--'}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Biggest mover */}
      {!isLoading && summary?.biggest_mover && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Biggest Mover</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="font-medium">{summary.biggest_mover.account_name}</span>
              <DeltaBadge delta={summary.biggest_mover.delta} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Overview note */}
      {!isLoading && summary && (
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">
              Portfolio trend analysis over the last{' '}
              <span className="font-medium text-foreground">{summary.weeks_analyzed}</span>{' '}
              week{summary.weeks_analyzed !== 1 ? 's' : ''}. Totals:{' '}
              <span className="font-medium text-foreground">
                {(summary.improving ?? 0) + (summary.stable ?? 0) + (summary.declining ?? 0)}
              </span>{' '}
              deals tracked.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Teams tab
// ---------------------------------------------------------------------------

function TeamsTab({ weeks }: { weeks: number }) {
  const { data: rawTeams, isLoading, isError, error } = useTeamTrends(weeks);
  const teams = useMemo<TeamTrend[]>(() => {
    if (!rawTeams) return [];
    return rawTeams as TeamTrend[];
  }, [rawTeams]);

  if (isError) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive font-medium">Failed to load team trends</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Team Trend Summary</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Team</TableHead>
                <TableHead className="text-right">Deals</TableHead>
                <TableHead className="text-right">Delta</TableHead>
                <TableHead>Direction</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading && (
                <>
                  {Array.from({ length: 4 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 4 }).map((__, j) => (
                        <TableCell key={j}>
                          <div className="h-4 animate-pulse rounded bg-muted w-20" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </>
              )}
              {!isLoading && teams.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>
                    <div className="py-8 text-center text-muted-foreground">
                      No team trend data available
                    </div>
                  </TableCell>
                </TableRow>
              )}
              {!isLoading &&
                teams.map((team) => (
                  <TableRow key={team.team_name}>
                    <TableCell className="font-medium">{team.team_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{team.deal_count}</TableCell>
                    <TableCell className="text-right">
                      <DeltaBadge delta={team.delta} />
                    </TableCell>
                    <TableCell>
                      <DirectionBadge direction={team.direction} />
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Deals tab
// ---------------------------------------------------------------------------

function buildChartData(deals: DealTrend[]): Array<Record<string, string | number | null>> {
  if (deals.length === 0) return [];

  // Collect all week labels from all deals
  const weekSet = new Set<string>();
  deals.forEach((d) => d.weeks.forEach((w) => weekSet.add(w.week)));
  const weekLabels = Array.from(weekSet).sort();

  return weekLabels.map((week) => {
    const row: Record<string, string | number | null> = { week };
    deals.forEach((deal) => {
      const match = deal.weeks.find((w) => w.week === week);
      row[deal.account_name] = match?.score ?? null;
    });
    return row;
  });
}

function DealsTab({ weeks }: { weeks: number }) {
  const { data: rawDeals, isLoading, isError, error } = useDealTrends({ weeks });
  const deals = useMemo<DealTrend[]>(() => {
    if (!rawDeals) return [];
    return rawDeals as DealTrend[];
  }, [rawDeals]);

  const chartData = useMemo(() => buildChartData(deals), [deals]);

  if (isError) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive font-medium">Failed to load deal trends</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Line chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Health Score Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <SkeletonChart />
          ) : deals.length === 0 ? (
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              No trend data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
                  formatter={(value: number | undefined) =>
                    value !== undefined ? [Math.round(value), ''] : ['--', '']
                  }
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                {deals.map((deal, i) => (
                  <Line
                    key={deal.account_id}
                    type="monotone"
                    dataKey={deal.account_name}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Deals table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Deal Summary</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                  <TableHead>Direction</TableHead>
                  <TableHead className="text-right">Data Points</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && (
                  <>
                    {Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 4 }).map((__, j) => (
                          <TableCell key={j}>
                            <div className="h-4 animate-pulse rounded bg-muted w-24" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </>
                )}
                {!isLoading && deals.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <div className="py-8 text-center text-muted-foreground">
                        No deal trend data available
                      </div>
                    </TableCell>
                  </TableRow>
                )}
                {!isLoading &&
                  deals.map((deal) => (
                    <TableRow key={deal.account_id}>
                      <TableCell className="font-medium">{deal.account_name}</TableCell>
                      <TableCell className="text-right">
                        <DeltaBadge delta={deal.delta} />
                      </TableCell>
                      <TableCell>
                        <DirectionBadge direction={deal.direction} />
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {deal.weeks.filter((w) => w.score !== null).length}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const WEEK_OPTIONS = [4, 8, 12];

export default function TrendsPage() {
  const [weeks, setWeeks] = useState(4);
  const [activeTab, setActiveTab] = useState('portfolio');

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Trend Analysis</h1>
          <p className="text-sm text-muted-foreground">
            Health score trajectories over time
          </p>
        </div>

        {/* Week selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Weeks:</span>
          <div className="flex gap-1">
            {WEEK_OPTIONS.map((w) => (
              <Badge
                key={w}
                variant={weeks === w ? 'default' : 'outline'}
                className="cursor-pointer select-none min-w-[44px] justify-center py-2"
                onClick={() => setWeeks(w)}
              >
                {w}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 sm:w-auto sm:inline-flex">
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="teams">Teams</TabsTrigger>
          <TabsTrigger value="deals">Deals</TabsTrigger>
        </TabsList>

        <TabsContent value="portfolio" className="mt-4">
          <PortfolioTab weeks={weeks} />
        </TabsContent>

        <TabsContent value="teams" className="mt-4">
          <TeamsTab weeks={weeks} />
        </TabsContent>

        <TabsContent value="deals" className="mt-4">
          <DealsTab weeks={weeks} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
