'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, MessageSquarePlus, AlertTriangle, Zap, ChevronRight } from 'lucide-react';
import { useAccount } from '@/lib/hooks/use-accounts';
import { useAnalysisHistory, useAgentAnalyses, useAssessmentDelta } from '@/lib/hooks/use-analyses';
import { useDealPageWidgets, type WidgetConfig } from '@/lib/hooks/use-preferences';
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
import { ManagerActionsPanel } from '@/components/manager-actions-panel';
import { DealTimeline } from '@/components/deal-timeline';
import { CallTimeline } from '@/components/call-timeline';
import { DeltaBadge } from '@/components/delta-badge';
import { WhatChangedCard } from '@/components/what-changed-card';
import { ScoreFeedbackDialog } from '@/components/score-feedback-dialog';
import type { AgentAnalysis, HealthBreakdownEntry } from '@/components/agent-card';
import { usePermissions } from '@/lib/permissions';
import { VPBrief } from '@/components/vp-brief';
import { KeyMetricsRow } from '@/components/key-metrics-row';
import { DealNarrative } from '@/components/deal-narrative';
import { KeyFindings } from '@/components/key-findings';
import { RepActionPlan } from '@/components/rep-action-plan';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types for the account detail response
// ---------------------------------------------------------------------------

interface Participant {
  name: string;
  affiliation?: string;
  title?: string;
}

interface Transcript {
  id: string;
  call_date: string;
  duration_minutes: number | null;
  token_count: number | null;
  is_active: boolean;
  created_at: string;
  participants: Participant[] | null;
  call_title: string | null;
  call_topics?: Array<{ name: string; duration: number }> | null;
  analyzed: boolean;
}

interface Assessment {
  id: string;
  deal_memo: string | null;
  health_score: number;
  health_breakdown: unknown;
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
  sf_stage_at_run: number | null;
  sf_forecast_at_run: string | null;
  sf_close_quarter_at_run: string | null;
  cp_estimate_at_run: number | null;
  stage_gap_direction: string | null;
  stage_gap_magnitude: number | null;
  forecast_gap_direction: string | null;
  sf_gap_interpretation: string | null;
  manager_brief: string | null;
  attention_level: string | null;
  deal_memo_sections: Array<{
    section_id: string;
    title: string;
    content: string;
    health_signal: string;
    related_components: string[];
  }>;
}

