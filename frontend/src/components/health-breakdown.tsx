'use client';

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HealthBreakdownProps {
  breakdown: unknown;
  healthScore?: number | null;
}

interface BreakdownEntry {
  component: string;
  score: number;
  max_score: number;
  rationale?: string;
}

interface RadarDataItem {
  dimension: string;
  score: number;
  fullMark: number;
  zone100: number;
  zone70: number;
  zone45: number;
  rawScore?: string;
  rationale?: string;
}

// ---------------------------------------------------------------------------
// Constants — health zone thresholds
// ---------------------------------------------------------------------------

const ZONE_HEALTHY = 70;
const ZONE_AT_RISK = 45;

const COLOR_HEALTHY = '#059669';
const COLOR_AT_RISK = '#d97706';
const COLOR_CRITICAL = '#dc2626';

// ---------------------------------------------------------------------------
// Label mapping
// ---------------------------------------------------------------------------

const COMPONENT_LABELS: Record<string, string> = {
  buyer_validated_pain_commercial_clarity: 'Pain & Comm.',
  'buyer_validated_pain_&_commercial_clarity': 'Pain & Comm.',
  momentum_quality: 'Momentum',
  momentum: 'Momentum',
  champion_strength: 'Champion',
  commitment_quality: 'Commitment',
  economic_buyer_engagement: 'Econ. Buyer',
  economic_buyer: 'Econ. Buyer',
  urgency_compelling_event: 'Urgency',
  'urgency_&_compelling_event': 'Urgency',
  urgency: 'Urgency',
  stage_appropriateness: 'Stage',
  stage: 'Stage',
  multithreading_stakeholder_coverage: 'Multi-thread',
  'multithreading_&_stakeholder_coverage': 'Multi-thread',
  'multi_threading_&_stakeholder_coverage': 'Multi-thread',
  competitive_position: 'Competitive',
  technical_path_clarity: 'Tech. Path',
  technical_path: 'Tech. Path',
  account_health: 'Acct. Health',
  account_relationship_health: 'Acct. Health',
  // Legacy keys (backward compat with old data — will be removed in v2)
  stakeholder_completeness: 'Stakeholders',
  commercial_clarity: 'Commercial',
};

const LEGACY_KEYS = new Set(['stakeholder_completeness', 'commercial_clarity']);

function normalizeKey(key: string): string {
  const normalized = key.toLowerCase().replace(/[\s-]+/g, '_');
  if (LEGACY_KEYS.has(normalized)) {
    console.warn(
      `[HealthBreakdown] Legacy dimension "${key}" detected — this was split/renamed in v1.0. ` +
      `Update data source to use new dimension names.`
    );
  }
  return normalized;
}

// ---------------------------------------------------------------------------
// Health zone helpers
// ---------------------------------------------------------------------------

function getZone(score: number): 'healthy' | 'at-risk' | 'critical' {
  if (score >= ZONE_HEALTHY) return 'healthy';
  if (score >= ZONE_AT_RISK) return 'at-risk';
  return 'critical';
}

function getZoneColor(score: number): string {
  if (score >= ZONE_HEALTHY) return COLOR_HEALTHY;
  if (score >= ZONE_AT_RISK) return COLOR_AT_RISK;
  return COLOR_CRITICAL;
}

const ZONE_LABEL: Record<'healthy' | 'at-risk' | 'critical', string> = {
  healthy: 'Healthy',
  'at-risk': 'At Risk',
  critical: 'Critical',
};

const ZONE_BADGE_CLASS: Record<'healthy' | 'at-risk' | 'critical', string> = {
  healthy:
    'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-400 dark:border-emerald-800',
  'at-risk':
    'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800',
  critical:
    'bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800',
};

// ---------------------------------------------------------------------------
// Data normalization
// ---------------------------------------------------------------------------

