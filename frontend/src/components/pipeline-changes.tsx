'use client';

import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WeeklyChanges } from '@/lib/pipeline-types';

interface PipelineChangesProps {
  changes: WeeklyChanges;
}

function formatDollar(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function Metric({
  label,
  value,
  icon: Icon,
  colorClass,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  colorClass: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className={cn('size-3.5', colorClass)} />
      <span className={cn('text-sm font-semibold tabular-nums', colorClass)}>{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function PipelineChanges({ changes }: PipelineChangesProps) {
  const allZero = Object.values(changes).every((v) => v === 0);
  if (allZero) return null;

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        This week
      </span>
      <Metric label="added" value={`+${formatDollar(changes.added)}`} icon={TrendingUp} colorClass="text-healthy" />
      <Metric label="dropped" value={`-${formatDollar(changes.dropped)}`} icon={TrendingDown} colorClass="text-critical" />
      <Metric
        label="net"
        value={`${changes.net >= 0 ? '+' : ''}${formatDollar(changes.net)}`}
        icon={ArrowRight}
        colorClass={changes.net >= 0 ? 'text-healthy' : 'text-critical'}
      />
      <span className="text-border">|</span>
      <span className="text-xs text-muted-foreground">
        {changes.stage_advances} advances &middot; {changes.forecast_flips} flips &middot; {changes.new_risks} new risks
      </span>
    </div>
  );
}
