'use client';

import { useState, useMemo } from 'react';
import { usePipeline } from '@/lib/hooks/use-dashboard';
import { usePermissions } from '@/lib/permissions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DealTable } from '@/components/deal-table';
import { PipelineMovers } from '@/components/pipeline-movers';
import { TeamRollupCards } from '@/components/team-rollup-cards';
import type { PipelineOverviewResponse } from '@/lib/pipeline-types';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMrrSummary(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? `${count} ${singular}` : `${count} ${plural}`;
}

// ---------------------------------------------------------------------------
// Skeleton loading state
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="h-4 w-20 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent>
        <div className="h-8 w-16 animate-pulse rounded bg-muted mb-1" />
        <div className="h-3 w-12 animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}

function SkeletonTable() {
  return (
    <div className="space-y-3 pt-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex gap-4 px-2">
          <div className="h-4 w-40 animate-pulse rounded bg-muted" />
          <div className="h-4 w-16 animate-pulse rounded bg-muted" />
          <div className="h-4 w-12 animate-pulse rounded bg-muted" />
          <div className="h-4 w-10 animate-pulse rounded bg-muted" />
          <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          <div className="h-4 w-14 animate-pulse rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <SkeletonTable />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------

interface SummaryCardProps {
  title: string;
  count: number;
  mrr?: number;
  colorClass: string;
  accentBorder: string;
}

function SummaryCard({ title, count, mrr, colorClass, accentBorder }: SummaryCardProps) {
  return (
    <Card className={accentBorder}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${colorClass}`}>
          {count}
        </div>
        <p className="text-xs text-muted-foreground">
          {pluralize(count, 'deal', 'deals')}
          {mrr !== undefined && mrr > 0 && ` \u00B7 ${formatMrrSummary(mrr)}`}
        </p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Team filter: derive unique teams from the data
// ---------------------------------------------------------------------------

function deriveTeams(data: PipelineOverviewResponse): string[] {
  const allDeals = [
    ...data.healthy,
    ...data.at_risk,
    ...data.critical,
    ...data.unscored,
  ];
  const teams = new Set<string>();
  for (const deal of allDeals) {
    if (deal.team_name) teams.add(deal.team_name);
  }
  return Array.from(teams).sort();
}

// ---------------------------------------------------------------------------
// VP/GM Roll-up section
// ---------------------------------------------------------------------------

function RollupSection({ onTeamFilter }: { onTeamFilter: (team: string | undefined) => void }) {
  const [rollup, setRollup] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch team rollup data on mount
  useState(() => {
    api.dashboard.teamRollup()
      .then((data) => setRollup(data))
      .catch(() => setRollup(null))
      .finally(() => setLoading(false));
  });

  if (loading || !rollup || rollup.length === 0) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Team Overview</h2>
      <TeamRollupCards
        rollup={rollup}
        onTeamClick={(teamName) => onTeamFilter(teamName)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type TabValue = 'all' | 'healthy' | 'at_risk' | 'critical' | 'unscored';

export default function PipelinePage() {
  const [team, setTeam] = useState<string | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<TabValue>('all');
  const { canSeeRollup } = usePermissions();

  const { data, isLoading, isError, error } = usePipeline(team);
  const pipeline = data as PipelineOverviewResponse | undefined;

  const teams = useMemo(() => {
    if (!pipeline) return [];
    return deriveTeams(pipeline);
  }, [pipeline]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pipeline Overview</h1>
          <p className="text-sm text-muted-foreground">
            {pipeline
              ? `${pipeline.total_deals} total deals across all tiers`
              : 'Loading pipeline data...'}
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
              {teams.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* VP/GM Roll-up cards */}
      {canSeeRollup && (
        <RollupSection onTeamFilter={(t) => setTeam(t)} />
      )}

      {/* Loading state */}
      {isLoading && <LoadingSkeleton />}

      {/* Error state */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">
              Failed to load pipeline data
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Data loaded */}
      {pipeline && !isLoading && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <SummaryCard
              title="Healthy"
              count={pipeline.summary.healthy_count}
              mrr={pipeline.summary.total_mrr_healthy}
              colorClass="text-healthy"
              accentBorder="border-l-4 border-l-healthy"
            />
            <SummaryCard
              title="At Risk"
              count={pipeline.summary.at_risk_count}
              mrr={pipeline.summary.total_mrr_at_risk}
              colorClass="text-at-risk"
              accentBorder="border-l-4 border-l-at-risk"
            />
            <SummaryCard
              title="Critical"
              count={pipeline.summary.critical_count}
              mrr={pipeline.summary.total_mrr_critical}
              colorClass="text-critical"
              accentBorder="border-l-4 border-l-critical"
            />
            <SummaryCard
              title="Unscored"
              count={pipeline.summary.unscored_count}
              colorClass="text-muted-foreground"
              accentBorder="border-l-4 border-l-muted"
            />
          </div>

          {/* Pipeline movements */}
          <PipelineMovers />

          {/* Tabbed deal table */}
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as TabValue)}
          >
            <TabsList>
              <TabsTrigger value="all">
                All ({pipeline.total_deals})
              </TabsTrigger>
              <TabsTrigger value="healthy">
                Healthy ({pipeline.summary.healthy_count})
              </TabsTrigger>
              <TabsTrigger value="at_risk">
                At Risk ({pipeline.summary.at_risk_count})
              </TabsTrigger>
              <TabsTrigger value="critical">
                Critical ({pipeline.summary.critical_count})
              </TabsTrigger>
              <TabsTrigger value="unscored">
                Unscored ({pipeline.summary.unscored_count})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <DealTable deals={[...pipeline.healthy, ...pipeline.at_risk, ...pipeline.critical, ...pipeline.unscored]} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="healthy" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <DealTable deals={pipeline.healthy} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="at_risk" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <DealTable deals={pipeline.at_risk} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="critical" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <DealTable deals={pipeline.critical} />
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="unscored" className="mt-4">
              <Card>
                <CardContent className="p-0">
                  <DealTable deals={pipeline.unscored} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
