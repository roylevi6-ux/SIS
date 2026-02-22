'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { useAccounts, useRunAnalysis } from '@/lib/hooks';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Account {
  id: string;
  account_name: string;
  [key: string]: unknown;
}

interface AnalysisRun {
  id: string;
  account_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  [key: string]: unknown;
}

type TerminalStatus = 'completed' | 'failed' | 'partial';

const TERMINAL_STATUSES: TerminalStatus[] = ['completed', 'failed', 'partial'];
const POLL_INTERVAL_MS = 2000;

// ---------------------------------------------------------------------------
// Elapsed time helper
// ---------------------------------------------------------------------------

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

// ---------------------------------------------------------------------------
// Polling progress component (used until we have SSE run_id support)
// ---------------------------------------------------------------------------

function PollingProgress({
  accountId,
  onComplete,
}: {
  accountId: string;
  onComplete?: (run: AnalysisRun) => void;
}) {
  const [latestRun, setLatestRun] = useState<AnalysisRun | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [pollError, setPollError] = useState(false);
  const startTimeRef = useRef(Date.now());
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const isTerminal = latestRun
    ? TERMINAL_STATUSES.includes(latestRun.status as TerminalStatus)
    : false;

  // -- Polling loop ---------------------------------------------------------
  useEffect(() => {
    if (!accountId) return;

    startTimeRef.current = Date.now();
    let cancelled = false;

    const poll = async () => {
      try {
        const history = await api.analyses.history(accountId);
        if (cancelled) return;

        if (Array.isArray(history) && history.length > 0) {
          const latest = history[0] as AnalysisRun;
          setLatestRun(latest);
          setPollError(false);

          if (TERMINAL_STATUSES.includes(latest.status as TerminalStatus)) {
            onCompleteRef.current?.(latest);
            return; // stop polling
          }
        }
      } catch {
        if (!cancelled) setPollError(true);
      }

      if (!cancelled) {
        setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    // Start first poll after a short delay to give backend time to create the run
    const initialDelay = setTimeout(poll, 1000);

    return () => {
      cancelled = true;
      clearTimeout(initialDelay);
    };
  }, [accountId]);

  // -- Elapsed timer --------------------------------------------------------
  useEffect(() => {
    if (isTerminal || pollError) return;

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isTerminal, pollError]);

  // -- Render ---------------------------------------------------------------

  if (pollError && !latestRun) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex items-center gap-3 py-6">
          <XCircle className="size-5 text-destructive shrink-0" />
          <div>
            <p className="text-sm font-medium">Failed to check progress</p>
            <p className="text-xs text-muted-foreground">
              Could not reach the server. The analysis may still be running.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (latestRun?.status === 'completed') {
    return (
      <Card className="border-emerald-300 dark:border-emerald-800">
        <CardContent className="flex items-center justify-between gap-3 py-6">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <p className="text-sm font-medium">Analysis complete!</p>
          </div>
          <Button asChild size="sm">
            <Link href={`/deals/${accountId}`}>View Results</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (latestRun?.status === 'failed') {
    return (
      <Card className="border-destructive">
        <CardContent className="flex items-center gap-3 py-6">
          <XCircle className="size-5 text-destructive shrink-0" />
          <div>
            <p className="text-sm font-medium">Analysis failed</p>
            <p className="text-xs text-muted-foreground">
              The pipeline encountered an error. Check logs or try again.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (latestRun?.status === 'partial') {
    return (
      <Card className="border-amber-300 dark:border-amber-800">
        <CardContent className="flex items-center justify-between gap-3 py-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="size-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-medium">Analysis partially complete</p>
              <p className="text-xs text-muted-foreground">
                Some agents failed but results are available.
              </p>
            </div>
          </div>
          <Button asChild size="sm" variant="outline">
            <Link href={`/deals/${accountId}`}>View Results</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Running (default)
  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-6">
        <Loader2 className="size-5 animate-spin text-primary shrink-0" />
        <div>
          <p className="text-sm font-medium">Running analysis...</p>
          <p className="text-xs text-muted-foreground tabular-nums">
            Elapsed: {formatElapsed(elapsed)}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AnalyzePage() {
  const { data: accountsData, isLoading: accountsLoading } = useAccounts();
  const accounts = (accountsData ?? []) as Account[];
  const runAnalysis = useRunAnalysis();

  const [accountId, setAccountId] = useState('');
  const [tracking, setTracking] = useState(false);

  function handleRunAnalysis() {
    if (!accountId) return;

    setTracking(false);
    runAnalysis.mutate(accountId, {
      onSuccess: () => {
        // Analysis started -- begin polling for progress
        setTracking(true);
      },
    });
  }

  function handleReset() {
    setTracking(false);
    runAnalysis.reset();
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight mb-1">Run Analysis</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Run the 10-agent analysis pipeline on an account.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Select Account</CardTitle>
          <CardDescription>
            Choose an account to analyze. The pipeline will process all active
            transcripts.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Account selector */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="analyze-account">
              Account
            </label>
            <Select
              value={accountId}
              onValueChange={(v) => {
                setAccountId(v);
                handleReset();
              }}
              disabled={accountsLoading}
            >
              <SelectTrigger id="analyze-account" className="w-full">
                <SelectValue
                  placeholder={
                    accountsLoading ? 'Loading accounts...' : 'Select an account'
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.account_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Run button */}
          <Button
            onClick={handleRunAnalysis}
            disabled={!accountId || runAnalysis.isPending || tracking}
            className="w-full sm:w-auto"
          >
            {runAnalysis.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="size-4" />
                Run Analysis
              </>
            )}
          </Button>

          {/* Error from mutation */}
          {runAnalysis.isError && (
            <div className="rounded-md border border-destructive bg-destructive/5 p-3">
              <p className="text-sm text-destructive">
                {runAnalysis.error instanceof Error
                  ? runAnalysis.error.message
                  : 'Failed to start analysis. Please try again.'}
              </p>
            </div>
          )}

          {/* Polling progress tracker */}
          {tracking && accountId && (
            <div className="pt-2">
              <PollingProgress
                accountId={accountId}
                onComplete={() => {
                  // Polling stops automatically on terminal status
                }}
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
