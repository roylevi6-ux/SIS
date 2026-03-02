'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  const insights = agents
    .filter((a) => a.findings && typeof a.findings === 'object' && (a.findings as Record<string, unknown>).manager_insight)
    .map((a) => ({
      agentId: a.agent_id ?? a.id,
      agentLabel: AGENT_LABELS[a.agent_id ?? ''] ?? a.agent_name,
      insight: String((a.findings as Record<string, unknown>).manager_insight),
    }));

  if (insights.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Manager Actions This Week</CardTitle>
      </CardHeader>
      <CardContent>
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
    </Card>
  );
}
