'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface TeamRollupData {
  team_name: string;
  total_deals: number;
  avg_health_score: number | null;
  healthy_count: number;
  at_risk_count: number;
  critical_count: number;
  total_mrr: number;
}

interface TeamRollupCardsProps {
  rollup: TeamRollupData[];
  onTeamClick?: (teamName: string) => void;
}

function formatMrr(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function healthColor(score: number | null): string {
  if (score === null) return 'text-muted-foreground';
  if (score >= 70) return 'text-healthy';
  if (score >= 45) return 'text-at-risk';
  return 'text-critical';
}

export function TeamRollupCards({ rollup, onTeamClick }: TeamRollupCardsProps) {
  if (!rollup || rollup.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {rollup.map((team) => (
        <Card
          key={team.team_name}
          className={cn(
            'transition-colors',
            onTeamClick && 'cursor-pointer hover:border-primary/50'
          )}
          onClick={() => onTeamClick?.(team.team_name)}
        >
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium truncate">
              {team.team_name}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className={cn('text-2xl font-bold', healthColor(team.avg_health_score))}>
                {team.avg_health_score !== null ? team.avg_health_score : '--'}
              </span>
              <span className="text-xs text-muted-foreground">avg health</span>
            </div>
            <div className="flex gap-3 text-xs text-muted-foreground">
              <span>{team.total_deals} deals</span>
              <span>{formatMrr(team.total_mrr)}</span>
            </div>
            <div className="flex gap-2 text-xs">
              {team.healthy_count > 0 && (
                <span className="text-healthy">{team.healthy_count} healthy</span>
              )}
              {team.at_risk_count > 0 && (
                <span className="text-at-risk">{team.at_risk_count} at risk</span>
              )}
              {team.critical_count > 0 && (
                <span className="text-critical">{team.critical_count} critical</span>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
