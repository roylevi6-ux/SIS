'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useTeamComparison } from '@/lib/hooks/use-trends';

const TEAM_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6'];

export function TeamComparisonTab({ weeks }: { weeks: number }) {
  const { data, isLoading } = useTeamComparison(weeks);
  if (isLoading) return <div className="py-12 text-center text-muted-foreground">Loading team data...</div>;
  if (!data || data.benchmark_table.length === 0) return <div className="py-12 text-center text-muted-foreground">No team data available.</div>;

  const topPipeline = data.benchmark_table[0];
  const healthiest = [...data.benchmark_table].sort((a, b) => (b.avg_health ?? 0) - (a.avg_health ?? 0))[0];
  const mostImproved = [...data.benchmark_table].sort((a, b) => b.improving_count - a.improving_count)[0];
  const needsAttention = [...data.benchmark_table].sort((a, b) => (a.avg_health ?? 100) - (b.avg_health ?? 100))[0];

  // Transform team_pipeline_trend for multi-line chart
  const teamNames = data.benchmark_table.map((t) => t.team_name);
  const trendData = data.team_pipeline_trend.map((point) => ({
    week: point.week,
    ...point.teams,
  }));

  return (
    <div className="space-y-6 mt-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Top Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold truncate">{topPipeline?.team_name}</p>
            <p className="text-sm text-muted-foreground">${((topPipeline?.pipeline_value || 0) / 1000).toFixed(0)}K</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Healthiest</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold truncate">{healthiest?.team_name}</p>
            <p className="text-sm text-muted-foreground">Avg {healthiest?.avg_health}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Most Improved</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold truncate">{mostImproved?.team_name}</p>
            <p className="text-sm text-muted-foreground">{mostImproved?.improving_count} improving</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Needs Attention</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold truncate">{needsAttention?.team_name}</p>
            <p className="text-sm text-muted-foreground">Avg {needsAttention?.avg_health}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Team Pipeline Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="week" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip />
              <Legend />
              {teamNames.map((name, idx) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={TEAM_COLORS[idx % TEAM_COLORS.length]}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Team Benchmarking</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Team</TableHead>
                <TableHead className="text-right">Deals</TableHead>
                <TableHead className="text-right">Pipeline</TableHead>
                <TableHead className="text-right">Avg Health</TableHead>
                <TableHead className="text-right">Improving</TableHead>
                <TableHead className="text-right">Stable</TableHead>
                <TableHead className="text-right">Declining</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.benchmark_table.map((t) => (
                <TableRow key={t.team_name}>
                  <TableCell className="font-medium">{t.team_name}</TableCell>
                  <TableCell className="text-right">{t.total_deals}</TableCell>
                  <TableCell className="text-right">${(t.pipeline_value / 1000).toFixed(0)}K</TableCell>
                  <TableCell className="text-right">{t.avg_health ?? '--'}</TableCell>
                  <TableCell className="text-right text-green-600">{t.improving_count}</TableCell>
                  <TableCell className="text-right">{t.stable_count}</TableCell>
                  <TableCell className="text-right text-red-600">{t.declining_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Team Momentum</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={Math.max(200, data.momentum_distribution.length * 50)}>
            <BarChart
              data={data.momentum_distribution}
              layout="vertical"
              margin={{ top: 5, right: 20, bottom: 5, left: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis type="number" className="text-xs" />
              <YAxis type="category" dataKey="team_name" className="text-xs" width={70} />
              <Tooltip />
              <Legend />
              <Bar dataKey="improving" name="Improving" stackId="a" fill="#22c55e" isAnimationActive={false} />
              <Bar dataKey="stable" name="Stable" stackId="a" fill="#94a3b8" isAnimationActive={false} />
              <Bar dataKey="declining" name="Declining" stackId="a" fill="#ef4444" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
