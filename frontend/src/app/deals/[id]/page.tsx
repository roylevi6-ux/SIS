'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, MessageSquarePlus, AlertTriangle, Zap } from 'lucide-react';
import { useAccount } from '@/lib/hooks/use-accounts';
import { useAnalysisHistory, useAgentAnalyses, useAssessmentDelta } from '@/lib/hooks/use-analyses';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { HealthBadge } from '@/components/health-badge';
import { MomentumIndicator } from '@/components/momentum-indicator';
import { ForecastBadge } from '@/components/forecast-badge';
import { HealthBreakdown } from '@/components/health-breakdown';
import { DealMemo } from '@/components/deal-memo';
import { AgentCard } from '@/components/agent-card';
import { ActionsList } from '@/components/actions-list';
import { DealTimeline } from '@/components/deal-timeline';
import { DeltaBadge } from '@/components/delta-badge';
import type { AgentAnalysis } from '@/components/agent-card';

// ---------------------------------------------------------------------------
// Types for the account detail response
// ---------------------------------------------------------------------------

interface Transcript {
  id: string;
  call_date: string;
  duration_minutes: number | null;
  token_count: number | null;
  is_active: boolean;
  created_at: string;
}

interface Assessment {
  id: string;
  deal_memo: string | null;
  health_score: number;
  health_breakdown: Record<string, number>;
  momentum_direction: string | null;
  momentum_trend: string | null;
  ai_forecast_category: string | null;
  forecast_rationale: string | null;
  inferred_stage: number;
  stage_name: string | null;
  stage_confidence: number;
  overall_confidence: number;
  key_unknowns: string[];
  top_positive_signals: Array<string | { text?: string; [key: string]: unknown }>;
  top_risks: Array<string | { text?: string; [key: string]: unknown }>;
  recommended_actions: Array<string | { text?: string; [key: string]: unknown }>;
  contradiction_map: Array<string | { description?: string; [key: string]: unknown }>;
  divergence_flag: boolean;
  divergence_explanation: string | null;
  created_at: string;
}

interface AccountDetail {
  id: string;
  account_name: string;
  mrr_estimate: number | null;
  team_lead: string | null;
  ae_owner: string | null;
  team_name: string | null;
  ic_forecast_category: string | null;
  transcripts: Transcript[];
  assessment: Assessment | null;
}

