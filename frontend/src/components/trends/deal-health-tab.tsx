'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useDealHealth } from '@/lib/hooks/use-trends';
import { Sparkline } from './sparkline';
import Link from 'next/link';

export function DealHealthTab({ weeks }: { weeks: number }) {
  const { data, isLoading } = useDealHealth(weeks);
  if (isLoading) return <div className="py-12 text-center text-muted-foreground">Loading health data...</div>;
  if (!data || data.distribution_over_time.length === 0) return <div className="py-12 text-center text-muted-foreground">No health data available for this time range.</div>;

  const latest = data.distribution_over_time[data.distribution_over_time.length - 1];

  return (
    <div className="space-y-6 mt-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Weighted Pipeline Health</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{data.weighted_health.current}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Avg Health Score</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {data.biggest_movers.length > 0
                ? Math.round(data.biggest_movers.reduce((s, m) => s + m.current_score, 0) / data.biggest_movers.length)
                : '--'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Deals in Critical</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{latest.critical}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Biggest Mover</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold truncate">{data.biggest_movers[0]?.account_name || '--'}</p>
            <p className="text-sm text-muted-foreground">
              {data.biggest_movers[0] ? `${data.biggest_movers[0].delta > 0 ? '+' : ''}${data.biggest_movers[0].delta}` : ''}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Health Distribution Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Health Distribution Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data.distribution_over_time} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="week" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip />
              <Area type="monotone" dataKey="healthy" stackId="1" fill="#22c55e" stroke="#22c55e" isAnimationActive={false} />
              <Area type="monotone" dataKey="at_risk" stackId="1" fill="#f59e0b" stroke="#f59e0b" isAnimationActive={false} />
              <Area type="monotone" dataKey="critical" stackId="1" fill="#ef4444" stroke="#ef4444" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Biggest Movers Table */}
      <Card>
        <CardHeader>
          <CardTitle>Biggest Movers</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Deal</TableHead>
                <TableHead className="text-right">MRR</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead className="text-right">Delta</TableHead>
                <TableHead>Trend</TableHead>
                <TableHead>Direction</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.biggest_movers.map((m) => (
                <TableRow key={m.account_id}>
                  <TableCell>
                    <Link href={`/deals/${m.account_id}`} className="text-blue-600 hover:underline">
                      {m.account_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right">${(m.cp_estimate / 1000).toFixed(0)}K</TableCell>
                  <TableCell className="text-right">{m.current_score}</TableCell>
                  <TableCell className="text-right">{m.delta > 0 ? '+' : ''}{m.delta}</TableCell>
                  <TableCell><Sparkline data={m.sparkline} /></TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        m.direction === 'Improving'
                          ? 'default'
                          : m.direction === 'Declining'
                          ? 'destructive'
                          : 'secondary'
                      }
                    >
                      {m.direction}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Component Averages */}
      {data.component_averages.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Component Averages</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(200, data.component_averages.length * 40)}>
              <BarChart
                data={data.component_averages}
                layout="vertical"
                margin={{ top: 5, right: 20, bottom: 5, left: 120 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" domain={[0, 100]} className="text-xs" />
                <YAxis type="category" dataKey="component" className="text-xs" width={110} />
                <Tooltip />
                <Bar dataKey="avg_score" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
