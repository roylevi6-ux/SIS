'use client';

import { useAssessmentTimeline } from '@/lib/hooks/use-analyses';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineEntry {
  id: string;
  analysis_run_id: string;
  created_at: string;
  health_score: number;
  inferred_stage: number;
  stage_name: string;
  momentum_direction: string;
  ai_forecast_category: string;
  overall_confidence: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function healthColor(score: number): string {
  if (score >= 70) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 40) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

function momentumIcon(dir: string): string {
  if (dir === 'Improving') return '\u2191';
  if (dir === 'Declining') return '\u2193';
  return '\u2192';
}

function momentumColor(dir: string): string {
  if (dir === 'Improving') return 'text-emerald-600 dark:text-emerald-400';
  if (dir === 'Declining') return 'text-red-600 dark:text-red-400';
  return 'text-muted-foreground';
}

// ---------------------------------------------------------------------------
// Sparkline (simple inline SVG)
// ---------------------------------------------------------------------------

function HealthSparkline({ entries }: { entries: TimelineEntry[] }) {
  if (entries.length < 2) return null;

  const scores = entries.map((e) => e.health_score);
  const min = Math.min(...scores, 0);
  const max = Math.max(...scores, 100);
  const range = max - min || 1;

  const width = 120;
  const height = 32;
  const padding = 2;

  const points = scores.map((score, i) => {
    const x = padding + (i / (scores.length - 1)) * (width - padding * 2);
    const y = height - padding - ((score - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const lastScore = scores[scores.length - 1];
  const color = lastScore >= 70 ? '#10b981' : lastScore >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        points={points.join(' ')}
      />
      {/* Dot on last point */}
      {points.length > 0 && (
        <circle
          cx={points[points.length - 1].split(',')[0]}
          cy={points[points.length - 1].split(',')[1]}
          r="2.5"
          fill={color}
        />
      )}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DealTimeline({ accountId }: { accountId: string }) {
  const { data, isLoading } = useAssessmentTimeline(accountId);
  const entries = (data ?? []) as unknown as TimelineEntry[];

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="h-24 rounded bg-muted/20 animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Assessment Timeline</h2>
        <HealthSparkline entries={entries} />
      </div>
      <Card>
        <CardContent className="pt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead className="text-center">Health</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Momentum</TableHead>
                <TableHead>Forecast</TableHead>
                <TableHead className="text-center">Confidence</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...entries].reverse().map((entry, i) => {
                // Compute delta from previous row (entries are asc, reversed for display)
                const prevEntry = i < entries.length - 1 ? [...entries].reverse()[i + 1] : null;
                const healthDelta = prevEntry ? entry.health_score - prevEntry.health_score : null;

                return (
                  <TableRow key={entry.id}>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={`font-semibold tabular-nums ${healthColor(entry.health_score)}`}>
                        {entry.health_score}
                      </span>
                      {healthDelta !== null && healthDelta !== 0 && (
                        <span className={`text-xs ml-1 ${healthDelta > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                          ({healthDelta > 0 ? '+' : ''}{healthDelta})
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {entry.inferred_stage} - {entry.stage_name}
                    </TableCell>
                    <TableCell>
                      <span className={momentumColor(entry.momentum_direction)}>
                        {momentumIcon(entry.momentum_direction)} {entry.momentum_direction}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {entry.ai_forecast_category}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center text-sm tabular-nums">
                      {Math.round(entry.overall_confidence <= 1.0 ? entry.overall_confidence * 100 : entry.overall_confidence)}%
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
