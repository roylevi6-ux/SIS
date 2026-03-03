'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface AgentAnalysis {
  id?: string;
  agent_id?: string;
  findings?: Record<string, unknown> | null;
}

const DIMENSION_MAP: Record<string, { label: string; color: string }> = {
  agent_0e_account_health: { label: 'Account Health', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' },
  agent_1_stage_progress: { label: 'Stage & Progress', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  agent_2_relationship: { label: 'Relationship', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' },
  agent_3_commercial_risk: { label: 'Commercial', color: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' },
  agent_4_momentum: { label: 'Momentum', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
  agent_5_technical: { label: 'Technical', color: 'bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300' },
  agent_6_economic_buyer: { label: 'Economic Buyer', color: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' },
  agent_7_msp_next_steps: { label: 'Next Steps', color: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300' },
  agent_8_competitive: { label: 'Competitive', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300' },
};

function getInsight(agent: AgentAnalysis): string | null {
  if (!agent.findings || typeof agent.findings !== 'object') return null;
  const insight = agent.findings.manager_insight;
  return insight ? String(insight) : null;
}

function getAgentId(agent: AgentAnalysis): string {
  return agent.agent_id ?? agent.id ?? '';
}

interface KeyFindingsProps {
  agents: AgentAnalysis[];
}

export function KeyFindings({ agents }: KeyFindingsProps) {
  const findings = agents
    .map((agent) => ({
      agentId: getAgentId(agent),
      insight: getInsight(agent),
    }))
    .filter((f): f is { agentId: string; insight: string } => !!f.insight);

  if (findings.length === 0) return null;

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Key Findings by Dimension
        </h3>
        <div className="space-y-2.5">
          {findings.map(({ agentId, insight }) => {
            const dim = DIMENSION_MAP[agentId];
            return (
              <div key={agentId} className="flex items-start gap-2.5">
                <Badge
                  variant="secondary"
                  className={`text-[10px] px-1.5 py-0.5 shrink-0 mt-0.5 ${dim?.color ?? ''}`}
                >
                  {dim?.label ?? agentId}
                </Badge>
                <p className="text-sm leading-relaxed text-foreground">{insight}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