function toRadarData(breakdown: unknown): RadarDataItem[] {
  if (!breakdown) return [];

  let items: Omit<RadarDataItem, 'zone100' | 'zone70' | 'zone45'>[] = [];

  if (Array.isArray(breakdown)) {
    items = (breakdown as BreakdownEntry[])
      .filter((e) => e.component && typeof e.score === 'number')
      .map((entry) => {
        const key = normalizeKey(entry.component);
        const label =
          COMPONENT_LABELS[key] ??
          entry.component
            .replace(/\b\w/g, (c) => c.toUpperCase())
            .replace(/^(.{12}).+$/, '$1\u2026');
        const pct =
          entry.max_score > 0
            ? Math.round((entry.score / entry.max_score) * 100)
            : Math.round(entry.score);
        return {
          dimension: label,
          score: pct,
          fullMark: 100,
          rawScore: `${entry.score}/${entry.max_score}`,
          rationale: entry.rationale,
        };
      });
  } else if (typeof breakdown === 'object' && breakdown !== null) {
    items = Object.entries(breakdown as Record<string, number>)
      .filter(([, v]) => typeof v === 'number')
      .map(([apiKey, score]) => {
        const key = normalizeKey(apiKey);
        const label =
          COMPONENT_LABELS[key] ??
          apiKey
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c) => c.toUpperCase())
            .replace(/^(.{12}).+$/, '$1\u2026');
        return {
          dimension: label,
          score: Math.round(score),
          fullMark: 100,
        };
      });
  }

  return items.map((item) => ({
    ...item,
    zone100: 100,
    zone70: 70,
    zone45: 45,
  }));
}

function deriveOverallScore(data: RadarDataItem[]): number | null {
  if (data.length === 0) return null;
  const sum = data.reduce((acc, d) => acc + d.score, 0);
  return Math.round(sum / data.length);
}

// ---------------------------------------------------------------------------
// Custom angle axis tick — label + coloured score pill
// ---------------------------------------------------------------------------

interface CustomTickProps {
  x?: string | number;
  y?: string | number;
  cx?: string | number;
  cy?: string | number;
  payload?: { value: string };
  scoreMap?: Map<string, number>;
  textAnchor?: 'start' | 'middle' | 'end' | 'inherit';
  index?: number;
}

function CustomAngleTick({
  x: xRaw = 0,
  y: yRaw = 0,
  cx: cxRaw = 0,
  cy: cyRaw = 0,
  payload,
  scoreMap,
  textAnchor = 'middle',
}: CustomTickProps) {
  if (!payload) return null;

  const x = Number(xRaw);
  const y = Number(yRaw);
  const cx = Number(cxRaw);
  const cy = Number(cyRaw);

  const label = payload.value;
  const score = scoreMap?.get(label);
  const color = score !== undefined ? getZoneColor(score) : '#6b7280';

  // Push the tick outward from the chart centre
  const dx = x - cx;
  const dy = y - cy;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const nudge = 14;
  const nx = x + (dx / dist) * nudge;
  const ny = y + (dy / dist) * nudge;

  // Pill dimensions
  const PILL_W = 38;
  const PILL_H = 18;
  const PILL_GAP = 4; // gap between label baseline and pill top

  // Pill horizontal alignment follows the textAnchor so it sits flush with
  // the label — not always centered, which caused overlaps on the sides.
  let pillRectX: number;
  if (textAnchor === 'start') {
    pillRectX = nx;
  } else if (textAnchor === 'end') {
    pillRectX = nx - PILL_W;
  } else {
    pillRectX = nx - PILL_W / 2;
  }
  const pillTextX = pillRectX + PILL_W / 2;

  // Label at ny, pill directly below with a small gap
  const labelBaseY = ny;
  const pillTopY = labelBaseY + PILL_GAP;

  // Build native tooltip text for the label/pill area
  const zone = score !== undefined ? ZONE_LABEL[getZone(score)] : '';
  const titleText = score !== undefined
    ? `${label}: ${score}% (${zone})`
    : label;

  return (
    <g style={{ cursor: 'default' }}>
      <title>{titleText}</title>
      {/* Dimension label */}
      <text
        x={nx}
        y={labelBaseY}
        textAnchor={textAnchor}
        dominantBaseline="auto"
        style={{
          fontSize: 12,
          fill: 'hsl(var(--muted-foreground))',
          fontWeight: 500,
        }}
      >
        {label}
      </text>

      {/* Score pill — anchored below label, aligned to same edge */}
      {score !== undefined && (
        <>
          <rect
            x={pillRectX}
            y={pillTopY}
            width={PILL_W}
            height={PILL_H}
            rx={PILL_H / 2}
            fill={color}
            fillOpacity={0.14}
          />
          <rect
            x={pillRectX}
            y={pillTopY}
            width={PILL_W}
            height={PILL_H}
            rx={PILL_H / 2}
            fill="none"
            stroke={color}
            strokeWidth={0.8}
            strokeOpacity={0.55}
          />
          <text
            x={pillTextX}
            y={pillTopY + PILL_H / 2 + 4}
            textAnchor="middle"
            dominantBaseline="auto"
            style={{ fontSize: 11, fill: color, fontWeight: 700 }}
          >
            {score}%
          </text>
        </>
      )}
    </g>
  );
}

