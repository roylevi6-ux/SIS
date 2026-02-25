'use client';

import { useState, useMemo } from 'react';
import { useAccounts, useAccount } from '@/lib/hooks/use-accounts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { HealthBadge } from '@/components/health-badge';
import { MomentumIndicator } from '@/components/momentum-indicator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertTriangle,
  Zap,
  ListChecks,
  HelpCircle,
  TrendingUp,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AccountSummary {
  id: string;
  account_name: string;
}

interface Assessment {
  health_score: number;
  momentum_direction: string | null;
  ai_forecast_category: string | null;
  inferred_stage: number;
  stage_name: string | null;
  recommended_actions: Array<string | { text?: string; [key: string]: unknown }>;
  top_risks: Array<string | { text?: string; [key: string]: unknown }>;
  key_unknowns: string[];
  top_positive_signals: Array<string | { text?: string; [key: string]: unknown }>;
}

interface AccountDetail {
  id: string;
  account_name: string;
  ae_owner: string | null;
  team_name: string | null;
  cp_estimate: number | null;
  ic_forecast_category: string | null;
  assessment: Assessment | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getItemText(item: string | Record<string, unknown>): string {
  if (typeof item === 'string') return item;

  // RiskEntry
  if (item.risk) {
    const parts = [item.risk as string];
    if (item.severity) parts.push(`[${item.severity}]`);
    if (item.evidence_summary) parts.push(`— ${item.evidence_summary}`);
    if (item.mitigation) parts.push(`Mitigation: ${item.mitigation}`);
    return parts.join(' ');
  }

  // SignalEntry
  if (item.signal) {
    const parts = [item.signal as string];
    if (item.evidence_summary) parts.push(`— ${item.evidence_summary}`);
    return parts.join(' ');
  }

  // RecommendedAction
  if (item.action) {
    const parts = [item.action as string];
    if (item.owner) parts.push(`(${item.owner})`);
    if (item.priority) parts.push(`[${item.priority}]`);
    return parts.join(' ');
  }

  // ContradictionEntry
  if (item.contradiction_detail) {
    const parts: string[] = [];
    if (item.dimension) parts.push(`${item.dimension}:`);
    parts.push(item.contradiction_detail as string);
    if (item.resolution) parts.push(`Resolution: ${item.resolution}`);
    return parts.join(' ');
  }

  return (item.text || item.description || item.name || JSON.stringify(item)) as string;
}

function derivedQuestions(unknowns: string[]): string[] {
  return unknowns.map((u) => {
    const clean = u.replace(/^(what|whether|if|how|who|when|why)\s+/i, '');
    return `What is the status of: ${clean}?`;
  });
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function PrepSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-24 rounded-xl border bg-muted/20" />
      <div className="h-32 rounded-xl border bg-muted/20" />
      <div className="h-32 rounded-xl border bg-muted/20" />
      <div className="h-32 rounded-xl border bg-muted/20" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section card
// ---------------------------------------------------------------------------

function PrepSection({
  title,
  icon,
  items,
  emptyText,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  emptyText: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{emptyText}</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Account overview card
// ---------------------------------------------------------------------------

function AccountOverview({ account }: { account: AccountDetail }) {
  const a = account.assessment;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Account Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            {a ? (
              <>
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Health:</span>
                  <HealthBadge score={a.health_score} />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Momentum:</span>
                  <MomentumIndicator
                    direction={
                      a.momentum_direction as 'Improving' | 'Stable' | 'Declining' | null
                    }
                  />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Stage:</span>
                  <span className="font-medium">
                    {a.inferred_stage}
                    {a.stage_name ? ` — ${a.stage_name}` : ''}
                  </span>
                </div>
                {a.ai_forecast_category && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-muted-foreground">Forecast:</span>
                    <Badge variant="outline" className="text-xs">
                      {a.ai_forecast_category}
                    </Badge>
                  </div>
                )}
              </>
            ) : (
              <span className="text-muted-foreground">No assessment available</span>
            )}
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {account.ae_owner && <span>AE: {account.ae_owner}</span>}
            {account.team_name && <span>Team: {account.team_name}</span>}
            {account.cp_estimate !== null && (
              <span>
                CP Est.: $
                {account.cp_estimate >= 1000
                  ? `${(account.cp_estimate / 1000).toFixed(1)}K`
                  : account.cp_estimate.toLocaleString()}
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Brief card when no assessment
// ---------------------------------------------------------------------------

function NoAssessmentCard() {
  return (
    <Card>
      <CardContent className="py-10 text-center">
        <p className="text-muted-foreground">No assessment available for this account.</p>
        <p className="text-sm text-muted-foreground mt-1">
          Upload transcripts and run an analysis to generate meeting prep content.
        </p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function MeetingPrepPage() {
  const [selectedId, setSelectedId] = useState<string>('');

  const { data: rawAccounts, isLoading: accountsLoading } = useAccounts();
  const accounts = useMemo<AccountSummary[]>(() => {
    if (!rawAccounts) return [];
    return rawAccounts as AccountSummary[];
  }, [rawAccounts]);

  const { data: rawDetail, isLoading: detailLoading } = useAccount(selectedId);
  const detail = rawDetail as AccountDetail | undefined;

  const assessment = detail?.assessment ?? null;

  const actionTexts = useMemo(
    () => (assessment?.recommended_actions ?? []).map(getItemText),
    [assessment],
  );
  const riskTexts = useMemo(
    () => (assessment?.top_risks ?? []).map(getItemText),
    [assessment],
  );
  const questions = useMemo(
    () => derivedQuestions(assessment?.key_unknowns ?? []),
    [assessment],
  );
  const signalTexts = useMemo(
    () => (assessment?.top_positive_signals ?? []).map(getItemText),
    [assessment],
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Meeting Prep</h1>
        <p className="text-sm text-muted-foreground">Pre-call brief for your next conversation</p>
      </div>

      {/* Account selector */}
      <div className="max-w-sm">
        <Select
          value={selectedId || 'none'}
          onValueChange={(v) => setSelectedId(v === 'none' ? '' : v)}
          disabled={accountsLoading}
        >
          <SelectTrigger className="min-h-[44px]">
            <SelectValue placeholder={accountsLoading ? 'Loading accounts...' : 'Select an account...'} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Select an account...</SelectItem>
            {accounts.map((acc) => (
              <SelectItem key={acc.id} value={acc.id}>
                {acc.account_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* No account selected */}
      {!selectedId && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Select an account above to generate a pre-call brief.</p>
          </CardContent>
        </Card>
      )}

      {/* Loading detail */}
      {selectedId && detailLoading && <PrepSkeleton />}

      {/* Account detail */}
      {selectedId && !detailLoading && detail && (
        <div className="space-y-4">
          <AccountOverview account={detail} />

          {!assessment ? (
            <NoAssessmentCard />
          ) : (
            <>
              <PrepSection
                title="Key Topics to Discuss"
                icon={<ListChecks className="size-4 text-blue-500" />}
                items={actionTexts}
                emptyText="No recommended topics identified."
              />

              <PrepSection
                title="Risks to Be Aware Of"
                icon={<AlertTriangle className="size-4 text-amber-500" />}
                items={riskTexts}
                emptyText="No risks identified in the latest assessment."
              />

              <PrepSection
                title="Questions to Ask"
                icon={<HelpCircle className="size-4 text-purple-500" />}
                items={questions}
                emptyText="No key unknowns to probe for."
              />

              <PrepSection
                title="Recent Positive Signals"
                icon={<TrendingUp className="size-4 text-emerald-500" />}
                items={signalTexts}
                emptyText="No positive signals in the latest assessment."
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}
