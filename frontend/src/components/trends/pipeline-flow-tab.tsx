'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { usePipelineFlow } from '@/lib/hooks/use-trends';
import { WaterfallChart } from './waterfall-chart';

export function PipelineFlowTab({ weeks }: { weeks: number }) {
  const { data, isLoading } = usePipelineFlow(weeks);
  if (isLoading) return <div className="py-12 text-center text-muted-foreground">Loading pipeline data...</div>;
  if (!data) return <div className="py-12 text-center text-muted-foreground">No pipeline data available.</div>;

  const latestCoverage = data.coverage_trend[data.coverage_trend.length - 1];
  const latestCategory = data.pipeline_by_category[data.pipeline_by_category.length - 1];
  const totalPipeline = latestCategory
    ? latestCategory.commit + latestCategory.realistic + latestCategory.upside + latestCategory.risk
    : 0;

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
    return `$${v.toFixed(0)}`;
  };

  return (
    <div className="space-y-6 mt-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatValue(totalPipeline)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Net Change</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {data.waterfall ? formatValue(data.waterfall.current_total - data.waterfall.previous_total) : '--'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Coverage Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {latestCoverage?.coverage_ratio ? `${latestCoverage.coverage_ratio}x` : '--'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Active Deals</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {latestCategory ? data.pipeline_by_category.length : '--'}
            </p>
          </CardContent>
        </Card>
      </div>

      {data.waterfall && (
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Waterfall</CardTitle>
          </CardHeader>
          <CardContent>
            <WaterfallChart data={data.waterfall} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Coverage Ratio Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.coverage_trend} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="week" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip />
              <ReferenceLine y={1} stroke="#ef4444" strokeDasharray="5 5" label="1x" />
              <ReferenceLine y={3} stroke="#22c55e" strokeDasharray="5 5" label="3x" />
              <Line
                type="monotone"
                dataKey="coverage_ratio"
                stroke="#3b82f6"
                strokeWidth={2}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline by Forecast Category</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data.pipeline_by_category} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="week" className="text-xs" />
              <YAxis tickFormatter={formatValue} className="text-xs" />
              <Tooltip formatter={(v) => formatValue(v as number)} />
              <Area type="monotone" dataKey="commit" stackId="1" fill="#22c55e" stroke="#22c55e" isAnimationActive={false} />
              <Area type="monotone" dataKey="realistic" stackId="1" fill="#3b82f6" stroke="#3b82f6" isAnimationActive={false} />
              <Area type="monotone" dataKey="upside" stackId="1" fill="#f59e0b" stroke="#f59e0b" isAnimationActive={false} />
              <Area type="monotone" dataKey="risk" stackId="1" fill="#ef4444" stroke="#ef4444" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
