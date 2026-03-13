'use client';

import { useEffect, useRef } from 'react';
import { CheckCircle2, XCircle, Loader2, X, Clock } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useSyncProgress } from '@/lib/hooks/use-sync-progress';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SyncProgressModalProps {
  jobId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(value: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((value / total) * 100);
}

function formatSeconds(s: number): string {
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

// ---------------------------------------------------------------------------
// Account status row
// ---------------------------------------------------------------------------

function AccountStatusRow({
  name,
  n8nStatus,
  importStatus,
  callsImported,
}: {
  name: string;
  n8nStatus: string;
  importStatus: string;
  callsImported: number;
}) {
  const isDone = n8nStatus === 'success' || importStatus === 'done';
  const isFailed = n8nStatus === 'failed' || importStatus === 'failed';
  const isActive = n8nStatus === 'running' || importStatus === 'running';

  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="shrink-0">
        {isFailed ? (
          <XCircle className="size-4 text-destructive" />
        ) : isDone ? (
          <CheckCircle2 className="size-4 text-healthy" />
        ) : isActive ? (
          <Loader2 className="size-4 animate-spin text-primary" />
        ) : (
          <div className="size-4 rounded-full border border-border" />
        )}
      </div>
      <span className="flex-1 min-w-0 truncate text-sm text-foreground whitespace-normal">
        {name}
      </span>
      {callsImported > 0 && (
        <span className="shrink-0 text-xs text-muted-foreground font-mono">
          +{callsImported}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: N8N Extraction
// ---------------------------------------------------------------------------

function N8nPhase({
  completed,
  total,
  currentAccount,
}: {
  completed: number;
  total: number;
  currentAccount: string | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Extracting from Gong</span>
        <span className="font-mono text-foreground">
          {completed}/{total}
        </span>
      </div>
      <Progress value={pct(completed, total)} className="h-1.5" />
      {currentAccount && (
        <p className="text-xs text-muted-foreground truncate">
          Processing: {currentAccount}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: Drive Wait
// ---------------------------------------------------------------------------

function DriveWaitPhase({
  elapsed,
  max,
  fileCount,
  stableChecks,
  neededChecks,
  status,
}: {
  elapsed: number;
  max: number;
  fileCount: number;
  stableChecks: number;
  neededChecks: number;
  status: string;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Waiting for Drive sync</span>
        <span className="font-mono text-foreground flex items-center gap-1">
          <Clock className="size-3" />
          {formatSeconds(elapsed)} / {formatSeconds(max)}
        </span>
      </div>
      <Progress value={pct(elapsed, max)} className="h-1.5" />
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>{fileCount} files found</span>
        <span>Stable: {stableChecks}/{neededChecks}</span>
        <span className="capitalize">{status}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase: Import
// ---------------------------------------------------------------------------

function ImportPhase({
  completed,
  total,
}: {
  completed: number;
  total: number;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Importing transcripts</span>
        <span className="font-mono text-foreground">
          {completed}/{total}
        </span>
      </div>
      <Progress value={pct(completed, total)} className="h-1.5" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------

export function SyncProgressModal({
  jobId,
  open,
  onOpenChange,
  onComplete,
}: SyncProgressModalProps) {
  const { progress, isRunning, error } = useSyncProgress(open ? jobId : null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;
  const notifiedRef = useRef(false);

  const isTerminal =
    progress?.status === 'completed' ||
    progress?.status === 'failed' ||
    progress?.status === 'cancelled';

  // Notify parent once when job reaches a terminal state
  useEffect(() => {
    if (isTerminal && !notifiedRef.current) {
      notifiedRef.current = true;
      onCompleteRef.current?.();
    }
    // Reset notified flag when job changes
    if (!isTerminal) {
      notifiedRef.current = false;
    }
  }, [isTerminal]);

  async function handleCancel() {
    if (!jobId) return;
    try {
      await api.sync.cancel(jobId);
    } catch {
      // ignore
    }
  }

  const totalAccounts = progress?.total_accounts ?? 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg bg-card border-border"
        showCloseButton={false}
      >
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-base font-semibold">
              {isTerminal
                ? progress?.status === 'completed'
                  ? 'Sync complete'
                  : progress?.status === 'cancelled'
                    ? 'Sync cancelled'
                    : 'Sync failed'
                : `Syncing ${totalAccounts} account${totalAccounts !== 1 ? 's' : ''}`}
            </DialogTitle>
            <div className="flex items-center gap-2">
              {isRunning && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCancel}
                  className="text-muted-foreground hover:text-foreground h-8 px-2 text-xs"
                >
                  Cancel
                </Button>
              )}
              {isTerminal && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onOpenChange(false)}
                  className="size-8 text-muted-foreground hover:text-foreground"
                  aria-label="Close"
                >
                  <X className="size-4" />
                </Button>
              )}
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-5">
          {/* Connection error */}
          {error && !progress && (
            <div className="flex items-center gap-3 rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3">
              <XCircle className="size-4 text-destructive shrink-0" />
              <p className="text-sm text-destructive">
                Could not connect to sync progress stream.
              </p>
            </div>
          )}

          {/* Phase progress */}
          {progress && (
            <>
              {/* N8N phase */}
              {(progress.phase === 'n8n_extraction' || (progress.n8n_progress?.completed ?? 0) > 0) && progress.n8n_progress && (
                <div className="rounded-lg bg-muted/40 px-4 py-3 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Step 1 — Gong Extraction
                  </p>
                  <N8nPhase
                    completed={progress.n8n_progress.completed}
                    total={progress.n8n_progress.total}
                    currentAccount={progress.n8n_progress.current_account}
                  />
                </div>
              )}

              {/* Drive wait phase */}
              {progress.drive_poll && (
                <div className="rounded-lg bg-muted/40 px-4 py-3 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Step 2 — Drive Sync
                  </p>
                  <DriveWaitPhase
                    elapsed={progress.drive_poll.elapsed_seconds}
                    max={progress.drive_poll.max_seconds}
                    fileCount={progress.drive_poll.file_count}
                    stableChecks={progress.drive_poll.stable_checks}
                    neededChecks={progress.drive_poll.needed_checks}
                    status={progress.drive_poll.status}
                  />
                </div>
              )}

              {/* Import phase */}
              {(progress.phase === 'importing' || (progress.import_progress?.completed ?? 0) > 0) && progress.import_progress && (
                <div className="rounded-lg bg-muted/40 px-4 py-3 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Step 3 — Import
                  </p>
                  <ImportPhase
                    completed={progress.import_progress.completed}
                    total={progress.import_progress.total}
                  />
                </div>
              )}

              {/* Per-account list (collapsed scrollable) */}
              {progress.accounts && Object.keys(progress.accounts).length > 0 && (
                <div className="rounded-lg border border-border bg-background max-h-52 overflow-y-auto">
                  <div className="px-4 py-2 border-b border-border">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Accounts
                    </p>
                  </div>
                  <div className="px-4 py-1 divide-y divide-border/50">
                    {Object.entries(progress.accounts).map(([id, acct]) => (
                      <AccountStatusRow
                        key={id}
                        name={acct.name}
                        n8nStatus={acct.n8n_status}
                        importStatus={acct.import_status}
                        callsImported={acct.calls_imported}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Errors */}
              {(progress.errors?.length ?? 0) > 0 && (
                <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 space-y-1">
                  <p className="text-xs font-semibold text-destructive">Errors</p>
                  {progress.errors.map((err, i) => (
                    <p key={i} className="text-xs text-destructive/80 whitespace-normal">
                      {err}
                    </p>
                  ))}
                </div>
              )}

              {/* Completion summary */}
              {isTerminal && progress.summary && (
                <div className="rounded-lg bg-healthy/10 border border-healthy/20 px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="size-4 text-healthy shrink-0" />
                    <p className="text-sm font-medium text-foreground">Sync complete</p>
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground mt-2">
                    {typeof progress.summary['calls_imported'] === 'number' && (
                      <span>{progress.summary['calls_imported'] as number} calls imported</span>
                    )}
                    {typeof progress.summary['calls_skipped'] === 'number' && (
                      <span>{progress.summary['calls_skipped'] as number} skipped</span>
                    )}
                    {typeof progress.summary['accounts_with_new_data'] === 'number' && (
                      <span>{progress.summary['accounts_with_new_data'] as number} accounts with new data</span>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Waiting for first event */}
          {!progress && !error && (
            <div className="flex items-center gap-3 py-4">
              <Loader2 className="size-4 animate-spin text-primary shrink-0" />
              <p className="text-sm text-muted-foreground">Connecting to sync stream...</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
