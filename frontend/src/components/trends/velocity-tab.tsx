'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useVelocity } from '@/lib/hooks/use-trends';
import Link from 'next/link';

export function VelocityTab({ weeks }: { weeks: number }) {
  const { data, isLoading } = useVelocity(weeks);
  if (isLoading) return <div className="py-12 text-center text-muted-foreground">Loading velocity data...</div>;
  if (!data) return <div className="py-12 text-center text-muted-foreground">No velocity data available.</div>;

  const avgCycleTime =
    data.stage_durations.length > 0
      ? Math.round(data.stage_durations.reduce((s, d) => s + d.avg_days, 0) / data.stage_durations.length)
      : 0;
  const bottleneck =
    data.stage_durations.length > 0
      ? data.stage_durations.reduce((max, d) => (d.median_days > max.median_days ? d : max), data.stage_durations[0])
      : null;
  const stalledMrr = data.stalled_deals.reduce((s, d) => s + d.cp_estimate, 0);

  return (
    <div className="space-y-6 mt-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Avg Stage Duration</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{avgCycleTime}d</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Stalled Deals</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{data.stalled_deals.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Stalled MRR</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">${(stalledMrr / 1000).toFixed(0)}K</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Bottleneck Stage</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold truncate">{bottleneck?.stage_name || '--'}</p>
          </CardContent>
        </Card>
      </div>

      {data.stage_durations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Average Days per Stage</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.stage_durations} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="stage_name" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip />
                <Legend />
                <Bar dataKey="avg_days" name="Avg Days" fill="#3b82f6" isAnimationActive={false} />
                <Bar dataKey="median_days" name="Median Days" fill="#94a3b8" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {data.stalled_deals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Stalled Deals</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Deal</TableHead>
                  <TableHead className="text-right">MRR</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead className="text-right">Days</TableHead>
                  <TableHead className="text-right">Median</TableHead>
                  <TableHead>Excess</TableHead>
                  <TableHead className="text-right">Health</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.stalled_deals.map((d) => (
                  <TableRow
                    key={d.account_id}
                    className={d.days_in_stage > d.median_for_stage * 2 ? 'border-l-4 border-l-red-500' : ''}
                  >
                    <TableCell>
                      <Link href={`/deals/${d.account_id}`} className="text-blue-600 hover:underline">
                        {d.account_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right">${(d.cp_estimate / 1000).toFixed(0)}K</TableCell>
                    <TableCell>{d.stage_name}</TableCell>
                    <TableCell className="text-right">{d.days_in_stage}</TableCell>
                    <TableCell className="text-right">{d.median_for_stage}</TableCell>
                    <TableCell className="w-32">
                      <Progress
                        value={Math.min(100, (d.excess_days / d.median_for_stage) * 100)}
                        className="h-2"
                      />
                    </TableCell>
                    <TableCell className="text-right">{d.health_score ?? '--'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {data.stage_events.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Stage Progression Events</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Account</TableHead>
                  <TableHead>From</TableHead>
                  <TableHead></TableHead>
                  <TableHead>To</TableHead>
                  <TableHead>Direction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.stage_events.map((e, idx) => (
                  <TableRow key={`${e.account_id}-${idx}`}>
                    <TableCell className="text-muted-foreground">{e.event_date}</TableCell>
                    <TableCell>{e.account_name}</TableCell>
                    <TableCell>{e.from_stage_name}</TableCell>
                    <TableCell className="text-center">{e.direction === 'advance' ? '→' : '←'}</TableCell>
                    <TableCell>{e.to_stage_name}</TableCell>
                    <TableCell>
                      <Badge variant={e.direction === 'advance' ? 'default' : 'destructive'}>
                        {e.direction === 'advance' ? '↑ Advance' : '↓ Regression'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
