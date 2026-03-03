'use client';

import { useCountUp } from '@/lib/hooks/use-count-up';
import type { CommandCenterPipeline, CommandCenterQuota, ForecastBreakdown } from '@/lib/pipeline-types';

interface NumberLineProps {
  quota: CommandCenterQuota;
  pipeline: CommandCenterPipeline;
  forecast: ForecastBreakdown;
}

function formatDollar(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function AnimatedKpi({
  label,
  rawValue,
  subtext,
  colorClass,
}: {
  label: string;
  rawValue: number;
  subtext?: string;
  colorClass?: string;
}) {
  const animated = useCountUp(rawValue);
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className={`text-3xl font-medium font-mono tabular-nums sm:text-4xl ${colorClass ?? 'text-foreground'}`}>
        {formatDollar(animated)}
      </span>
      {subtext && (
        <span className="text-xs text-muted-foreground">{subtext}</span>
      )}
    </div>
  );
}

function DistributionBar({ forecast }: { forecast: ForecastBreakdown }) {
  const total =
    forecast.commit.value +
    forecast.realistic.value +
    forecast.upside.value +
    forecast.risk.value;
  if (total === 0) return null;

  const segments = [
    { key: 'commit', label: 'Commit', value: forecast.commit.value, color: 'bg-forecast-commit' },
    { key: 'realistic', label: 'Realistic', value: forecast.realistic.value, color: 'bg-forecast-realistic' },
    { key: 'upside', label: 'Upside', value: forecast.upside.value, color: 'bg-forecast-upside' },
    { key: 'risk', label: 'Risk', value: forecast.risk.value, color: 'bg-forecast-risk' },
  ];

  return (
    <div className="space-y-2 pt-4 mt-4 border-t border-border">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full">
        {segments.map((seg) => {
          const pct = (seg.value / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={seg.key}
              className={`${seg.color} transition-all duration-700`}
              style={{ width: `${pct}%` }}
              title={`${seg.label}: ${formatDollar(seg.value)} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        {segments.map((seg) => (
          <span key={seg.key} className="flex items-center gap-1.5">
            <span className={`inline-block size-2 rounded-full ${seg.color}`} />
            {seg.label} <span className="font-mono tabular-nums">{formatDollar(seg.value)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export function NumberLine({ quota, pipeline, forecast }: NumberLineProps) {
  const gapColor = pipeline.gap >= 0 ? 'text-healthy' : 'text-needs-attention';
  const coverageColor =
    pipeline.coverage >= 3 ? 'text-healthy' :
    pipeline.coverage >= 2 ? 'text-neutral' :
    'text-needs-attention';

  const coverageAnimated = useCountUp(Math.round(pipeline.coverage * 10));

  return (
    <div className="relative rounded-xl border bg-card p-6 space-y-4 overflow-hidden">
      {/* Top accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-brand-500" />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <AnimatedKpi label="Quota" rawValue={quota.amount} subtext={quota.period} />
        <AnimatedKpi label="Pipeline" rawValue={pipeline.total_value} subtext={`${pipeline.total_deals} deals`} />
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
            Coverage
          </span>
          <span className={`text-3xl font-medium font-mono tabular-nums sm:text-4xl ${coverageColor}`}>
            {(coverageAnimated / 10).toFixed(1)}x
          </span>
        </div>
        <AnimatedKpi label="Weighted" rawValue={pipeline.weighted_value} />
        <div className="flex flex-col items-center gap-1">
          <span className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
            Gap
          </span>
          <span className={`text-3xl font-medium font-mono tabular-nums sm:text-4xl ${gapColor}`}>
            {pipeline.gap >= 0 ? '+' : ''}{formatDollar(Math.abs(pipeline.gap))}
          </span>
          <span className="text-xs text-muted-foreground">
            {pipeline.gap >= 0 ? 'above quota' : 'below quota'}
          </span>
        </div>
      </div>
      <DistributionBar forecast={forecast} />
    </div>
  );
}
