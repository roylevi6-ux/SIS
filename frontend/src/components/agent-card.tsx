'use client';

import { useState } from 'react';
import { ChevronRight, AlertTriangle } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { EvidenceViewer } from '@/components/evidence-viewer';

// Agent analysis shape from the API (loosely typed since the API returns unknown)
export interface AgentAnalysis {
  id: string;
  agent_name: string;
  agent_id?: string;
  confidence_overall?: number | null;
  sparse_data_flag?: boolean;
  narrative?: string | null;
  findings?: Record<string, unknown> | null;
  evidence?: Array<{ quote?: string; source?: string; [key: string]: unknown }> | null;
  data_gaps?: string[] | null;
  findings_summary?: string | null;
  [key: string]: unknown;
}

export interface HealthBreakdownEntry {
  component: string;
  score: number;
  max_score: number;
  rationale?: string;
}

interface AgentCardProps {
  analysis: AgentAnalysis;
  healthBreakdown?: HealthBreakdownEntry[] | null;
}

// Map agent_id → health component name (primary component per agent)
const AGENT_TO_COMPONENT: Record<string, string> = {
  agent_0e_account_health: 'account_health',
  agent_1_stage_progress: 'stage_appropriateness',
  agent_2_relationship: 'stakeholder_completeness',
  agent_3_commercial_risk: 'commercial_clarity',
  agent_4_momentum: 'momentum_quality',
  agent_5_technical: 'technical_path_clarity',
  agent_6_economic_buyer: 'economic_buyer_engagement',
  agent_7_msp_next_steps: 'commitment_quality',
  agent_8_competitive: 'competitive_position',
};

function findBreakdownEntry(
  agentId: string | undefined,
  breakdown: HealthBreakdownEntry[],
): HealthBreakdownEntry | null {
  if (!breakdown.length || !agentId) return null;
  const componentName = AGENT_TO_COMPONENT[agentId];
  if (!componentName) return null;
  const norm = (s: string) => s.toLowerCase().replace(/[\s-]+/g, '_');
  return breakdown.find((e) => norm(e.component) === componentName) ?? null;
}

function getScoreColor(score: number, maxScore: number): string {
  const pct = maxScore > 0 ? (score / maxScore) * 100 : score;
  if (pct >= 70) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400';
  if (pct >= 45) return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400';
  return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400';
}

/** Normalize confidence from 0.0-1.0 scale to 0-100 percentage. */
function toPercent(value: number | null | undefined): number | null {
  if (value == null) return null;
  // Backend stores as 0.0-1.0; convert to 0-100
  return value <= 1.0 ? Math.round(value * 100) : Math.round(value);
}

function getConfidenceColor(confidence: number | null | undefined): string {
  const pct = toPercent(confidence);
  if (pct == null) return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
  if (pct >= 70) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400';
  if (pct >= 45) return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400';
  return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400';
}

export function AgentCard({ analysis, healthBreakdown }: AgentCardProps) {
  const [open, setOpen] = useState(false);

  const pct = toPercent(analysis.confidence_overall);
  const confidenceLabel = pct != null ? `${pct}%` : 'N/A';
  const matchedComponent = findBreakdownEntry(
    analysis.agent_id,
    Array.isArray(healthBreakdown) ? healthBreakdown : [],
  );

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="py-0 overflow-hidden">
        <CollapsibleTrigger className="w-full text-left">
          <div className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors">
            <div className="flex items-center gap-3">
              <ChevronRight
                className={cn(
                  'size-4 text-muted-foreground transition-transform',
                  open && 'rotate-90',
                )}
              />
              <span className="font-medium text-sm">{analysis.agent_name}</span>
              {analysis.sparse_data_flag && (
                <AlertTriangle className="size-3.5 text-amber-500" />
              )}
            </div>
            <div className="flex items-center gap-2">
              {matchedComponent && (
                <Badge
                  variant="outline"
                  className={cn(
                    'border-transparent text-xs tabular-nums',
                    getScoreColor(matchedComponent.score, matchedComponent.max_score),
                  )}
                  title={`Health: ${matchedComponent.component}`}
                >
                  {matchedComponent.score}/{matchedComponent.max_score}
                </Badge>
              )}
              <Badge
                variant="outline"
                className={cn(
                  'border-transparent text-xs',
                  getConfidenceColor(analysis.confidence_overall),
                )}
              >
                {confidenceLabel}
              </Badge>
            </div>
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="pt-0 pb-4 space-y-4">
            {/* Narrative */}
            {analysis.narrative && (
              <div>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Narrative
                </h4>
                <p className="text-sm leading-relaxed">{analysis.narrative}</p>
              </div>
            )}

            {/* Findings summary (string) or structured findings (dict) */}
            {analysis.findings_summary ? (
              <div>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Findings
                </h4>
                <p className="text-sm leading-relaxed">{analysis.findings_summary}</p>
              </div>
            ) : analysis.findings && typeof analysis.findings === 'object' && Object.keys(analysis.findings).length > 0 ? (
              <div>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Key Findings
                </h4>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-sm">
                  {Object.entries(analysis.findings as Record<string, unknown>).map(([key, value]) => {
                    if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) return null;
                    const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                    const display = typeof value === 'object' ? JSON.stringify(value) : String(value);
                    return (
                      <div key={key} className="contents">
                        <dt className="text-muted-foreground text-xs font-medium whitespace-nowrap">{label}</dt>
                        <dd className="text-sm">{display}</dd>
                      </div>
                    );
                  })}
                </dl>
              </div>
            ) : null}

            {/* Evidence */}
            {analysis.evidence && analysis.evidence.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Evidence
                </h4>
                <EvidenceViewer evidence={analysis.evidence} />
              </div>
            )}

            {/* Data gaps */}
            {analysis.data_gaps && analysis.data_gaps.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Data Gaps
                </h4>
                <ul className="list-disc list-inside text-sm text-muted-foreground space-y-0.5">
                  {analysis.data_gaps.map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
