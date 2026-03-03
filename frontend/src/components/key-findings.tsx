'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface AgentAnalysis {
  id?: string;
  agent_id?: string;
  agent_name?: string;
  findings?: Record<string, unknown> | null;
}

const AGENT_COLORS: Record<string, string> = {
  agent_0e: 'bg-emerald-500/15 text-emerald-400',
  agent_1: 'bg-blue-500/15 text-blue-400',
  agent_2: 'bg-purple-500/15 text-purple-400',
  agent_3: 'bg-green-500/15 text-green-400',
  agent_4: 'bg-amber-500/15 text-amber-400',
  agent_5: 'bg-slate-500/15 text-slate-400',
  agent_6: 'bg-red-500/15 text-red-400',
  agent_7: 'bg-cyan-500/15 text-cyan-400',
  agent_8: 'bg-orange-500/15 text-orange-400',
};

function getInsight(agent: AgentAnalysis): string | null {
  if (!agent.findings || typeof agent.findings !== 'object') return null;
  const insight = agent.findings.manager_insight;
  return insight ? String(insight) : null;
}

function getAgentKey(agent: AgentAnalysis): string {
  return agent.agent_id ?? agent.id ?? '';
}

function getColor(agentKey: string): string {
  // Match on the base agent id (e.g. "agent_1" from "agent_1_stage_progress")
  const base = agentKey.match(/^agent_\d+e?/)?.[0] ?? '';
  return AGENT_COLORS[base] ?? '';
}

interface KeyFindingsProps {
  agents: AgentAnalysis[];
}

export function KeyFindings({ agents }: KeyFindingsProps) {
  const findings = agents
    .map((agent) => ({
      agentKey: getAgentKey(agent),
      name: agent.agent_name ?? getAgentKey(agent),
      insight: getInsight(agent),
    }))
    .filter((f): f is { agentKey: string; name: string; insight: string } => !!f.insight);

  if (findings.length === 0) return null;

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Key Findings by Dimension
        </h3>
        <div className="space-y-2.5">
          {findings.map(({ agentKey, name, insight }) => (
            <div key={agentKey} className="flex items-start gap-2.5">
              <Badge
                variant="secondary"
                className={`text-[10px] px-1.5 py-0.5 shrink-0 mt-0.5 ${getColor(agentKey)}`}
              >
                {name}
              </Badge>
              <p className="text-sm leading-relaxed text-foreground">{insight}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
