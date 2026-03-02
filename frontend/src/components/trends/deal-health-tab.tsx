'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
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
              {data.avg_health_score ?? '--'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Deals Needing Attention</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{latest.needs_attention}</p>
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
              <Area type="monotone" dataKey="neutral" stackId="1" fill="#f59e0b" stroke="#f59e0b" isAnimationActive={false} />
              <Area type="monotone" dataKey="needs_attention" stackId="1" fill="#ef4444" stroke="#ef4444" isAnimationActive={false} />
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
            <div className="space-y-3">
              {[...data.component_averages]
                .sort((a, b) => a.avg_score - b.avg_score)
                .map((c) => (
                  <div key={c.component} className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground w-48 shrink-0 text-right truncate" title={c.component}>
                      {c.component}
                    </span>
                    <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          c.avg_score >= 70
                            ? 'bg-emerald-500'
                            : c.avg_score >= 40
                            ? 'bg-amber-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${c.avg_score}%` }}
                      />
                    </div>
                    <span className={`text-sm font-medium w-8 text-right ${
                      c.avg_score >= 70
                        ? 'text-emerald-600'
                        : c.avg_score >= 40
                        ? 'text-amber-600'
                        : 'text-red-600'
                    }`}>
                      {c.avg_score}
                    </span>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
