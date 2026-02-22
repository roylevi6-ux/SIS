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
  evidence?: Array<{ quote?: string; source?: string; [key: string]: unknown }> | null;
  data_gaps?: string[] | null;
  findings_summary?: string | null;
  [key: string]: unknown;
}

interface AgentCardProps {
  analysis: AgentAnalysis;
}

function getConfidenceColor(confidence: number | null | undefined): string {
  if (confidence == null) return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
  if (confidence >= 70) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400';
  if (confidence >= 45) return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400';
  return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400';
}

export function AgentCard({ analysis }: AgentCardProps) {
  const [open, setOpen] = useState(false);

  const confidenceLabel =
    analysis.confidence_overall != null
      ? `${Math.round(analysis.confidence_overall)}%`
      : 'N/A';

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

            {/* Findings summary */}
            {analysis.findings_summary && (
              <div>
                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Findings
                </h4>
                <p className="text-sm leading-relaxed">{analysis.findings_summary}</p>
              </div>
            )}

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
