'use client';

import { useState } from 'react';
import { useActionLogs, useActionSummary } from '@/lib/hooks/use-admin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(ts: string | null): string {
  if (!ts) return '--';
  return new Date(ts).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------

function SummaryCards({ summary }: { summary: any }) {
  const total: number = summary?.total ?? 0;
  const byType: Record<string, number> = summary?.by_type ?? {};
  const byUser: Record<string, number> = summary?.by_user ?? {};
  const topType = Object.entries(byType).sort(([, a], [, b]) => b - a)[0];
  const topUser = Object.entries(byUser).sort(([, a], [, b]) => b - a)[0];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <Card>
        <CardHeader className="pb-1 pt-4 px-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Total Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 px-4">
          <span className="text-2xl font-bold tabular-nums">{total.toLocaleString()}</span>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-1 pt-4 px-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Top Action Type
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 px-4">
          <span className="text-base font-semibold">{topType ? topType[0] : '--'}</span>
          {topType && <p className="text-xs text-muted-foreground">{topType[1]} times</p>}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-1 pt-4 px-4">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Most Active User
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4 px-4">
          <span className="text-base font-semibold">{topUser ? topUser[0] : '--'}</span>
          {topUser && <p className="text-xs text-muted-foreground">{topUser[1]} actions</p>}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const DAY_OPTIONS = [
  { label: 'Last 7 days', value: 7 },
  { label: 'Last 14 days', value: 14 },
  { label: 'Last 30 days', value: 30 },
];

export default function ActivityLogPage() {
  const [days, setDays] = useState(30);
  const [actionType, setActionType] = useState('');
  const [userName, setUserName] = useState('');

  const { data: summary, isLoading: summaryLoading } = useActionSummary(days);
  const { data: rawLogs, isLoading, isError, error } = useActionLogs({
    days,
    action_type: actionType || undefined,
    user_name: userName || undefined,
  });

  const logs: any[] = rawLogs ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Activity Log</h1>
          <p className="text-sm text-muted-foreground">User actions and system events</p>
        </div>
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DAY_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={String(o.value)}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Summary */}
      {!summaryLoading && summary && <SummaryCards summary={summary} />}

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          placeholder="Filter by action type..."
          value={actionType}
          onChange={(e) => setActionType(e.target.value)}
          className="sm:w-[200px]"
        />
        <Input
          placeholder="Filter by user..."
          value={userName}
          onChange={(e) => setUserName(e.target.value)}
          className="sm:w-[200px]"
        />
      </div>

      {/* Error */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load activity log</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      {!isError && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Action Type</TableHead>
                    <TableHead>Detail</TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead>Page</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading && (
                    Array.from({ length: 8 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 6 }).map((_, j) => (
                          <TableCell key={j}>
                            <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                  {!isLoading && logs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <div className="flex items-center justify-center py-10 text-muted-foreground">
                          No activity found
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  {!isLoading && logs.map((log: any, i: number) => (
                    <TableRow key={log.id ?? i}>
                      <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                        {formatTimestamp(log.timestamp ?? log.created_at)}
                      </TableCell>
                      <TableCell className="text-sm font-medium">{log.user_name ?? '--'}</TableCell>
                      <TableCell className="font-mono text-xs">{log.action_type ?? '--'}</TableCell>
                      <TableCell className="max-w-[200px] text-sm text-muted-foreground truncate">
                        {log.detail ?? '--'}
                      </TableCell>
                      <TableCell className="text-sm">{log.account_name ?? log.account_id ?? '--'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{log.page ?? '--'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
