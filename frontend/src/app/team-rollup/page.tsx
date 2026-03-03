'use client';

import { useState, useMemo, Fragment } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useTeamRollupHierarchy } from '@/lib/hooks/use-dashboard';
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
import type {
  TeamRollupHierarchyTeam,
  TeamRollupHierarchyRep,
  TeamRollupHierarchyDeal,
} from '@/lib/api-types';

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

function healthColor(score: number | null): string {
  if (score === null) return 'text-muted-foreground';
  if (score >= 70) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 40) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
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
      {Array.from({ length: 8 }).map((_, i) => (
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
  neutral: '#d97706',
  needs_attention: '#dc2626',
};

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function TeamRollupPage() {
  const [team, setTeam] = useState<string | undefined>(undefined);
  const [expandedTeam, setExpandedTeam] = useState<string | null>(null);
  const [expandedRep, setExpandedRep] = useState<string | null>(null);

  const { data: rawData, isLoading, isError, error } = useTeamRollupHierarchy(team);
  const { data: teams = [] } = useForecastTeams();

  const items = useMemo<TeamRollupHierarchyTeam[]>(() => {
    if (!rawData) return [];
    return rawData;
  }, [rawData]);

  // Chart data: when a team is selected, show rep-level bars; otherwise team-level
  const chartData = useMemo(() => {
    if (team && items.length === 1 && items[0].reps.length > 0) {
      return items[0].reps.map((rep) => ({
        name: rep.rep_name,
        Healthy: rep.healthy_count,
        Neutral: rep.neutral_count,
        'Needs Attention': rep.needs_attention_count,
      }));
    }
    return items.map((item) => ({
      name: item.team_name,
      Healthy: item.healthy_count,
      Neutral: item.neutral_count,
      'Needs Attention': item.needs_attention_count,
    }));
  }, [items, team]);

  function toggleTeam(teamName: string) {
    setExpandedTeam(expandedTeam === teamName ? null : teamName);
    setExpandedRep(null);
  }

  function toggleRep(repKey: string) {
    setExpandedRep(expandedRep === repKey ? null : repKey);
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Team Performance</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading
              ? 'Loading team data...'
              : `${items.length} team${items.length !== 1 ? 's' : ''} in view`}
          </p>
        </div>

        {teams.length > 0 && (
          <Select
            value={team ?? 'all'}
            onValueChange={(v) => {
              setTeam(v === 'all' ? undefined : v);
              setExpandedTeam(null);
              setExpandedRep(null);
            }}
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
            <CardTitle className="text-base">
              {team ? `Rep Health — ${team}` : 'Deal Health by Team'}
            </CardTitle>
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
                  <Bar dataKey="Neutral" stackId="a" fill={CHART_COLORS.neutral} isAnimationActive={false} />
                  <Bar dataKey="Needs Attention" stackId="a" fill={CHART_COLORS.needs_attention} radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* Expandable hierarchy table */}
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
                    <TableHead className="w-8" />
                    <TableHead>Team</TableHead>
                    <TableHead className="text-right">Deals</TableHead>
                    <TableHead className="text-right">Avg Health</TableHead>
                    <TableHead className="text-right text-emerald-600">Healthy</TableHead>
                    <TableHead className="text-right text-amber-600">Neutral</TableHead>
                    <TableHead className="text-right text-red-600">Needs Attention</TableHead>
                    <TableHead className="text-right">Total MRR</TableHead>
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
                    items.map((teamItem) => (
                      <Fragment key={teamItem.team_name}>
                        {/* Team row */}
                        <TableRow
                          className={`cursor-pointer hover:bg-muted/50 font-medium ${
                            teamItem.needs_attention_count > 0 ? 'border-l-4 border-l-red-500' : ''
                          }`}
                          onClick={() => toggleTeam(teamItem.team_name)}
                        >
                          <TableCell className="w-8 pl-4">
                            {expandedTeam === teamItem.team_name ? (
                              <ChevronDown className="size-4 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="size-4 text-muted-foreground" />
                            )}
                          </TableCell>
                          <TableCell>
                            <div>
                              <span className="font-medium">{teamItem.team_name}</span>
                              {teamItem.team_lead && (
                                <span className="text-xs text-muted-foreground ml-2">
                                  ({teamItem.team_lead})
                                </span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{teamItem.total_deals}</TableCell>
                          <TableCell className={`text-right tabular-nums ${healthColor(teamItem.avg_health_score)}`}>
                            {formatScore(teamItem.avg_health_score)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-emerald-600 dark:text-emerald-400">
                            {teamItem.healthy_count}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-amber-600 dark:text-amber-400">
                            {teamItem.neutral_count}
                          </TableCell>
                          <TableCell className="text-right tabular-nums text-red-600 dark:text-red-400">
                            {teamItem.needs_attention_count}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatMrr(teamItem.total_mrr)}
                          </TableCell>
                        </TableRow>

                        {/* Rep rows (expanded) */}
                        {expandedTeam === teamItem.team_name &&
                          teamItem.reps.map((rep) => (
                            <Fragment key={rep.rep_id ?? rep.rep_name}>
                              <TableRow
                                className="cursor-pointer hover:bg-muted/30 bg-muted/10"
                                onClick={() => toggleRep(rep.rep_id ?? rep.rep_name)}
                              >
                                <TableCell className="w-8 pl-8">
                                  {expandedRep === (rep.rep_id ?? rep.rep_name) ? (
                                    <ChevronDown className="size-3.5 text-muted-foreground" />
                                  ) : (
                                    <ChevronRight className="size-3.5 text-muted-foreground" />
                                  )}
                                </TableCell>
                                <TableCell className="pl-6 text-sm">{rep.rep_name}</TableCell>
                                <TableCell className="text-right tabular-nums text-sm">{rep.total_deals}</TableCell>
                                <TableCell className={`text-right tabular-nums text-sm ${healthColor(rep.avg_health_score)}`}>
                                  {formatScore(rep.avg_health_score)}
                                </TableCell>
                                <TableCell className="text-right tabular-nums text-sm text-emerald-600 dark:text-emerald-400">
                                  {rep.healthy_count}
                                </TableCell>
                                <TableCell className="text-right tabular-nums text-sm text-amber-600 dark:text-amber-400">
                                  {rep.neutral_count}
                                </TableCell>
                                <TableCell className="text-right tabular-nums text-sm text-red-600 dark:text-red-400">
                                  {rep.needs_attention_count}
                                </TableCell>
                                <TableCell className="text-right tabular-nums text-sm">
                                  {formatMrr(rep.total_mrr)}
                                </TableCell>
                              </TableRow>

                              {/* Deal rows (expanded under rep) */}
                              {expandedRep === (rep.rep_id ?? rep.rep_name) &&
                                rep.deals.map((deal) => (
                                  <TableRow
                                    key={deal.account_id}
                                    className="bg-muted/5 hover:bg-muted/20"
                                  >
                                    <TableCell />
                                    <TableCell className="pl-12 text-xs">
                                      <Link
                                        href={`/deals/${deal.account_id}`}
                                        className="text-primary hover:underline"
                                      >
                                        {deal.account_name}
                                      </Link>
                                      {deal.stage_name && (
                                        <span className="ml-2 text-muted-foreground">
                                          {deal.stage_name}
                                        </span>
                                      )}
                                    </TableCell>
                                    <TableCell />
                                    <TableCell className={`text-right tabular-nums text-xs ${healthColor(deal.health_score)}`}>
                                      {deal.health_score ?? '--'}
                                    </TableCell>
                                    <TableCell colSpan={3} className="text-xs text-muted-foreground whitespace-normal">
                                      {deal.momentum_direction ?? '--'}
                                      {deal.ai_forecast_category && ` / ${deal.ai_forecast_category}`}
                                      {deal.divergence_flag && (
                                        <span className="ml-1 text-amber-600 dark:text-amber-400 font-medium">
                                          DIV
                                        </span>
                                      )}
                                    </TableCell>
                                    <TableCell className="text-right tabular-nums text-xs">
                                      {formatMrr(deal.cp_estimate)}
                                    </TableCell>
                                  </TableRow>
                                ))}
                            </Fragment>
                          ))}
                      </Fragment>
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
