'use client';

import { useCROMetrics } from '@/lib/hooks/use-admin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, MinusCircle } from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type MetricStatus = 'pass' | 'fail' | 'not_evaluable';

function getStatus(metric: any): MetricStatus {
  if (metric.evaluable === false || metric.status === 'not_evaluable') return 'not_evaluable';
  if (metric.pass === true || metric.status === 'pass') return 'pass';
  return 'fail';
}

function StatusIcon({ status }: { status: MetricStatus }) {
  if (status === 'pass') return <CheckCircle className="h-5 w-5 text-green-600" />;
  if (status === 'fail') return <XCircle className="h-5 w-5 text-red-600" />;
  return <MinusCircle className="h-5 w-5 text-muted-foreground" />;
}

function statusBadge(status: MetricStatus) {
  if (status === 'pass') return <Badge className="bg-green-100 text-green-800 border-green-200">Pass</Badge>;
  if (status === 'fail') return <Badge variant="destructive">Fail</Badge>;
  return <Badge variant="outline">N/A</Badge>;
}

function cardBorderClass(status: MetricStatus): string {
  if (status === 'pass') return 'border-green-500/30 bg-green-500/10';
  if (status === 'fail') return 'border-red-500/30 bg-red-500/10';
  return '';
}

// ---------------------------------------------------------------------------
// Metric card
// ---------------------------------------------------------------------------

function MetricCard({ metric }: { metric: any }) {
  const status = getStatus(metric);
  const name: string = metric.metric_name ?? metric.name ?? 'Metric';
  const target = metric.target ?? metric.threshold ?? null;
  const actual = metric.actual ?? metric.value ?? null;

  return (
    <Card className={cardBorderClass(status)}>
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-semibold leading-snug">{name}</CardTitle>
          <StatusIcon status={status} />
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-3">
        <div className="flex items-center justify-between">
          {statusBadge(status)}
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Target</p>
            <p className="font-semibold tabular-nums">
              {target !== null ? String(target) : '--'}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Actual</p>
            <p className="font-semibold tabular-nums">
              {actual !== null ? String(actual) : '--'}
            </p>
          </div>
        </div>
        {metric.description && (
          <p className="text-xs text-muted-foreground leading-relaxed">{metric.description}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function UsagePage() {
  const { data: rawMetrics, isLoading, isError, error } = useCROMetrics();

  const metrics: any[] = Array.isArray(rawMetrics) ? rawMetrics : [];

  const passCount = metrics.filter((m) => getStatus(m) === 'pass').length;
  const failCount = metrics.filter((m) => getStatus(m) === 'fail').length;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">CRO Metrics</h1>
        <p className="text-sm text-muted-foreground">
          {isLoading
            ? 'Loading metrics...'
            : `${passCount} passing, ${failCount} failing of ${metrics.length} criteria`}
        </p>
      </div>

      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load CRO metrics</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-44 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {metrics.length === 0 ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-muted-foreground py-8">
                  No CRO metrics available yet
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {metrics.map((m: any, i: number) => (
                <MetricCard key={m.metric_name ?? m.name ?? i} metric={m} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
