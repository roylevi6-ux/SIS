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

interface HealthBreakdownProps {
  breakdown: Record<string, number> | null | undefined;
}

// Canonical display names and weights for health components
const COMPONENT_CONFIG: Record<string, { label: string; weight: number }> = {
  economic_buyer: { label: 'Economic Buyer', weight: 15 },
  stage: { label: 'Stage', weight: 15 },
  momentum: { label: 'Momentum', weight: 15 },
  technical_path: { label: 'Technical Path', weight: 10 },
  competitive_position: { label: 'Competitive Position', weight: 10 },
  stakeholder_completeness: { label: 'Stakeholder Completeness', weight: 10 },
  commitment_quality: { label: 'Commitment Quality', weight: 15 },
  commercial_clarity: { label: 'Commercial Clarity', weight: 10 },
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
  weight: string;
  fill: string;
}

export function HealthBreakdown({ breakdown }: HealthBreakdownProps) {
  if (!breakdown || Object.keys(breakdown).length === 0) {
    return null;
  }

  // Build chart data by matching API keys to our config
  const chartData: ChartDataItem[] = [];

  for (const [apiKey, score] of Object.entries(breakdown)) {
    const normalizedKey = normalizeKey(apiKey);
    const config = COMPONENT_CONFIG[normalizedKey];

    if (config) {
      chartData.push({
        label: config.label,
        score: Math.round(score),
        weight: `${config.weight}%`,
        fill: getBarColor(score),
      });
    } else {
      // Unknown key: display it anyway with a reasonable label
      const label = apiKey
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
      chartData.push({
        label,
        score: Math.round(score),
        weight: '--',
        fill: getBarColor(score),
      });
    }
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
                  <div className="rounded-md border bg-background px-3 py-1.5 text-xs shadow-sm">
                    <p className="font-medium">{data.label}</p>
                    <p>Score: {data.score} / 100 (weight: {data.weight})</p>
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
