'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnalysisStatus {
  run_id: string;
  status: 'running' | 'completed' | 'failed' | 'partial';
  started_at: string;
  completed_at: string | null;
}

interface AnalysisProgressProps {
  /** The run ID to track via SSE. */
  runId: string;
  /** The account ID — used for the "View Results" link. */
  accountId: string;
  /** Called when analysis reaches a terminal state. */
  onComplete?: (status: AnalysisStatus) => void;
}

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
// Component
// ---------------------------------------------------------------------------

// SSE connections must bypass Next.js rewrite proxy (which buffers streams).
const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_SSE_URL || 'http://localhost:8000';

/**
 * Real-time analysis progress via Server-Sent Events.
 *
 * Connects to `GET /api/sse/analysis/{runId}` and displays:
 * - Spinner + elapsed time while running
 * - Green checkmark + "View Results" link on success
 * - Red X + error message on failure
 * - Amber warning for partial completion
 *
 * NOTE: This component requires a valid `runId`. If the API does not return
 * a run_id when starting an analysis, use polling to discover it first,
 * then render this component once you have the ID.
 */
export function AnalysisProgress({
  runId,
  accountId,
  onComplete,
}: AnalysisProgressProps) {
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [error, setError] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef(Date.now());
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const isTerminal =
    status?.status === 'completed' ||
    status?.status === 'failed' ||
    status?.status === 'partial';

  // -- SSE connection -------------------------------------------------------
  useEffect(() => {
    if (!runId) return;

    const es = new EventSource(`${API_BASE}/api/sse/analysis/${runId}`);

    es.onmessage = (event) => {
      try {
        const data: AnalysisStatus = JSON.parse(event.data);
        setStatus(data);

        if (
          data.status === 'completed' ||
          data.status === 'failed' ||
          data.status === 'partial'
        ) {
          es.close();
          onCompleteRef.current?.(data);
        }
      } catch {
        // Malformed JSON — ignore
      }
    };

    es.onerror = () => {
      es.close();
      setError(true);
    };

    return () => {
      es.close();
    };
  }, [runId]);

  // -- Elapsed timer --------------------------------------------------------
  useEffect(() => {
    if (isTerminal || error) return;

    startTimeRef.current = Date.now();
    setElapsed(0);

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isTerminal, error]);

  // -- Render ---------------------------------------------------------------

  // Connection error
  if (error && !status) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex items-center gap-3 py-6">
          <XCircle className="size-5 text-destructive shrink-0" />
          <div>
            <p className="text-sm font-medium">Connection lost</p>
            <p className="text-xs text-muted-foreground">
              Could not connect to the analysis progress stream.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Completed
  if (status?.status === 'completed') {
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

  // Failed
  if (status?.status === 'failed') {
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

  // Partial
  if (status?.status === 'partial') {
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
