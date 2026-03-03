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

/* ── Individual KPI Card (matches mockup: separate elevated cards) ── */
function KpiCard({
  label,
  children,
  accentColor = 'bg-brand-600/50',
  delay = 0,
}: {
  label: string;
  children: React.ReactNode;
  accentColor?: string;
  delay?: number;
}) {
  return (
    <div
      className="relative rounded-xl border border-border bg-muted px-5 py-5 overflow-hidden animate-row-reveal"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Top accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${accentColor}`} />
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        {label}
      </div>
      {children}
    </div>
  );
}

function AnimatedDollar({
  rawValue,
  colorClass,
}: {
  rawValue: number;
  colorClass?: string;
}) {
  const animated = useCountUp(rawValue);
  return (
    <div className={`font-mono text-[36px] font-medium leading-none tracking-tight ${colorClass ?? 'text-foreground'}`}>
      {formatDollar(animated)}
    </div>
  );
}

/* ── Distribution Bar (full-width below KPI grid) ── */
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
    <div className="space-y-2.5">
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
        Forecast Distribution
      </div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted">
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
      <div className="flex gap-5 text-xs text-muted-foreground">
        {segments.map((seg) => (
          <span key={seg.key} className="flex items-center gap-1.5">
            <span className={`inline-block size-2 rounded-full ${seg.color}`} />
            {seg.label}
            <span className="font-mono font-medium tabular-nums text-foreground/70">
              {formatDollar(seg.value)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Main NumberLine: 5 individual KPI cards ── */
export function NumberLine({ quota, pipeline, forecast }: NumberLineProps) {
  const gapColor = pipeline.gap >= 0 ? 'text-healthy' : 'text-needs-attention';
  const gapAccent = pipeline.gap >= 0 ? 'bg-brand-500' : 'bg-needs-attention';
  const coverageColor =
    pipeline.coverage >= 3 ? 'text-healthy' :
    pipeline.coverage >= 2 ? 'text-neutral' :
    'text-needs-attention';

  const coverageAnimated = useCountUp(Math.round(pipeline.coverage * 10));
  const gapAnimated = useCountUp(Math.abs(pipeline.gap));

  return (
    <div className="space-y-5">
      {/* KPI Grid — 5 individual cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <KpiCard label="Quota" accentColor="bg-brand-500 shadow-[0_0_12px_rgba(16,185,129,0.15)]" delay={50}>
          <AnimatedDollar rawValue={quota.amount} colorClass="text-brand-400" />
          <div className="text-xs text-muted-foreground mt-2">{quota.period}</div>
        </KpiCard>

        <KpiCard label="Pipeline" delay={100}>
          <AnimatedDollar rawValue={pipeline.total_value} />
          <div className="text-xs text-muted-foreground mt-2">
            {pipeline.total_deals} deals
          </div>
        </KpiCard>

        <KpiCard label="Coverage" delay={150}>
          <div className={`font-mono text-[36px] font-medium leading-none tracking-tight ${coverageColor}`}>
            {(coverageAnimated / 10).toFixed(1)}x
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            {pipeline.coverage >= 3 ? 'Strong' : pipeline.coverage >= 2 ? 'Adequate' : 'Low'} coverage
          </div>
        </KpiCard>

        <KpiCard label="Weighted" delay={200}>
          <AnimatedDollar rawValue={pipeline.weighted_value} />
        </KpiCard>

        <KpiCard label="Gap to Quota" accentColor={gapAccent} delay={250}>
          <div className={`font-mono text-[36px] font-medium leading-none tracking-tight ${gapColor}`}>
            {pipeline.gap >= 0 ? '+' : '-'}{formatDollar(gapAnimated)}
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            {pipeline.gap >= 0 ? 'above quota' : 'below quota'}
          </div>
        </KpiCard>
      </div>

      {/* Distribution Bar — below the card grid */}
      <div className="rounded-xl border border-border bg-muted p-5">
        <DistributionBar forecast={forecast} />
      </div>
    </div>
  );
}
