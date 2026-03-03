'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { AgentAnalysis } from '@/components/agent-card';

// Friendly display names for agent IDs
const AGENT_LABELS: Record<string, string> = {
  agent_0e_account_health: 'Account Health',
  agent_1_stage_progress: 'Stage & Progress',
  agent_2_relationship: 'Relationship',
  agent_3_commercial_risk: 'Commercial',
  agent_4_momentum: 'Momentum',
  agent_5_technical: 'Technical',
  agent_6_economic_buyer: 'Economic Buyer',
  agent_7_msp_next_steps: 'Next Steps',
  agent_8_competitive: 'Competitive',
};

interface ManagerActionsPanelProps {
  agents: AgentAnalysis[];
}

function buildSummary(labels: string[]): string {
  const count = labels.length;
  const areas = labels.slice(0, 3).join(', ');
  const more = count > 3 ? ` and ${count - 3} more` : '';
  return `${count} agent${count === 1 ? '' : 's'} flagged action items this week. Key areas: ${areas}${more}.`;
}

export function ManagerActionsPanel({ agents }: ManagerActionsPanelProps) {
  const [open, setOpen] = useState(true);

  const insights = agents
    .filter((a) => a.findings && typeof a.findings === 'object' && (a.findings as Record<string, unknown>).manager_insight)
    .map((a) => ({
      agentId: a.agent_id ?? a.id,
      agentLabel: AGENT_LABELS[a.agent_id ?? ''] ?? a.agent_name,
      insight: String((a.findings as Record<string, unknown>).manager_insight),
    }));

  if (insights.length === 0) return null;

  const summary = buildSummary(insights.map((i) => i.agentLabel));

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="py-0 overflow-hidden">
        <CollapsibleTrigger className="w-full text-left">
          <div className="flex items-center justify-between px-4 py-3 hover:bg-brand-500/8 transition-colors">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={`h-4 w-4 shrink-0 transition-transform duration-200 ${open ? 'rotate-90' : ''}`}
              />
              <span className="text-base font-semibold">Manager Actions This Week</span>
            </div>
            <Badge variant="secondary" className="text-xs">
              {insights.length} {insights.length === 1 ? 'action' : 'actions'}
            </Badge>
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="pt-0 pb-4 space-y-3">
            {/* Summary — always visible when section is open */}
            <p className="text-sm text-muted-foreground leading-relaxed px-1">
              {summary}
            </p>

            {/* Individual collapsible categories */}
            <div className="space-y-1">
              {insights.map((item) => (
                <CategoryRow
                  key={item.agentId}
                  label={item.agentLabel}
                  insight={item.insight}
                />
              ))}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

function CategoryRow({ label, insight }: { label: string; insight: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="w-full text-left">
        <div className="flex items-center gap-2 px-1 py-1.5 rounded-md hover:bg-brand-500/8 transition-colors">
          <ChevronRight
            className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-200 ${open ? 'rotate-90' : ''}`}
          />
          <Badge variant="outline" className="text-xs">
            {label}
          </Badge>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <p className="text-sm leading-relaxed pl-7 pr-2 pb-2 text-muted-foreground">
          {insight}
        </p>
      </CollapsibleContent>
    </Collapsible>
  );
}
