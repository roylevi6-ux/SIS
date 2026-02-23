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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HealthBreakdownProps {
  breakdown: unknown;
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
  rawScore?: string;
  rationale?: string;
}

// ---------------------------------------------------------------------------
// Label mapping
// ---------------------------------------------------------------------------

const COMPONENT_LABELS: Record<string, string> = {
  economic_buyer: 'Econ. Buyer',
  economic_buyer_engagement: 'Econ. Buyer',
  stage: 'Stage',
  stage_appropriateness: 'Stage',
  momentum: 'Momentum',
  momentum_quality: 'Momentum',
  technical_path: 'Tech. Path',
  technical_path_clarity: 'Tech. Path',
  competitive_position: 'Competitive',
  stakeholder_completeness: 'Stakeholders',
  commitment_quality: 'Commitment',
  commercial_clarity: 'Commercial',
};

function normalizeKey(key: string): string {
  return key.toLowerCase().replace(/[\s-]+/g, '_');
}

// ---------------------------------------------------------------------------
// Data normalization
// ---------------------------------------------------------------------------

function toRadarData(breakdown: unknown): RadarDataItem[] {
  if (!breakdown) return [];

  if (Array.isArray(breakdown)) {
    return (breakdown as BreakdownEntry[])
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
  }

  if (typeof breakdown === 'object' && breakdown !== null) {
    return Object.entries(breakdown as Record<string, number>)
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

  return [];
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

function RadarTooltip({ active, payload }: { active?: boolean; payload?: any[] }) {
  if (!active || !payload?.[0]) return null;
  const data = payload[0].payload as RadarDataItem;
  return (
    <div className="rounded-lg border bg-background/95 backdrop-blur px-3 py-2 text-xs shadow-md max-w-[220px]">
      <p className="font-semibold text-sm">{data.dimension}</p>
      <p className="mt-0.5 tabular-nums">
        {data.score}%
        {data.rawScore && (
          <span className="text-muted-foreground ml-1">({data.rawScore})</span>
        )}
      </p>
      {data.rationale && (
        <p className="mt-1.5 text-muted-foreground leading-snug">{data.rationale}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HealthBreakdown({ breakdown }: HealthBreakdownProps) {
  const data = toRadarData(breakdown);

  if (data.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Health Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="flex justify-center">
        <ResponsiveContainer width="100%" height={340}>
          <RadarChart cx="50%" cy="50%" outerRadius="72%" data={data}>
            <PolarGrid
              stroke="hsl(var(--border))"
              strokeOpacity={0.5}
            />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
              tickCount={5}
              axisLine={false}
            />
            <Radar
              dataKey="score"
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.15}
              strokeWidth={2}
              dot={{
                r: 3.5,
                fill: 'hsl(var(--primary))',
                strokeWidth: 0,
              }}
            />
            <Tooltip content={<RadarTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
