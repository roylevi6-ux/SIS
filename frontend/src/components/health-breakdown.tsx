'use client';

import type { TooltipContentProps } from 'recharts';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// Agent 10 returns an array of objects OR a flat dict — accept both
interface HealthBreakdownProps {
  breakdown: unknown;
}

// Array-of-objects format from Agent 10
interface BreakdownEntry {
  component: string;
  score: number;
  max_score: number;
  rationale?: string;
}

// Canonical display names for health components
const COMPONENT_LABELS: Record<string, string> = {
  economic_buyer: 'Economic Buyer',
  economic_buyer_engagement: 'Economic Buyer',
  stage: 'Stage',
  stage_appropriateness: 'Stage',
  momentum: 'Momentum',
  momentum_quality: 'Momentum',
  technical_path: 'Technical Path',
  technical_path_clarity: 'Technical Path',
  competitive_position: 'Competitive Position',
  stakeholder_completeness: 'Stakeholder Completeness',
  commitment_quality: 'Commitment Quality',
  commercial_clarity: 'Commercial Clarity',
};

function getBarColor(score: number): string {
  if (score >= 70) return '#10b981'; // emerald-500
  if (score >= 45) return '#f59e0b'; // amber-500
  return '#ef4444'; // red-500
}

function normalizeKey(key: string): string {
  return key.toLowerCase().replace(/[\s-]+/g, '_');
}

interface ChartDataItem {
  label: string;
  score: number;
  rawScore?: string;
  rationale?: string;
  fill: string;
}

/**
 * Normalize breakdown data into chart-ready items.
 * Handles two formats:
 *   1. Array of {component, score, max_score, rationale} (Agent 10 output)
 *   2. Flat dict {key: score} (legacy/alternative format)
 */
function toChartData(breakdown: unknown): ChartDataItem[] {
  if (!breakdown) return [];

  // Format 1: Array of objects
  if (Array.isArray(breakdown)) {
    return (breakdown as BreakdownEntry[])
      .filter((e) => e.component && typeof e.score === 'number')
      .map((entry) => {
        const key = normalizeKey(entry.component);
        const label = COMPONENT_LABELS[key]
          ?? entry.component.replace(/\b\w/g, (c) => c.toUpperCase());
        const pct = entry.max_score > 0
          ? Math.round((entry.score / entry.max_score) * 100)
          : Math.round(entry.score);
        return {
          label,
          score: pct,
          rawScore: `${entry.score}/${entry.max_score}`,
          rationale: entry.rationale,
          fill: getBarColor(pct),
        };
      });
  }

  // Format 2: Flat dict
  if (typeof breakdown === 'object' && breakdown !== null) {
    return Object.entries(breakdown as Record<string, number>)
      .filter(([, v]) => typeof v === 'number')
      .map(([apiKey, score]) => {
        const key = normalizeKey(apiKey);
        const label = COMPONENT_LABELS[key]
          ?? apiKey.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const rounded = Math.round(score);
        return {
          label,
          score: rounded,
          fill: getBarColor(rounded),
        };
      });
  }

  return [];
}

export function HealthBreakdown({ breakdown }: HealthBreakdownProps) {
  const chartData = toChartData(breakdown);

  if (chartData.length === 0) {
    return null;
  }

  // Sort by score ascending so the lowest are at the top (most actionable)
  chartData.sort((a, b) => a.score - b.score);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Health Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={chartData.length * 40 + 20}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
          >
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category"
              dataKey="label"
              width={170}
              tick={{ fontSize: 13 }}
            />
            <Tooltip
              content={({ active, payload }: TooltipContentProps<number, string>) => {
                if (!active || !payload?.[0]) return null;
                const data = payload[0].payload as ChartDataItem;
                return (
                  <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-sm max-w-xs">
                    <p className="font-medium">{data.label}</p>
                    <p>
                      Score: {data.score}%
                      {data.rawScore && ` (${data.rawScore})`}
                    </p>
                    {data.rationale && (
                      <p className="mt-1 text-muted-foreground">{data.rationale}</p>
                    )}
                  </div>
                );
              }}
              cursor={{ fill: 'transparent' }}
            />
            <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={20}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <span className="size-2.5 rounded-full bg-emerald-500" /> Healthy (70+)
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2.5 rounded-full bg-amber-500" /> At Risk (45-69)
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2.5 rounded-full bg-red-500" /> Critical (&lt;45)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
