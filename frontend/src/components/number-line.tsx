'use client';

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

function KpiItem({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="text-2xl font-bold font-mono tabular-nums text-foreground sm:text-3xl">
        {value}
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
    <div className="space-y-1.5">
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        {segments.map((seg) => {
          const pct = (seg.value / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={seg.key}
              className={`${seg.color} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${seg.label}: ${formatDollar(seg.value)} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        {segments.map((seg) => (
          <span key={seg.key}>
            {seg.label} {formatDollar(seg.value)}
          </span>
        ))}
      </div>
    </div>
  );
}

export function NumberLine({ quota, pipeline, forecast }: NumberLineProps) {
  const gapSign = pipeline.gap >= 0 ? '+' : '';
  const gapColor = pipeline.gap >= 0 ? 'text-healthy' : 'text-critical';
  const coverageColor =
    pipeline.coverage >= 3 ? 'text-healthy' :
    pipeline.coverage >= 2 ? 'text-at-risk' :
    'text-critical';

  return (
    <div className="rounded-xl border bg-brand-50/50 p-5 space-y-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <KpiItem label="Quota" value={formatDollar(quota.amount)} subtext={quota.period} />
        <KpiItem label="Pipeline" value={formatDollar(pipeline.total_value)} subtext={`${pipeline.total_deals} deals`} />
        <div className="flex flex-col items-center">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Coverage
          </span>
          <span className={`text-2xl font-bold font-mono tabular-nums sm:text-3xl ${coverageColor}`}>
            {pipeline.coverage.toFixed(1)}x
          </span>
        </div>
        <KpiItem label="Weighted" value={formatDollar(pipeline.weighted_value)} />
        <div className="flex flex-col items-center">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Gap
          </span>
          <span className={`text-2xl font-bold font-mono tabular-nums sm:text-3xl ${gapColor}`}>
            {gapSign}{formatDollar(Math.abs(pipeline.gap))}
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
