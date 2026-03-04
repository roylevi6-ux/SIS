'use client';

import { useState } from 'react';
import { useUsageSummary } from '@/lib/hooks/use-admin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------

function SummaryCards({ summary, days }: { summary: any; days: number }) {
  const total: number = summary?.total_events ?? 0;
  const perDay = days > 0 ? (total / days).toFixed(1) : '--';

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <Card>
        <CardHeader className="pb-1 pt-4 px-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Total Events
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 px-4">
          <span className="text-2xl font-bold tabular-nums">{total.toLocaleString()}</span>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-1 pt-4 px-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Avg / Day
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 px-4">
          <span className="text-2xl font-bold tabular-nums">{perDay}</span>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-1 pt-4 px-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Period
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 px-4">
          <span className="text-2xl font-bold tabular-nums">{days}d</span>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Daily chart
// ---------------------------------------------------------------------------

function DailyChart({ byDay }: { byDay: Record<string, number> }) {
  const data = Object.entries(byDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date: date.slice(5), count })); // "MM-DD"

  if (data.length === 0) return <p className="text-sm text-muted-foreground">No daily data</p>;

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm font-medium">Events by Day</CardTitle>
      </CardHeader>
      <CardContent className="px-2 pb-4">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={32} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8, backgroundColor: 'var(--card)', border: '1px solid var(--border)' }}
              labelStyle={{ fontWeight: 600, color: 'var(--foreground)' }}
              itemStyle={{ color: 'var(--muted-foreground)' }}
            />
            <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// By-type table
// ---------------------------------------------------------------------------

function ByTypeTable({ byType }: { byType: Record<string, number> }) {
  const rows = Object.entries(byType).sort(([, a], [, b]) => b - a);

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm font-medium">Events by Type</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Event Type</TableHead>
              <TableHead className="text-right">Count</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={2}>
                  <div className="flex items-center justify-center py-6 text-muted-foreground">
                    No data
                  </div>
                </TableCell>
              </TableRow>
            )}
            {rows.map(([type, count]) => (
              <TableRow key={type}>
                <TableCell className="font-mono text-sm">{type}</TableCell>
                <TableCell className="text-right tabular-nums">{count.toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CostsPage() {
  const [days, setDays] = useState(30);
  const { data: summary, isLoading, isError, error } = useUsageSummary(days);

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cost Monitor</h1>
          <p className="text-sm text-muted-foreground">Usage event tracking and cost overview</p>
        </div>
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="w-full sm:w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="14">Last 14 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load usage data</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
          <div className="h-52 animate-pulse rounded-lg bg-muted" />
        </div>
      )}

      {!isLoading && !isError && summary && (
        <>
          <SummaryCards summary={summary} days={days} />
          {summary.by_day && <DailyChart byDay={summary.by_day} />}
          {summary.by_type && <ByTypeTable byType={summary.by_type} />}
        </>
      )}
    </div>
  );
}
