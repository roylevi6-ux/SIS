'use client';

import { cn } from '@/lib/utils';
import type { ForecastBreakdown } from '@/lib/pipeline-types';

export type ForecastFilter = 'all' | 'commit' | 'realistic' | 'upside' | 'risk';
export type HealthFilter = 'healthy' | 'neutral' | 'needs_attention';
export type FlagFilter = 'divergent' | 'stale' | 'declining';

interface FilterChipsProps {
  forecast: ForecastBreakdown;
  totalDeals: number;
  activeForecast: ForecastFilter;
  activeHealth: HealthFilter[];
  activeFlags: FlagFilter[];
  onForecastChange: (filter: ForecastFilter) => void;
  onHealthToggle: (filter: HealthFilter) => void;
  onFlagToggle: (filter: FlagFilter) => void;
  onClearAll: () => void;
  healthCounts: { healthy: number; neutral: number; needs_attention: number };
  flagCounts: { divergent: number; stale: number; declining: number };
}

function Chip({
  label,
  count,
  active,
  colorClass,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  colorClass: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? `${colorClass} text-white shadow-sm`
          : 'bg-muted text-muted-foreground hover:bg-muted/80'
      )}
    >
      {label}
      <span className={cn(
        'inline-flex items-center justify-center rounded-full px-1.5 text-[10px] font-semibold min-w-[20px]',
        active ? 'bg-white/20 text-white' : 'bg-background text-foreground'
      )}>
        {count}
      </span>
    </button>
  );
}

export function FilterChips({
  forecast,
  totalDeals,
  activeForecast,
  activeHealth,
  activeFlags,
  onForecastChange,
  onHealthToggle,
  onFlagToggle,
  onClearAll,
  healthCounts,
  flagCounts,
}: FilterChipsProps) {
  const hasActiveFilters =
    activeForecast !== 'all' || activeHealth.length > 0 || activeFlags.length > 0;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Chip label="All" count={totalDeals} active={activeForecast === 'all'} colorClass="bg-foreground" onClick={() => onForecastChange('all')} />
      <Chip label="Commit" count={forecast.commit.count} active={activeForecast === 'commit'} colorClass="bg-forecast-commit" onClick={() => onForecastChange('commit')} />
      <Chip label="Realistic" count={forecast.realistic.count} active={activeForecast === 'realistic'} colorClass="bg-forecast-realistic" onClick={() => onForecastChange('realistic')} />
      <Chip label="Upside" count={forecast.upside.count} active={activeForecast === 'upside'} colorClass="bg-forecast-upside" onClick={() => onForecastChange('upside')} />
      <Chip label="Risk" count={forecast.risk.count} active={activeForecast === 'risk'} colorClass="bg-forecast-risk" onClick={() => onForecastChange('risk')} />

      <span className="mx-1 text-border">|</span>

      <Chip label="Healthy" count={healthCounts.healthy} active={activeHealth.includes('healthy')} colorClass="bg-healthy" onClick={() => onHealthToggle('healthy')} />
      <Chip label="Neutral" count={healthCounts.neutral} active={activeHealth.includes('neutral')} colorClass="bg-neutral" onClick={() => onHealthToggle('neutral')} />
      <Chip label="Needs Attention" count={healthCounts.needs_attention} active={activeHealth.includes('needs_attention')} colorClass="bg-needs-attention" onClick={() => onHealthToggle('needs_attention')} />

      <span className="mx-1 text-border">|</span>

      <Chip label="Divergent" count={flagCounts.divergent} active={activeFlags.includes('divergent')} colorClass="bg-neutral" onClick={() => onFlagToggle('divergent')} />
      <Chip label="Stale" count={flagCounts.stale} active={activeFlags.includes('stale')} colorClass="bg-muted-foreground" onClick={() => onFlagToggle('stale')} />
      <Chip label="Declining" count={flagCounts.declining} active={activeFlags.includes('declining')} colorClass="bg-needs-attention" onClick={() => onFlagToggle('declining')} />

      {hasActiveFilters && (
        <button
          onClick={onClearAll}
          className="text-xs text-muted-foreground hover:text-foreground underline ml-2"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
