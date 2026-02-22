'use client';

import { useCalibrationCurrent, useCalibrationPatterns, useCalibrationHistory } from '@/lib/hooks/use-admin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ---------------------------------------------------------------------------
// Config key-value display
// ---------------------------------------------------------------------------

function ConfigDisplay({ config }: { config: Record<string, unknown> }) {
  const entries = Object.entries(config);
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No config data</p>;

  return (
    <div className="divide-y rounded-md border">
      {entries.map(([key, value]) => (
        <div key={key} className="flex items-start gap-4 px-4 py-2 text-sm">
          <span className="w-48 shrink-0 font-mono text-muted-foreground">{key}</span>
          <span className="font-mono break-all">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Patterns cards
// ---------------------------------------------------------------------------

function PatternsSection({ patterns }: { patterns: any }) {
  const byReason: Record<string, number> = patterns?.by_reason ?? {};
  const byDirection: Record<string, number> = patterns?.by_direction ?? {};

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">By Direction</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-1">
          {Object.entries(byDirection).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground capitalize">{k.replace('_', ' ')}</span>
              <span className="font-semibold tabular-nums">{v}</span>
            </div>
          ))}
          {Object.keys(byDirection).length === 0 && (
            <p className="text-sm text-muted-foreground">No data</p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm font-medium">By Reason</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-1">
          {Object.entries(byReason).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span>
              <span className="font-semibold tabular-nums">{v}</span>
            </div>
          ))}
          {Object.keys(byReason).length === 0 && (
            <p className="text-sm text-muted-foreground">No data</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CalibrationPage() {
  const { data: current, isLoading: currentLoading } = useCalibrationCurrent();
  const { data: patterns, isLoading: patternsLoading } = useCalibrationPatterns();
  const { data: history, isLoading: historyLoading } = useCalibrationHistory();

  const historyItems: any[] = history ?? [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Calibration</h1>
        <p className="text-sm text-muted-foreground">Current scoring config and calibration history</p>
      </div>

      {/* Current config */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Current Configuration</h2>
        {currentLoading && (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted" />
            ))}
          </div>
        )}
        {!currentLoading && current && <ConfigDisplay config={current as Record<string, unknown>} />}
        {!currentLoading && !current && (
          <p className="text-sm text-muted-foreground">No calibration config found</p>
        )}
      </section>

      {/* Feedback patterns */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Feedback Patterns</h2>
        {patternsLoading && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="h-32 animate-pulse rounded bg-muted" />
            <div className="h-32 animate-pulse rounded bg-muted" />
          </div>
        )}
        {!patternsLoading && patterns && <PatternsSection patterns={patterns} />}
      </section>

      {/* History table */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Change History</h2>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Previous</TableHead>
                    <TableHead>Changes</TableHead>
                    <TableHead>Items Reviewed</TableHead>
                    <TableHead>Approved By</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {historyLoading && (
                    Array.from({ length: 3 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 6 }).map((_, j) => (
                          <TableCell key={j}>
                            <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                  {!historyLoading && historyItems.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <div className="flex items-center justify-center py-10 text-muted-foreground">
                          No calibration history yet
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  {!historyLoading && historyItems.map((entry: any, i: number) => (
                    <TableRow key={entry.id ?? i}>
                      <TableCell className="text-sm">{formatDate(entry.created_at)}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{entry.config_version}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {entry.previous_version ?? '--'}
                      </TableCell>
                      <TableCell className="max-w-xs text-sm">{entry.changes ?? '--'}</TableCell>
                      <TableCell className="tabular-nums">{entry.feedback_items_reviewed}</TableCell>
                      <TableCell className="text-sm">{entry.approved_by ?? '--'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