interface AccountDetail {
  id: string;
  account_name: string;
  cp_estimate: number | null;
  team_lead: string | null;
  ae_owner: string | null;
  team_name: string | null;
  deal_type: string;
  buying_culture: string;
  prior_contract_value: number | null;
  sf_forecast_category: string | null;
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
// Widget visibility helpers
// ---------------------------------------------------------------------------

function getVisibleWidgets(prefs: WidgetConfig[] | undefined, _vpMode: boolean): string[] {
  if (prefs) {
    return prefs
      .filter((w) => w.visible)
      .sort((a, b) => a.order - b.order)
      .map((w) => w.id);
  }

  // Fallback order (both VP and non-VP use the same consolidated layout)
  return [
    'status_strip', 'call_timeline', 'what_changed',
    'vp_brief', 'rep_action_plan', 'deal_narrative',
    'health_breakdown', 'sf_gap', 'agent_analyses',
    'deal_timeline', 'analysis_history', 'transcript_list',
  ];
}

// ---------------------------------------------------------------------------
// SF Gap Analysis card
// ---------------------------------------------------------------------------

const STAGE_NAMES: Record<number, string> = {
  1: 'Qualify', 2: 'Discover', 3: 'Scope', 4: 'Validate',
  5: 'Negotiate', 6: 'Prove', 7: 'Close',
};

function SFGapCard({ assessment }: { assessment: Assessment }) {
  if (!assessment.sf_stage_at_run && !assessment.sf_forecast_at_run) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">SF Gap Analysis</CardTitle>
        <p className="text-xs text-muted-foreground">SF indication at day of last analysis</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Stage gap row */}
        {assessment.sf_stage_at_run != null && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Stage</span>
            <div className="flex items-center gap-2">
              <span>SIS: {STAGE_NAMES[assessment.inferred_stage] ?? assessment.inferred_stage} ({assessment.inferred_stage})</span>
              <span className="text-muted-foreground">vs</span>
              <span>SF: {STAGE_NAMES[assessment.sf_stage_at_run] ?? assessment.sf_stage_at_run} ({assessment.sf_stage_at_run})</span>
              {assessment.stage_gap_direction && assessment.stage_gap_direction !== 'Aligned' && (
                <Badge variant="outline" className="text-xs">
                  {assessment.stage_gap_direction === 'SF-ahead'
                    ? `SF +${assessment.stage_gap_magnitude}`
                    : `SIS +${assessment.stage_gap_magnitude}`}
                </Badge>
              )}
              {assessment.stage_gap_direction === 'Aligned' && (
                <Badge variant="outline" className="text-xs">=</Badge>
              )}
            </div>
          </div>
        )}

        {/* Forecast gap row */}
        {assessment.sf_forecast_at_run && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Forecast</span>
            <div className="flex items-center gap-2">
              <span>AI: {assessment.ai_forecast_category}</span>
              <span className="text-muted-foreground">vs</span>
              <span>SF: {assessment.sf_forecast_at_run}</span>
              {assessment.forecast_gap_direction && assessment.forecast_gap_direction !== 'Aligned' && (
                <Badge variant="outline" className="text-xs">
                  {assessment.forecast_gap_direction === 'SF-more-optimistic' ? 'SF > AI' : 'AI > SF'}
                </Badge>
              )}
              {assessment.forecast_gap_direction === 'Aligned' && (
                <Badge variant="outline" className="text-xs">=</Badge>
              )}
            </div>
          </div>
        )}

        {/* Close Quarter */}
        {assessment.sf_close_quarter_at_run && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Close Quarter</span>
            <span>{assessment.sf_close_quarter_at_run}</span>
          </div>
        )}

        {/* CP Estimate at run */}
        {assessment.cp_estimate_at_run != null && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">CP Estimate (at run)</span>
            <span>${(assessment.cp_estimate_at_run / 1000).toFixed(0)}K</span>
          </div>
        )}

        {/* Agent 10's interpretation */}
        {assessment.sf_gap_interpretation && (
          <>
            <Separator />
            <p className="text-sm text-muted-foreground">{assessment.sf_gap_interpretation}</p>
          </>
        )}

        {/* Forecast rationale (folded in from standalone widget) */}
        {assessment.forecast_rationale && (
          <>
            <Separator />
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">Forecast Rationale</p>
              <p className="text-sm leading-relaxed">{assessment.forecast_rationale}</p>
            </div>
          </>
        )}

        {/* Divergence explanation (folded in from standalone widget) */}
        {assessment.divergence_flag && assessment.divergence_explanation && (
          <>
            <Separator />
            <div className="rounded-md border border-amber-300 bg-neutral-bg p-3">
              <p className="text-xs font-semibold uppercase text-neutral mb-1 flex items-center gap-1">
                <AlertTriangle className="size-3" />
                Forecast Divergence
              </p>
              <p className="text-sm text-neutral">{assessment.divergence_explanation}</p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Collapsible widget wrapper — default-collapsed sections
// ---------------------------------------------------------------------------

function CollapsibleWidget({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="w-full text-left">
        <div className="flex items-center gap-2 py-2 hover:opacity-80 transition-opacity">
          <ChevronRight
            className={cn(
              'size-4 text-muted-foreground transition-transform',
              open && 'rotate-90',
            )}
          />
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>{children}</CollapsibleContent>
    </Collapsible>
  );
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

function AgentAnalysesSection({ agents, healthBreakdown }: { agents: AgentAnalysis[]; healthBreakdown?: unknown }) {
  if (agents.length === 0) return null;

  return (
    <div className="space-y-2">
      {agents.map((agent) => (
        <AgentCard key={agent.agent_id} analysis={agent} healthBreakdown={healthBreakdown as HealthBreakdownEntry[] | null} />
      ))}
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
                        ? 'bg-brand-500/10 text-brand-400 border-transparent'
                        : run.status === 'failed'
                          ? 'bg-needs-attention-bg text-needs-attention border-transparent'
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
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const { data: deltaData } = useAssessmentDelta(id);
  const deltaFields = deltaData?.fields as Record<string, { previous: unknown; current: unknown; changed: boolean; delta?: number }> | undefined;

  // Fetch agent analyses for Manager Actions panel + AgentAnalysesSection
  const { data: historyData } = useAnalysisHistory(id);
  const historyRuns = (historyData ?? []) as AnalysisRun[];
  const latestCompletedRun = historyRuns.find((r) => r.status === 'completed') ?? historyRuns[0];
  const { data: agentData } = useAgentAnalyses(latestCompletedRun?.run_id ?? '');
  const agentList = (agentData ?? []) as AgentAnalysis[];

  // Widget preferences
  const { data: widgetPrefs } = useDealPageWidgets();
  const { isVpOrAbove } = usePermissions();

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

  function renderWidget(widgetId: string) {
    if (!account) return null;
    switch (widgetId) {
      case 'status_strip':
        return null; // Status strip is rendered in the header, not dynamically
      case 'call_timeline':
        return account.transcripts?.length > 0 ? (
          <CallTimeline key={widgetId} transcripts={account.transcripts} />
        ) : null;
      case 'what_changed':
        return (
          <CollapsibleWidget key={widgetId} title="What Changed">
            <WhatChangedCard accountId={id} />
          </CollapsibleWidget>
        );
      case 'deal_memo':
        return assessment ? <DealMemo key={widgetId} memo={assessment.deal_memo} /> : null;
      case 'manager_actions':
        return assessment ? <ManagerActionsPanel key={widgetId} agents={agentList} /> : null;
      case 'health_breakdown':
        return assessment ? (
          <HealthBreakdown key={widgetId} breakdown={assessment.health_breakdown} healthScore={assessment.health_score} />
        ) : null;
      case 'actions_risks':
        return assessment ? (
          <div key={widgetId} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ActionsList actions={assessment.recommended_actions} />
            <SignalsList
              title="Risk Signals"
              items={assessment.top_risks}
              icon={<AlertTriangle className="size-3.5 text-amber-500" />}
              emptyText="No risks identified."
            />
          </div>
        ) : null;
      case 'positive_contradictions':
        return assessment ? (
          <div key={widgetId} className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
        ) : null;
      case 'forecast_divergence':
        return assessment?.divergence_flag && assessment.divergence_explanation ? (
          <Card key={widgetId} className="border-amber-200/50">
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
        ) : null;
      case 'key_unknowns':
        return (assessment?.key_unknowns?.length ?? 0) > 0 ? (
          <Card key={widgetId}>
            <CardHeader>
              <CardTitle className="text-base">Key Unknowns</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc list-inside text-sm space-y-1">
                {assessment?.key_unknowns?.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null;
      case 'forecast_rationale':
        return assessment?.forecast_rationale ? (
          <Card key={widgetId}>
            <CardHeader>
              <CardTitle className="text-base">Forecast Rationale</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{assessment.forecast_rationale}</p>
            </CardContent>
          </Card>
        ) : null;
      case 'sf_gap':
        return assessment ? (
          <CollapsibleWidget key={widgetId} title="SF Gap Analysis">
            <SFGapCard assessment={assessment} />
          </CollapsibleWidget>
        ) : null;
      case 'agent_analyses':
        return assessment ? (
          <CollapsibleWidget key={widgetId} title="Per-Agent Analysis">
            <AgentAnalysesSection agents={agentList} healthBreakdown={assessment.health_breakdown} />
          </CollapsibleWidget>
        ) : null;
      case 'deal_timeline':
        return <DealTimeline key={widgetId} accountId={id} />;
      case 'analysis_history':
        return <AnalysisHistorySection key={widgetId} accountId={id} />;
      case 'transcript_list':
        return <TranscriptListSection key={widgetId} transcripts={account.transcripts ?? []} />;
      case 'vp_brief':
        return assessment ? (
          <VPBrief
            key={widgetId}
            brief={assessment.manager_brief}
            attentionLevel={assessment.attention_level}
            fallbackMemo={assessment.deal_memo}
          />
        ) : null;
      case 'key_metrics':
        return assessment ? (
          <KeyMetricsRow
            key={widgetId}
            topRisk={assessment.top_risks?.[0] ?? null}
            topAction={assessment.recommended_actions?.[0] ?? null}
            keyUnknown={assessment.key_unknowns?.[0] ?? null}
          />
        ) : null;
      case 'deal_narrative':
        return assessment ? (
          <CollapsibleWidget key={widgetId} title="Deal Narrative">
            <DealNarrative
              memo={assessment.deal_memo}
              sections={assessment.deal_memo_sections ?? []}
            />
          </CollapsibleWidget>
        ) : null;
      case 'key_findings':
        return assessment ? (
          <KeyFindings key={widgetId} agents={agentList} />
        ) : null;
      case 'rep_action_plan':
        return assessment ? (
          <RepActionPlan key={widgetId} actions={assessment.recommended_actions ?? []} />
        ) : null;
      default:
        return null;
    }
  }

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
            <h1 className="text-xl font-semibold tracking-tight">
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
                  <span className="text-sm text-muted-foreground">SF Forecast:</span>
                  <ForecastBadge category={account.sf_forecast_category} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-muted-foreground">Confidence:</span>
                  <span className="text-sm font-medium tabular-nums">
                    {Math.round(assessment.overall_confidence <= 1.0 ? assessment.overall_confidence * 100 : assessment.overall_confidence)}%
                  </span>
                  <DeltaBadge field={deltaFields?.overall_confidence} />
                </div>
                {assessment.divergence_flag && (
                  <Badge
                    variant="outline"
                    className="border-amber-300 bg-neutral-bg text-neutral"
                  >
                    <AlertTriangle className="size-3 mr-1" />
                    Divergence
                  </Badge>
                )}
              </div>
            )}

            {/* Meta info */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {account.deal_type && account.deal_type !== 'new_logo' && (
                <Badge variant="outline" className="text-xs border-blue-300 bg-blue-500/10 text-blue-400">
                  {account.deal_type.replace('expansion_', 'Expansion: ').replace('_', ' ')}
                </Badge>
              )}
              {account.buying_culture === 'proxy_delegated' && (
                <Badge variant="outline" className="text-xs border-amber-300 bg-neutral-bg text-neutral">
                  Proxy-Delegated
                </Badge>
              )}
              {account.ae_owner && <span>AE: {account.ae_owner}</span>}
              {account.team_lead && <span>TL: {account.team_lead}</span>}
              {account.team_name && <span>Team: {account.team_name}</span>}
              {account.cp_estimate !== null && (
                <span>
                  CP Est.: $
                  {account.cp_estimate >= 1000
                    ? `${(account.cp_estimate / 1000).toFixed(1)}K`
                    : account.cp_estimate.toLocaleString()}
                </span>
              )}
              {account.prior_contract_value != null && (
                <span>
                  Prior: $
                  {account.prior_contract_value >= 1000
                    ? `${(account.prior_contract_value / 1000).toFixed(1)}K`
                    : account.prior_contract_value.toLocaleString()}
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

          {/* Feedback dialog */}
          <ScoreFeedbackDialog
            open={feedbackOpen}
            onOpenChange={setFeedbackOpen}
            accountId={id}
            assessmentId={assessment?.id ?? ''}
            currentHealthScore={assessment?.health_score ?? 0}
          />
        </div>
      </div>

      <Separator />

      {/* ---- Dynamic widget layout ---- */}
      {!assessment && <NoAssessmentState accountName={account.account_name} />}
      {getVisibleWidgets(widgetPrefs, isVpOrAbove).map((widgetId) => renderWidget(widgetId))}
    </div>
  );
}
