'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { WaterfallData } from '@/lib/api-types';

interface WaterfallChartProps {
  data: WaterfallData;
}

export function WaterfallChart({ data }: WaterfallChartProps) {
  const items = [
    { name: 'Previous', value: data.previous_total, color: '#94a3b8' },
    { name: 'New Deals', value: data.new_deals, color: '#22c55e' },
    { name: 'Upgrades', value: data.upgrades, color: '#3b82f6' },
    { name: 'Downgrades', value: data.downgrades, color: '#f97316' },
    { name: 'Lost', value: data.lost_deals, color: '#ef4444' },
    { name: 'Current', value: data.current_total, color: '#16a34a' },
  ];

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
    return `$${v.toFixed(0)}`;
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={items} margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="name" className="text-xs" />
        <YAxis tickFormatter={formatValue} className="text-xs" />
        <Tooltip formatter={(v: number | undefined) => (v !== undefined ? formatValue(v) : '--')} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {items.map((item, idx) => (
            <Cell key={idx} fill={item.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