// ---------------------------------------------------------------------------
// Simple hover tooltip — no animation, appears/disappears instantly
// ---------------------------------------------------------------------------

function SimpleTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: unknown[];
}) {
  if (!active || !Array.isArray(payload)) return null;

  const scoreEntry = (
    payload as Array<{ dataKey?: string; payload?: RadarDataItem }>
  ).find((p) => p.dataKey === 'score');

  const data = scoreEntry?.payload;
  if (!data || typeof data.score !== 'number') return null;

  const zone = ZONE_LABEL[getZone(data.score)];
  const color = getZoneColor(data.score);

  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md max-w-[220px]">
      <p className="font-semibold text-foreground">
        {data.dimension}{' '}
        <span style={{ color }} className="tabular-nums">{data.score}%</span>
        {' '}<span className="text-muted-foreground font-normal">({zone})</span>
      </p>
      {data.rationale && (
        <p className="text-muted-foreground mt-1 leading-snug">{data.rationale}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Needs Attention / Watch List panels — replaces DimensionLegend
// ---------------------------------------------------------------------------

function WeaknessPanel({ data }: { data: RadarDataItem[] }) {
  const critical = data
    .filter((d) => d.score < ZONE_AT_RISK)
    .sort((a, b) => a.score - b.score);
  const atRisk = data
    .filter((d) => d.score >= ZONE_AT_RISK && d.score < ZONE_HEALTHY)
    .sort((a, b) => a.score - b.score);

  if (critical.length === 0 && atRisk.length === 0) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 px-3">
      {critical.length > 0 && (
        <div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50/50 dark:bg-red-950/30 p-3">
          <p className="text-[11px] font-semibold text-red-600 dark:text-red-400 mb-2 uppercase tracking-wide">
            Needs Attention
          </p>
          <div className="space-y-1.5">
            {critical.map((item) => (
              <div key={item.dimension} className="flex items-center justify-between gap-2">
                <span className="text-xs text-red-700 dark:text-red-300 truncate">
                  {item.dimension}
                </span>
                <span className="text-xs font-bold tabular-nums text-red-600 dark:text-red-400">
                  {item.score}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {atRisk.length > 0 && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/30 p-3">
          <p className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 mb-2 uppercase tracking-wide">
            Watch List
          </p>
          <div className="space-y-1.5">
            {atRisk.map((item) => (
              <div key={item.dimension} className="flex items-center justify-between gap-2">
                <span className="text-xs text-amber-700 dark:text-amber-300 truncate">
                  {item.dimension}
                </span>
                <span className="text-xs font-bold tabular-nums text-amber-600 dark:text-amber-400">
                  {item.score}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Zone legend
// ---------------------------------------------------------------------------

function ZoneLegend() {
  return (
    <div className="flex items-center gap-4 text-[11px] text-muted-foreground whitespace-nowrap">
      {(
        [
          { color: COLOR_CRITICAL, label: 'Critical <45' },
          { color: COLOR_AT_RISK, label: 'At Risk 45\u201369' },
          { color: COLOR_HEALTHY, label: 'Healthy 70+' },
        ] as const
      ).map(({ color, label }) => (
        <span key={label} className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm opacity-80"
            style={{ background: color }}
          />
          {label}
        </span>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function HealthBreakdown({ breakdown, healthScore }: HealthBreakdownProps) {
  const data = toRadarData(breakdown);

  if (data.length === 0) return null;

  const derivedScore = deriveOverallScore(data);
  const overallScore = healthScore != null ? healthScore : derivedScore;
  const overallZone = overallScore !== null ? getZone(overallScore) : null;
  const scoreMap = new Map(data.map((d) => [d.dimension, d.score]));

  const radarColor =
    overallScore !== null ? getZoneColor(overallScore) : '#6366f1';

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <CardHeader className="pb-0 pt-5 px-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-0.5">
            <CardTitle className="text-base font-semibold tracking-tight">
              Health Breakdown
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              {data.length} dimensions &middot; scored 0&ndash;100
            </p>
          </div>
        </div>
      </CardHeader>

      {/* Chart with centred overall score */}
      <CardContent className="px-2 pt-2 pb-4">
        <div className="relative">
          <ResponsiveContainer width="100%" height={520}>
            <RadarChart
              cx="50%"
              cy="50%"
              outerRadius="80%"
              data={data}
              margin={{ top: 44, right: 56, bottom: 44, left: 56 }}
            >
              {/* Zone band: outer healthy ring (green, covers full area) */}
              <Radar
                dataKey="zone100"
                stroke="none"
                fill={COLOR_HEALTHY}
                fillOpacity={0.13}
                dot={false}
                legendType="none"
                isAnimationActive={false}
              />
              {/* Zone band: middle at-risk ring (amber, overwrites centre of green) */}
              <Radar
                dataKey="zone70"
                stroke="none"
                fill={COLOR_AT_RISK}
                fillOpacity={0.16}
                dot={false}
                legendType="none"
                isAnimationActive={false}
              />
              {/* Zone band: inner critical ring (red, overwrites centre of amber) */}
              <Radar
                dataKey="zone45"
                stroke="none"
                fill={COLOR_CRITICAL}
                fillOpacity={0.20}
                dot={false}
                legendType="none"
                isAnimationActive={false}
              />

              {/* Dashed threshold rings at 45% and 70% */}
              <Radar
                dataKey="zone70"
                stroke={COLOR_AT_RISK}
                strokeWidth={1}
                strokeDasharray="4 3"
                strokeOpacity={0.45}
                fill="none"
                dot={false}
                legendType="none"
                isAnimationActive={false}
              />
              <Radar
                dataKey="zone45"
                stroke={COLOR_CRITICAL}
                strokeWidth={1}
                strokeDasharray="4 3"
                strokeOpacity={0.45}
                fill="none"
                dot={false}
                legendType="none"
                isAnimationActive={false}
              />

              {/* Polar grid */}
              <PolarGrid
                stroke="hsl(var(--border))"
                strokeOpacity={0.45}
              />

              {/* Radius axis — hidden ticks, sets domain */}
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={false}
                tickCount={6}
                axisLine={false}
                stroke="transparent"
              />

              {/* Angle axis with custom ticks */}
              <PolarAngleAxis
                dataKey="dimension"
                tick={(props: CustomTickProps) => (
                  <CustomAngleTick {...props} scoreMap={scoreMap} />
                )}
                tickLine={false}
              />

              {/* Main score radar */}
              <Radar
                dataKey="score"
                stroke={radarColor}
                fill={radarColor}
                fillOpacity={0.22}
                strokeWidth={2.5}
                dot={(dotProps: {
                  cx?: number;
                  cy?: number;
                  index?: number;
                }) => {
                  const { cx = 0, cy = 0, index = 0 } = dotProps;
                  const item = data[index];
                  const dotColor = item ? getZoneColor(item.score) : radarColor;
                  return (
                    <circle
                      key={`dot-${index}`}
                      cx={cx}
                      cy={cy}
                      r={4.5}
                      fill={dotColor}
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                  );
                }}
                activeDot={(dotProps: {
                  cx?: number;
                  cy?: number;
                  index?: number;
                }) => {
                  const { cx = 0, cy = 0, index = 0 } = dotProps;
                  const item = data[index];
                  const dotColor = item ? getZoneColor(item.score) : radarColor;
                  return (
                    <circle
                      key={`adot-${index}`}
                      cx={cx}
                      cy={cy}
                      r={6}
                      fill={dotColor}
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    />
                  );
                }}
              />

              <Tooltip
                content={<SimpleTooltip />}
                cursor={false}
                isAnimationActive={false}
              />
            </RadarChart>
          </ResponsiveContainer>

          {/* Centred overall score overlay */}
          {overallScore !== null && overallZone !== null && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="flex flex-col items-center gap-0.5">
                <span
                  className="text-3xl font-bold tabular-nums leading-none"
                  style={{ color: radarColor }}
                >
                  {overallScore}
                </span>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[11px] font-medium border px-1.5 py-0 pointer-events-auto',
                    ZONE_BADGE_CLASS[overallZone],
                  )}
                >
                  {ZONE_LABEL[overallZone]}
                </Badge>
              </div>
            </div>
          )}
        </div>

        {/* Zone legend */}
        <div className="flex items-center gap-3 px-3 mb-3">
          <div className="flex-1 h-px bg-border" />
          <ZoneLegend />
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Weakness panels (replaces old dimension grid) */}
        <WeaknessPanel data={data} />
      </CardContent>
    </Card>
  );
}
