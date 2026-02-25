'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronRight,
  Upload,
  RotateCcw,
} from 'lucide-react';
import { useBatchProgress } from '@/lib/hooks/use-batch-analysis';
import { AnalysisProgressDetail } from '@/components/analysis-progress-detail';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import type { BatchItem } from '@/lib/api-types';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface BatchProgressViewProps {
  batchId: string;
  onRetryItem?: (item: BatchItem) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

/** A row is expandable if it has a run_id and is either actively analyzing or done. */
function isExpandable(item: BatchItem): boolean {
  return (
    item.run_id != null &&
    (item.status === 'analyzing' || item.status === 'completed')
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface StatusIconProps {
  status: BatchItem['status'];
}

function StatusIcon({ status }: StatusIconProps) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />;
    case 'failed':
      return <XCircle className="size-4 shrink-0 text-destructive" />;
    case 'uploading':
      return (
        <Upload className="size-4 shrink-0 text-blue-500 animate-pulse" />
      );
    case 'analyzing':
      return (
        <Loader2 className="size-4 shrink-0 text-primary animate-spin" />
      );
    case 'queued':
    default:
      return (
        <Clock className="size-4 shrink-0 text-muted-foreground/50" />
      );
  }
}

function statusLabel(status: BatchItem['status']): string {
  switch (status) {
    case 'completed':
      return 'Done';
    case 'failed':
      return 'Failed';
    case 'uploading':
      return 'Uploading...';
    case 'analyzing':
      return 'Analyzing...';
    case 'queued':
    default:
      return 'Queued';
  }
}

// ---------------------------------------------------------------------------
// BatchItemRow
// ---------------------------------------------------------------------------

interface BatchItemRowProps {
  item: BatchItem;
  isExpanded: boolean;
  onToggle: () => void;
  onRetry?: (item: BatchItem) => void;
}

function BatchItemRow({
  item,
  isExpanded,
  onToggle,
  onRetry,
}: BatchItemRowProps) {
  const expandable = isExpandable(item);

  return (
    <>
      {/* Main row */}
      <div
        className={`flex items-center gap-2 px-4 py-3 text-sm transition-colors ${
          expandable
            ? 'cursor-pointer hover:bg-muted/40 select-none'
            : 'cursor-default'
        }`}
        onClick={expandable ? onToggle : undefined}
        role={expandable ? 'button' : undefined}
        aria-expanded={expandable ? isExpanded : undefined}
        tabIndex={expandable ? 0 : undefined}
        onKeyDown={
          expandable
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onToggle();
                }
              }
            : undefined
        }
      >
        {/* Expand chevron — always 16px wide to keep alignment */}
        <div className="w-4 shrink-0 flex justify-center">
          {expandable ? (
            isExpanded ? (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="size-3.5 text-muted-foreground" />
            )
          ) : null}
        </div>

        {/* Status icon */}
        <StatusIcon status={item.status} />

        {/* Account name */}
        <span
          className={`flex-1 min-w-0 truncate font-medium ${
            item.status === 'queued' ? 'text-muted-foreground' : ''
          }`}
        >
          {item.account_name}
        </span>

        {/* Status label */}
        <span
          className={`shrink-0 text-xs tabular-nums ${
            item.status === 'completed'
              ? 'text-emerald-600 dark:text-emerald-400'
              : item.status === 'failed'
              ? 'text-destructive'
              : item.status === 'uploading'
              ? 'text-blue-600 dark:text-blue-400'
              : item.status === 'analyzing'
              ? 'text-primary'
              : 'text-muted-foreground/60'
          }`}
        >
          {statusLabel(item.status)}
        </span>

        {/* Elapsed */}
        <span className="w-14 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
          {item.elapsed_seconds != null
            ? formatElapsed(item.elapsed_seconds)
            : ''}
        </span>

        {/* Cost */}
        <span className="w-16 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
          {item.cost_usd != null ? formatCost(item.cost_usd) : ''}
        </span>

        {/* Action */}
        <div className="w-20 shrink-0 flex justify-end" onClick={(e) => e.stopPropagation()}>
          {item.status === 'completed' && item.account_id ? (
            <Button asChild size="sm" variant="ghost" className="h-7 px-2 text-xs">
              <Link href={`/deals/${item.account_id}`}>
                View &rarr;
              </Link>
            </Button>
          ) : item.status === 'failed' && onRetry ? (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs"
              onClick={() => onRetry(item)}
            >
              <RotateCcw className="size-3 mr-1" />
              Retry
            </Button>
          ) : null}
        </div>
      </div>

      {/* Error message */}
      {item.status === 'failed' && item.error && (
        <div className="px-10 pb-2 text-xs text-destructive">
          {item.error}
        </div>
      )}

      {/* Expanded per-agent detail */}
      {isExpanded && expandable && item.run_id && item.account_id && (
        <div className="px-4 pb-4">
          <AnalysisProgressDetail
            runId={item.run_id}
            accountId={item.account_id}
          />
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function BatchProgressView({
  batchId,
  onRetryItem,
}: BatchProgressViewProps) {
  const { batch, error, isTerminal } = useBatchProgress(batchId);
  const [expandedIndices, setExpandedIndices] = useState<Set<number>>(
    new Set()
  );

  function toggleExpand(index: number) {
    setExpandedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  // -- Loading state ---------------------------------------------------------
  if (!batch) {
    if (error) {
      // Connection error with no data at all
      return (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-6">
            <XCircle className="size-5 text-destructive shrink-0" />
            <div>
              <p className="text-sm font-medium">Connection lost</p>
              <p className="text-xs text-muted-foreground">
                Could not connect to the batch progress stream.
              </p>
            </div>
          </CardContent>
        </Card>
      );
    }

    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-6">
          <Loader2 className="size-5 animate-spin text-muted-foreground shrink-0" />
          <p className="text-sm text-muted-foreground">
            Connecting to batch progress...
          </p>
        </CardContent>
      </Card>
    );
  }

  // -- Derived values -------------------------------------------------------
  const progressPct =
    batch.total_items > 0
      ? (batch.completed_count / batch.total_items) * 100
      : 0;

  const totalElapsed = batch.items.reduce(
    (sum, item) => sum + (item.elapsed_seconds ?? 0),
    0
  );
  const totalCost = batch.items.reduce(
    (sum, item) => sum + (item.cost_usd ?? 0),
    0
  );

  const headerTitle = isTerminal
    ? `Batch Complete — ${batch.completed_count}/${batch.total_items} succeeded`
    : `Batch Analysis — ${batch.completed_count}/${batch.total_items} complete`;

  // -- Main render ----------------------------------------------------------
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-base">{headerTitle}</CardTitle>

          {/* Terminal summary stats */}
          {isTerminal && (
            <div className="flex items-center gap-4 text-xs text-muted-foreground tabular-nums shrink-0">
              {totalElapsed > 0 && (
                <span>{formatElapsed(totalElapsed)}</span>
              )}
              {totalCost > 0 && (
                <span>{formatCost(totalCost)} total</span>
              )}
              {batch.failed_count > 0 && (
                <span className="text-destructive">
                  {batch.failed_count} failed
                </span>
              )}
            </div>
          )}
        </div>

        <Progress value={progressPct} className="h-2 mt-2" />

        <p className="text-xs text-muted-foreground mt-1">
          {batch.completed_count}/{batch.total_items} accounts{' '}
          {isTerminal ? 'finished' : 'complete'}
          {batch.failed_count > 0 && ` · ${batch.failed_count} failed`}
        </p>
      </CardHeader>

      <CardContent className="pt-0 px-0 pb-2">
        {/* Column header */}
        <div className="flex items-center gap-2 px-4 py-1.5 text-xs font-medium text-muted-foreground border-b border-border/50">
          <div className="w-4 shrink-0" />
          <div className="w-4 shrink-0" />
          <span className="flex-1">Account</span>
          <span className="shrink-0">Status</span>
          <span className="w-14 shrink-0 text-right">Time</span>
          <span className="w-16 shrink-0 text-right">Cost</span>
          <span className="w-20 shrink-0 text-right">Action</span>
        </div>

        {/* Item rows */}
        <div className="divide-y divide-border/40">
          {batch.items.map((item) => (
            <BatchItemRow
              key={item.index}
              item={item}
              isExpanded={expandedIndices.has(item.index)}
              onToggle={() => toggleExpand(item.index)}
              onRetry={onRetryItem}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
