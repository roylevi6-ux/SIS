'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useForecastMovement } from '@/lib/hooks/use-trends';
import Link from 'next/link';

export function ForecastMovementTab({ weeks }: { weeks: number }) {
  const { data, isLoading } = useForecastMovement(weeks);
  if (isLoading) return <div className="py-12 text-center text-muted-foreground">Loading forecast data...</div>;
  if (!data) return <div className="py-12 text-center text-muted-foreground">No forecast data available.</div>;

  const s = data.migration_summary;
  const latestDivergence =
    data.divergence_trend.length > 0
      ? data.divergence_trend[data.divergence_trend.length - 1].divergence_pct
      : 0;

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
            <CardTitle className="text-sm text-muted-foreground">AI-IC Agreement</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{(100 - latestDivergence).toFixed(0)}%</p>
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
                    <TableCell className="text-center">{m.direction === 'upgrade' ? '↑' : '↓'}</TableCell>
                    <TableCell>{m.current_category}</TableCell>
                    <TableCell className="text-muted-foreground">{m.changed_at}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {data.divergence_trend.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>AI vs IC Divergence Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart data={data.divergence_trend} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="week" className="text-xs" />
                <YAxis yAxisId="left" className="text-xs" />
                <YAxis yAxisId="right" orientation="right" className="text-xs" />
                <Tooltip />
                <Bar yAxisId="left" dataKey="divergent_count" fill="#f59e0b" isAnimationActive={false} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="divergence_pct"
                  stroke="#ef4444"
                  strokeDasharray="5 5"
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
