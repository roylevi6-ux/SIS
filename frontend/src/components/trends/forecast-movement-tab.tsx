'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useForecastMovement } from '@/lib/hooks/use-trends';
import Link from 'next/link';
import type { DivergenceTrendPoint } from '@/lib/api-types';

function AlignmentTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ payload: DivergenceTrendPoint }>; label?: string }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md text-sm space-y-2">
      <p className="font-medium">{label}</p>
      <div className="space-y-1">
        <p className="text-amber-600">
          Stage Gaps: {d.stage_gap_count} deal{d.stage_gap_count !== 1 ? 's' : ''}
        </p>
        {d.stage_gap_count > 0 && (
          <div className="pl-3 text-xs text-muted-foreground">
            <p>SF ahead: {d.stage_sf_ahead}</p>
            <p>SIS ahead: {d.stage_sis_ahead}</p>
          </div>
        )}
        <p className="text-purple-600">
          Forecast Gaps: {d.forecast_gap_count} deal{d.forecast_gap_count !== 1 ? 's' : ''}
        </p>
        {d.forecast_gap_count > 0 && (
          <div className="pl-3 text-xs text-muted-foreground">
            <p>SF more optimistic: {d.forecast_sf_optimistic}</p>
            <p>SIS more optimistic: {d.forecast_sis_optimistic}</p>
          </div>
        )}
      </div>
      <div className="border-t pt-1 text-xs text-muted-foreground">
        Total misaligned: {d.any_gap_count} / {d.total_deals} ({(100 - d.alignment_pct).toFixed(1)}%)
      </div>
    </div>
  );
}

export function ForecastMovementTab({ weeks }: { weeks: number }) {
  const { data, isLoading } = useForecastMovement(weeks);
  if (isLoading) return <div className="py-12 text-center text-muted-foreground">Loading forecast data...</div>;
  if (!data) return <div className="py-12 text-center text-muted-foreground">No forecast data available.</div>;

  const s = data.migration_summary;
  const trend = data.divergence_trend;
  const latest = trend.length > 0 ? trend[trend.length - 1] : null;
  const prev = trend.length > 1 ? trend[trend.length - 2] : null;

  // Compute alignment percentages for the KPI card
  const stageAlignPct = latest
    ? latest.total_deals > 0
      ? Math.round(((latest.total_deals - latest.stage_gap_count) / latest.total_deals) * 100)
      : 100
    : null;
  const forecastAlignPct = latest
    ? latest.total_deals > 0
      ? Math.round(((latest.total_deals - latest.forecast_gap_count) / latest.total_deals) * 100)
      : 100
    : null;

  // Week-over-week delta for overall alignment
  const alignmentDelta = latest && prev
    ? Math.round(latest.alignment_pct - prev.alignment_pct)
    : null;

  return (
    <div className="space-y-6 mt-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Deals Moved</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{data.migrations.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Positive Migrations</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-500">{s.upgrades}</p>
            <p className="text-sm text-muted-foreground">${(s.upgrade_value / 1000).toFixed(0)}K</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Negative Migrations</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{s.downgrades}</p>
            <p className="text-sm text-muted-foreground">${(s.downgrade_value / 1000).toFixed(0)}K</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Pipeline Alignment</CardTitle>
          </CardHeader>
          <CardContent>
            {latest ? (
              <div className="space-y-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold">{Math.round(latest.alignment_pct)}%</span>
                  {alignmentDelta !== null && alignmentDelta !== 0 && (
                    <span className={`text-sm font-medium ${alignmentDelta > 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {alignmentDelta > 0 ? '+' : ''}{alignmentDelta}pp
                    </span>
                  )}
                </div>
                <div className="flex gap-3 text-xs text-muted-foreground">
                  <span>
                    Stage{' '}
                    <span className={stageAlignPct !== null && stageAlignPct >= 90 ? 'text-green-600' : stageAlignPct !== null && stageAlignPct >= 70 ? 'text-amber-600' : 'text-red-600'}>
                      {stageAlignPct ?? '—'}%
                    </span>
                  </span>
                  <span>
                    Forecast{' '}
                    <span className={forecastAlignPct !== null && forecastAlignPct >= 90 ? 'text-green-600' : forecastAlignPct !== null && forecastAlignPct >= 70 ? 'text-amber-600' : 'text-red-600'}>
                      {forecastAlignPct ?? '—'}%
                    </span>
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-2xl font-bold text-muted-foreground">—</p>
            )}
          </CardContent>
        </Card>
      </div>

      {data.migrations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Forecast Category Migrations</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead className="text-right">MRR</TableHead>
                  <TableHead>Previous</TableHead>
                  <TableHead></TableHead>
                  <TableHead>Current</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.migrations.map((m) => (
                  <TableRow
                    key={m.account_id}
                    className={
                      m.direction === 'upgrade'
                        ? 'bg-green-50 dark:bg-green-950/20'
                        : 'bg-red-50 dark:bg-red-950/20'
                    }
                  >
                    <TableCell>
                      <Link href={`/deals/${m.account_id}`} className="text-blue-600 hover:underline">
                        {m.account_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right">${(m.cp_estimate / 1000).toFixed(0)}K</TableCell>
                    <TableCell>{m.previous_category}</TableCell>
                    <TableCell className="text-center">{m.direction === 'upgrade' ? '\u2191' : '\u2193'}</TableCell>
                    <TableCell>{m.current_category}</TableCell>
                    <TableCell className="text-muted-foreground">{m.changed_at}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {trend.length >= 2 ? (
        <Card>
          <CardHeader>
            <CardTitle>Salesforce Alignment Trend</CardTitle>
            <p className="text-xs text-muted-foreground">
              Weekly comparison of AI-assessed stage and forecast vs Salesforce values
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={trend} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="week" className="text-xs" />
                <YAxis yAxisId="left" className="text-xs" label={{ value: 'Deals with Gap', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' } }} />
                <YAxis yAxisId="right" orientation="right" domain={[0, 100]} className="text-xs" label={{ value: 'Alignment %', angle: 90, position: 'insideRight', style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' } }} />
                <Tooltip content={<AlignmentTooltip />} />
                <Bar yAxisId="left" dataKey="stage_gap_count" stackId="gaps" name="Stage Gaps" fill="#f59e0b" opacity={0.85} isAnimationActive={false} />
                <Bar yAxisId="left" dataKey="forecast_gap_count" stackId="gaps" name="Forecast Gaps" fill="#8b5cf6" opacity={0.85} isAnimationActive={false} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="alignment_pct"
                  name="Alignment %"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#22c55e' }}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="flex items-center justify-center gap-6 mt-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-amber-500 opacity-85" /> Stage Gaps
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm bg-purple-500 opacity-85" /> Forecast Gaps
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-1 rounded bg-green-500" /> Alignment %
              </span>
            </div>
          </CardContent>
        </Card>
      ) : trend.length === 1 ? (
        <Card>
          <CardHeader>
            <CardTitle>Salesforce Alignment Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="py-8 text-center text-muted-foreground">
              Alignment trending starts after 2 weeks of pipeline analysis. One more week of data needed.
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
