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

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="py-0 overflow-hidden">
        <CollapsibleTrigger className="w-full text-left">
          <div className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors">
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
          <CardContent className="pt-0 pb-4">
            <ul className="space-y-3">
              {insights.map((item) => (
                <li key={item.agentId} className="flex items-start gap-2 text-sm">
                  <Badge variant="outline" className="shrink-0 mt-0.5 text-xs">
                    {item.agentLabel}
                  </Badge>
                  <span className="leading-relaxed">{item.insight}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