interface AnalysisRun {
  run_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_cost_usd: number | null;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getSignalText(item: string | Record<string, unknown>): string {
  if (typeof item === 'string') return item;

  // RiskEntry: risk + severity + evidence_summary + mitigation
  if (item.risk) {
    const parts = [item.risk as string];
    if (item.severity) parts.push(`[${item.severity}]`);
    if (item.evidence_summary) parts.push(`— ${item.evidence_summary}`);
    if (item.mitigation) parts.push(`Mitigation: ${item.mitigation}`);
    return parts.join(' ');
  }

  // SignalEntry: signal + evidence_summary
  if (item.signal) {
    const parts = [item.signal as string];
    if (item.evidence_summary) parts.push(`— ${item.evidence_summary}`);
    return parts.join(' ');
  }

  // ContradictionEntry: dimension + detail + resolution
  if (item.contradiction_detail) {
    const parts: string[] = [];
    if (item.dimension) parts.push(`${item.dimension}:`);
    parts.push(item.contradiction_detail as string);
    if (item.resolution) parts.push(`Resolution: ${item.resolution}`);
    return parts.join(' ');
  }

  // Generic fallback: try common text fields, then stringify
  return (item.text || item.description || item.name || JSON.stringify(item)) as string;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDuration(minutes: number | null): string {
  if (minutes === null || minutes === undefined) return '--';
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function PageSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-4 w-32 rounded bg-muted" />
        <div className="h-8 w-64 rounded bg-muted" />
        <div className="flex gap-3">
          <div className="h-6 w-16 rounded bg-muted" />
          <div className="h-6 w-24 rounded bg-muted" />
          <div className="h-6 w-20 rounded bg-muted" />
        </div>
      </div>
      {/* Deal memo skeleton */}
      <div className="h-40 rounded-xl border bg-muted/20" />
      {/* Health breakdown skeleton */}
      <div className="h-56 rounded-xl border bg-muted/20" />
      {/* Two-column skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="h-32 rounded-xl border bg-muted/20" />
        <div className="h-32 rounded-xl border bg-muted/20" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// No assessment state
// ---------------------------------------------------------------------------

function NoAssessmentState({ accountName }: { accountName: string }) {
  return (
    <Card>
      <CardContent className="py-12 text-center">
        <p className="text-lg font-medium text-muted-foreground">
          No assessment available for {accountName}
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          Upload transcripts and run an analysis to generate an assessment.
        </p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Signals list component (for risks, positive signals, contradictions)
// ---------------------------------------------------------------------------

function SignalsList({
  title,
  items,
  icon,
  emptyText,
}: {
  title: string;
  items: Array<string | { text?: string; description?: string; [key: string]: unknown }> | null | undefined;
  icon: React.ReactNode;
  emptyText: string;
}) {
  if (!items || items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span className="mt-0.5 shrink-0">{icon}</span>
              <span>{getSignalText(item)}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Agent analyses section
// ---------------------------------------------------------------------------

function AgentAnalysesSection({ accountId }: { accountId: string }) {
  const { data: history } = useAnalysisHistory(accountId);
  const runs = (history ?? []) as AnalysisRun[];

  // Get the latest completed run
  const latestRun = runs.find((r) => r.status === 'completed') ?? runs[0];
  const runId = latestRun?.run_id ?? '';

  const { data: agents, isLoading } = useAgentAnalyses(runId);
  const agentList = (agents ?? []) as AgentAnalysis[];

  if (!latestRun) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Per-Agent Analysis</h2>
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 rounded-xl border bg-muted/20 animate-pulse" />
          ))}
        </div>
      ) : agentList.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No agent analyses found for this run.
        </p>
      ) : (
        <div className="space-y-2">
          {agentList.map((agent) => (
            <AgentCard key={agent.agent_id} analysis={agent} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Analysis history section
// ---------------------------------------------------------------------------

function AnalysisHistorySection({ accountId }: { accountId: string }) {
  const { data: history } = useAnalysisHistory(accountId);
  const runs = (history ?? []) as AnalysisRun[];

  if (runs.length === 0) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Analysis History</h2>
      <Card>
        <CardContent className="pt-4">
          <div className="space-y-2">
            {runs.slice(0, 10).map((run) => (
              <div
                key={run.run_id}
                className="flex items-center justify-between text-sm py-1"
              >
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={
                      run.status === 'completed'
                        ? 'bg-emerald-100 text-emerald-700 border-transparent dark:bg-emerald-950 dark:text-emerald-400'
                        : run.status === 'failed'
                          ? 'bg-red-100 text-red-700 border-transparent dark:bg-red-950 dark:text-red-400'
                          : 'bg-blue-100 text-blue-700 border-transparent dark:bg-blue-950 dark:text-blue-400'
                    }
                  >
                    {run.status}
                  </Badge>
                  <span className="text-muted-foreground">
                    {formatDate(run.started_at)}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  {run.run_id.slice(0, 8)}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Transcript list section
// ---------------------------------------------------------------------------

function TranscriptListSection({ transcripts }: { transcripts: Transcript[] }) {
  if (transcripts.length === 0) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Transcripts</h2>
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-muted-foreground text-center">
              No transcripts uploaded yet.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">
        Transcripts ({transcripts.length})
      </h2>
      <Card>
        <CardContent className="pt-4">
          <div className="space-y-2">
            {transcripts.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between text-sm py-1"
              >
                <div className="flex items-center gap-2">
                  <span>{formatDate(t.call_date)}</span>
                  {!t.is_active && (
                    <Badge variant="outline" className="text-xs">
                      Inactive
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-3 text-muted-foreground text-xs">
                  <span>{formatDuration(t.duration_minutes)}</span>
                  {t.token_count !== null && (
                    <span>{t.token_count.toLocaleString()} tokens</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function DealDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, isLoading, isError, error } = useAccount(id);
  const account = data as AccountDetail | undefined;
  const [_feedbackOpen, setFeedbackOpen] = useState(false);
  const { data: deltaData } = useAssessmentDelta(id);
  const deltaFields = deltaData?.fields as Record<string, { previous: unknown; current: unknown; changed: boolean; delta?: number }> | undefined;

  // Loading state
  if (isLoading) {
    return <PageSkeleton />;
  }

  // Error state
  if (isError) {
    return (
      <div className="p-6">
        <Link
          href="/pipeline"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="size-4" />
          Back to Pipeline
        </Link>
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">
              Failed to load deal details
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!account) return null;

  const assessment = account.assessment;

  return (
    <div className="p-6 space-y-6">
      {/* ---- Header ---- */}
      <div>
        <Link
          href="/pipeline"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="size-4" />
          Back to Pipeline
        </Link>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight">
              {account.account_name}
            </h1>

            {/* Status row */}
            <div className="flex flex-wrap items-center gap-3">
              {assessment ? (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm text-muted-foreground">Health:</span>
                    <HealthBadge score={assessment.health_score} />
                    <DeltaBadge field={deltaFields?.health_score} />
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className="text-sm text-muted-foreground">Momentum:</span>
                    <MomentumIndicator
                      direction={assessment.momentum_direction as 'Improving' | 'Stable' | 'Declining' | null}
                    />
                    <DeltaBadge field={deltaFields?.momentum_direction} />
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className="text-sm text-muted-foreground">Stage:</span>
                    <span className="text-sm font-medium">
                      {assessment.inferred_stage}
                      {assessment.stage_name && ` - ${assessment.stage_name}`}
                    </span>
                    <DeltaBadge field={deltaFields?.stage_name} />
                  </div>
                </>
              ) : (
                <span className="text-sm text-muted-foreground">No assessment</span>
              )}
            </div>

            {/* Forecast row */}
            {assessment && (
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-muted-foreground">AI Forecast:</span>
                  <ForecastBadge category={assessment.ai_forecast_category} />
                  <DeltaBadge field={deltaFields?.ai_forecast_category} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-muted-foreground">IC Forecast:</span>
                  <ForecastBadge category={account.ic_forecast_category} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-muted-foreground">Confidence:</span>
                  <span className="text-sm font-medium tabular-nums">
                    {Math.round(assessment.overall_confidence)}%
                  </span>
                  <DeltaBadge field={deltaFields?.overall_confidence} />
                </div>
                {assessment.divergence_flag && (
                  <Badge
                    variant="outline"
                    className="border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400"
                  >
                    <AlertTriangle className="size-3 mr-1" />
                    Divergence
                  </Badge>
                )}
              </div>
            )}

            {/* Meta info */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {account.ae_owner && <span>AE: {account.ae_owner}</span>}
              {account.team_lead && <span>TL: {account.team_lead}</span>}
              {account.team_name && <span>Team: {account.team_name}</span>}
              {account.mrr_estimate !== null && (
                <span>
                  MRR: $
                  {account.mrr_estimate >= 1000
                    ? `${(account.mrr_estimate / 1000).toFixed(1)}K`
                    : account.mrr_estimate.toLocaleString()}
                </span>
              )}
            </div>
          </div>

          {/* Feedback button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setFeedbackOpen(true)}
          >
            <MessageSquarePlus className="size-4" />
            Give Feedback
          </Button>
        </div>
      </div>

      <Separator />

      {/* ---- No assessment state ---- */}
      {!assessment && (
        <NoAssessmentState accountName={account.account_name} />
      )}

      {/* ---- Assessment content ---- */}
      {assessment && (
        <>
          {/* Deal Memo */}
          <DealMemo memo={assessment.deal_memo} />

          {/* Health Breakdown */}
          <HealthBreakdown breakdown={assessment.health_breakdown} />

          {/* Two-column: Actions + Risks */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ActionsList actions={assessment.recommended_actions} />
            <SignalsList
              title="Risk Signals"
              items={assessment.top_risks}
              icon={<AlertTriangle className="size-3.5 text-amber-500" />}
              emptyText="No risks identified."
            />
          </div>

          {/* Two-column: Positive Signals + Contradictions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SignalsList
              title="Positive Signals"
              items={assessment.top_positive_signals}
              icon={<span className="text-emerald-500">+</span>}
              emptyText="No positive signals."
            />
            <SignalsList
              title="Contradictions"
              items={assessment.contradiction_map}
              icon={<Zap className="size-3.5 text-purple-500" />}
              emptyText="No contradictions detected."
            />
          </div>

          {/* Divergence explanation */}
          {assessment.divergence_flag && assessment.divergence_explanation && (
            <Card className="border-amber-200 dark:border-amber-800">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="size-4 text-amber-500" />
                  Forecast Divergence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{assessment.divergence_explanation}</p>
              </CardContent>
            </Card>
          )}

          {/* Key unknowns */}
          {assessment.key_unknowns && assessment.key_unknowns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Key Unknowns</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc list-inside text-sm space-y-1">
                  {assessment.key_unknowns.map((unknown, i) => (
                    <li key={i}>{unknown}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Forecast rationale */}
          {assessment.forecast_rationale && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Forecast Rationale</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed">{assessment.forecast_rationale}</p>
              </CardContent>
            </Card>
          )}

          <Separator />

          {/* Per-Agent Analysis */}
          <AgentAnalysesSection accountId={id} />
        </>
      )}

      <Separator />

      {/* Assessment Timeline */}
      <DealTimeline accountId={id} />

      {/* Analysis History */}
      <AnalysisHistorySection accountId={id} />

      {/* Transcript List */}
      <TranscriptListSection transcripts={account.transcripts ?? []} />
    </div>
  );
}
