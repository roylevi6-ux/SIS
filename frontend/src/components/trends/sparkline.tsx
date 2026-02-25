'use client';

import { LineChart, Line, ResponsiveContainer } from 'recharts';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export function Sparkline({ data, width = 80, height = 24, color, className }: SparklineProps) {
  if (!data || data.length === 0) return <span className="text-muted-foreground text-xs">--</span>;

  const chartData = data.map((value, i) => ({ i, v: value }));
  const trend = data[data.length - 1] - data[0];
  const lineColor = color || (trend >= 0 ? 'oklch(0.60 0.18 145)' : 'oklch(0.60 0.20 25)');

  return (
    <div className={className} style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={lineColor}
            strokeWidth={1.5}
            dot={data.length === 1}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
