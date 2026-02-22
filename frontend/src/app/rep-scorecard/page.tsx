'use client';

import { useState, useMemo } from 'react';
import { useRepScorecard } from '@/lib/hooks/use-admin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { ChevronDown, ChevronRight } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Dimensions = {
  'Stakeholder Engagement': number | null;
  'Objection Handling': number | null;
  'Commercial Progression': number | null;
  'Next-Step Setting': number | null;
};

interface ScorecardAccount {
  account_id: string;
  account_name: string;
  scored: boolean;
  health_score: number | null;
  dimensions: Dimensions;
}

interface RepScorecard {
  rep_name: string;
  total_accounts: number;
  scored_accounts: number;
  dimensions: Dimensions;
  overall_score: number | null;
  accounts: ScorecardAccount[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DIMENSION_KEYS = [
  'Stakeholder Engagement',
  'Objection Handling',
  'Commercial Progression',
  'Next-Step Setting',
] as const;

function scoreColor(score: number | null): string {
  if (score === null) return 'text-muted-foreground';
  if (score >= 70) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 50) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

function formatScore(score: number | null): string {
  if (score === null) return '--';
  return Math.round(score).toString();
}

function buildRadarData(reps: RepScorecard[]) {
  return DIMENSION_KEYS.map((key) => {
    const entry: Record<string, string | number> = { dimension: key };
    reps.forEach((rep) => {
      entry[rep.rep_name] = rep.dimensions[key] ?? 0;
    });
    return entry;
  });
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function PageSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 rounded bg-muted" />
      <div className="h-64 rounded-xl border bg-muted/20" />
      <div className="h-48 rounded-xl border bg-muted/20" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rep accounts sub-table
// ---------------------------------------------------------------------------

function RepAccountsTable({ accounts }: { accounts: ScorecardAccount[] }) {
  if (accounts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground px-4 py-3">
        No accounts for this rep.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto border-t">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-8">Account</TableHead>
            <TableHead>Scored</TableHead>
            <TableHead className="text-right">Health</TableHead>
            <TableHead className="text-right">Stakeholder</TableHead>
            <TableHead className="text-right">Objection</TableHead>
            <TableHead className="text-right">Commercial</TableHead>
            <TableHead className="text-right">Next-Step</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {accounts.map((acc) => (
            <TableRow key={acc.account_id} className="bg-muted/20">
              <TableCell className="pl-8 font-medium">{acc.account_name}</TableCell>
              <TableCell>
                {acc.scored ? (
                  <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800">
                    Yes
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs">No</Badge>
                )}
              </TableCell>
              <TableCell className={`text-right tabular-nums ${scoreColor(acc.health_score)}`}>
                {formatScore(acc.health_score)}
              </TableCell>
              <TableCell className={`text-right tabular-nums ${scoreColor(acc.dimensions['Stakeholder Engagement'])}`}>
                {formatScore(acc.dimensions['Stakeholder Engagement'])}
              </TableCell>
              <TableCell className={`text-right tabular-nums ${scoreColor(acc.dimensions['Objection Handling'])}`}>
                {formatScore(acc.dimensions['Objection Handling'])}
              </TableCell>
              <TableCell className={`text-right tabular-nums ${scoreColor(acc.dimensions['Commercial Progression'])}`}>
                {formatScore(acc.dimensions['Commercial Progression'])}
              </TableCell>
              <TableCell className={`text-right tabular-nums ${scoreColor(acc.dimensions['Next-Step Setting'])}`}>
                {formatScore(acc.dimensions['Next-Step Setting'])}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const RADAR_COLORS = [
  '#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
];

export default function RepScorecardPage() {
  const [aeFilter, setAeFilter] = useState('');
  const [expandedRep, setExpandedRep] = useState<string | null>(null);

  // Pass aeFilter as the aeOwner param when non-empty
  const { data: rawData, isLoading, isError, error } = useRepScorecard(
    aeFilter.trim() || undefined,
  );

  const reps = useMemo<RepScorecard[]>(() => {
    if (!rawData) return [];
    return rawData as RepScorecard[];
  }, [rawData]);

  const radarData = useMemo(() => buildRadarData(reps), [reps]);

  if (isLoading) return <PageSkeleton />;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Rep Scorecard</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading ? 'Loading...' : `${reps.length} rep${reps.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <Input
          placeholder="Filter by AE owner..."
          value={aeFilter}
          onChange={(e) => setAeFilter(e.target.value)}
          className="w-full sm:w-[220px]"
        />
      </div>

      {/* Error state */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load scorecard data</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Radar Chart */}
      {!isError && reps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dimension Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData} margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
                <PolarGrid />
                <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                {reps.map((rep, i) => (
                  <Radar
                    key={rep.rep_name}
                    name={rep.rep_name}
                    dataKey={rep.rep_name}
                    stroke={RADAR_COLORS[i % RADAR_COLORS.length]}
                    fill={RADAR_COLORS[i % RADAR_COLORS.length]}
                    fillOpacity={0.15}
                    isAnimationActive={false}
                  />
                ))}
                <Tooltip
                  contentStyle={{ fontSize: '12px', borderRadius: '6px' }}
                  formatter={(value: number | undefined) =>
                    value !== undefined ? [Math.round(value), ''] : ['--', '']
                  }
                />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* No data state */}
      {!isError && !isLoading && reps.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No scorecard data available.</p>
            <p className="text-sm text-muted-foreground mt-1">
              Analyses must be run before rep scorecards are computed.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Rep table with expandable rows */}
      {!isError && reps.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rep Performance</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8" />
                    <TableHead>Rep Name</TableHead>
                    <TableHead className="text-right">Overall</TableHead>
                    <TableHead className="text-right">Stakeholder</TableHead>
                    <TableHead className="text-right">Objection</TableHead>
                    <TableHead className="text-right">Commercial</TableHead>
                    <TableHead className="text-right">Next-Step</TableHead>
                    <TableHead className="text-right">Accounts</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reps.map((rep) => (
                    <>
                      <TableRow
                        key={rep.rep_name}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() =>
                          setExpandedRep(
                            expandedRep === rep.rep_name ? null : rep.rep_name,
                          )
                        }
                      >
                        <TableCell className="w-8 pl-4">
                          {expandedRep === rep.rep_name ? (
                            <ChevronDown className="size-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="size-4 text-muted-foreground" />
                          )}
                        </TableCell>
                        <TableCell className="font-medium">{rep.rep_name}</TableCell>
                        <TableCell className={`text-right tabular-nums font-semibold ${scoreColor(rep.overall_score)}`}>
                          {formatScore(rep.overall_score)}
                        </TableCell>
                        <TableCell className={`text-right tabular-nums ${scoreColor(rep.dimensions['Stakeholder Engagement'])}`}>
                          {formatScore(rep.dimensions['Stakeholder Engagement'])}
                        </TableCell>
                        <TableCell className={`text-right tabular-nums ${scoreColor(rep.dimensions['Objection Handling'])}`}>
                          {formatScore(rep.dimensions['Objection Handling'])}
                        </TableCell>
                        <TableCell className={`text-right tabular-nums ${scoreColor(rep.dimensions['Commercial Progression'])}`}>
                          {formatScore(rep.dimensions['Commercial Progression'])}
                        </TableCell>
                        <TableCell className={`text-right tabular-nums ${scoreColor(rep.dimensions['Next-Step Setting'])}`}>
                          {formatScore(rep.dimensions['Next-Step Setting'])}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {rep.scored_accounts}/{rep.total_accounts}
                        </TableCell>
                      </TableRow>

                      {expandedRep === rep.rep_name && (
                        <TableRow key={`${rep.rep_name}-expanded`}>
                          <TableCell colSpan={8} className="p-0">
                            <RepAccountsTable accounts={rep.accounts} />
                          </TableCell>
                        </TableRow>
                      )}
                    </>
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
