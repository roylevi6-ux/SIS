'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Clock,
  Minus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AgentProgress {
  status: 'pending' | 'running' | 'completed' | 'failed';
  name: string;
  started_at: string | null;
  elapsed_seconds: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  model: string | null;
  attempts: number | null;
  error: string | null;
}

interface RunProgress {
  run_id: string;
  status: 'running' | 'completed' | 'failed' | 'partial' | 'not_found';
  started_at?: string;
  agents: Record<string, AgentProgress>;
  total_cost_usd: number;
  total_elapsed_seconds: number;
  errors: string[];
}

interface AnalysisProgressDetailProps {
  runId: string;
  accountId: string;
  onComplete?: (status: RunProgress) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

const AGENT_ORDER = [
  'agent_1', 'agent_2', 'agent_3', 'agent_4', 'agent_5',
  'agent_6', 'agent_7', 'agent_8', 'agent_9', 'agent_10',
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AnalysisProgressDetail({
  runId,
  accountId,
  onComplete,
}: AnalysisProgressDetailProps) {
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [connectionError, setConnectionError] = useState(false);
  const [wallClock, setWallClock] = useState(0);
  const startTimeRef = useRef(Date.now());
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const isTerminal =
    progress?.status === 'completed' ||
    progress?.status === 'failed' ||
    progress?.status === 'partial';

  // -- SSE connection -------------------------------------------------------
  useEffect(() => {
    if (!runId) return;

    const es = new EventSource(`${API_BASE}/api/sse/analysis/${runId}`);

    es.onmessage = (event) => {
      try {
        const data: RunProgress = JSON.parse(event.data);
        setProgress(data);

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
      setConnectionError(true);
    };

    return () => {
      es.close();
    };
  }, [runId]);

  // -- Wall clock timer -----------------------------------------------------
  useEffect(() => {
    if (isTerminal || connectionError) return;

    startTimeRef.current = Date.now();
    setWallClock(0);

    const interval = setInterval(() => {
      setWallClock(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isTerminal, connectionError]);

  // -- Derived data ---------------------------------------------------------
  const agents = progress?.agents ?? {};
  const agentEntries = AGENT_ORDER
    .map((id) => ({ id, ...(agents[id] || { status: 'pending', name: id }) }))
    .filter((a) => a.name);
  const completedCount = agentEntries.filter(
    (a) => a.status === 'completed' || a.status === 'failed'
  ).length;
  const progressPct = (completedCount / 10) * 100;

  // -- Connection error -----------------------------------------------------
  if (connectionError && !progress) {
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

  // -- Main render ----------------------------------------------------------
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {isTerminal ? 'Analysis Complete' : 'Running Analysis...'}
          </CardTitle>
          <span className="text-xs text-muted-foreground tabular-nums">
            {isTerminal
              ? formatElapsed(progress?.total_elapsed_seconds ?? 0)
              : formatElapsed(wallClock)}
          </span>
        </div>
        <Progress value={progressPct} className="h-2 mt-2" />
        <p className="text-xs text-muted-foreground mt-1">
          {completedCount}/10 agents {isTerminal ? 'finished' : 'complete'}
        </p>
      </CardHeader>

      <CardContent className="space-y-1 pt-0">
        {/* Agent rows */}
        <div className="divide-y divide-border/50">
          {agentEntries.map((agent) => (
            <div
              key={agent.id}
              className="flex items-center gap-3 py-2 text-sm"
            >
              {/* Status icon */}
              <div className="w-5 shrink-0 flex justify-center">
                {agent.status === 'completed' && (
                  <CheckCircle2 className="size-4 text-emerald-500" />
                )}
                {agent.status === 'running' && (
                  <Loader2 className="size-4 animate-spin text-primary" />
                )}
                {agent.status === 'failed' && (
                  <XCircle className="size-4 text-destructive" />
                )}
                {agent.status === 'pending' && (
                  <Minus className="size-4 text-muted-foreground/40" />
                )}
              </div>

              {/* Agent name */}
              <span
                className={`flex-1 ${
                  agent.status === 'pending'
                    ? 'text-muted-foreground/60'
                    : agent.status === 'running'
                    ? 'font-medium'
                    : ''
                }`}
              >
                {agent.name}
              </span>

              {/* Elapsed */}
              <span className="w-14 text-right text-xs text-muted-foreground tabular-nums">
                {agent.elapsed_seconds != null
                  ? formatElapsed(agent.elapsed_seconds)
                  : agent.status === 'running'
                  ? '...'
                  : ''}
              </span>

              {/* Tokens */}
              <span className="w-20 text-right text-xs text-muted-foreground tabular-nums">
                {agent.input_tokens != null && agent.output_tokens != null
                  ? `${formatTokens(agent.input_tokens)}/${formatTokens(agent.output_tokens)}`
                  : ''}
              </span>

              {/* Cost */}
              <span className="w-16 text-right text-xs text-muted-foreground tabular-nums">
                {agent.cost_usd != null ? formatCost(agent.cost_usd) : ''}
              </span>
            </div>
          ))}
        </div>

        {/* Totals footer */}
        {progress && (completedCount > 0) && (
          <div className="flex items-center gap-3 pt-3 mt-2 border-t border-border text-sm font-medium">
            <div className="w-5 shrink-0" />
            <span className="flex-1">Total</span>
            <span className="w-14 text-right text-xs tabular-nums">
              {formatElapsed(progress.total_elapsed_seconds)}
            </span>
            <span className="w-20 text-right text-xs tabular-nums" />
            <span className="w-16 text-right text-xs tabular-nums">
              {formatCost(progress.total_cost_usd)}
            </span>
          </div>
        )}

        {/* Terminal states */}
        {progress?.status === 'completed' && (
          <div className="flex items-center justify-between pt-4 mt-2 border-t border-emerald-200 dark:border-emerald-900">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-emerald-500" />
              <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
                Analysis complete — {formatCost(progress.total_cost_usd)} total
              </span>
            </div>
            <Button asChild size="sm">
              <Link href={`/deals/${accountId}`}>View Deal Detail</Link>
            </Button>
          </div>
        )}

        {progress?.status === 'partial' && (
          <div className="flex items-center justify-between pt-4 mt-2 border-t border-amber-200 dark:border-amber-900">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-amber-500" />
              <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
                Partial results — some agents failed
              </span>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link href={`/deals/${accountId}`}>View Results</Link>
            </Button>
          </div>
        )}

        {progress?.status === 'failed' && (
          <div className="pt-4 mt-2 border-t border-destructive/30">
            <div className="flex items-center gap-2">
              <XCircle className="size-4 text-destructive" />
              <span className="text-sm font-medium text-destructive">
                Analysis failed
              </span>
            </div>
            {progress.errors.length > 0 && (
              <ul className="mt-2 space-y-1">
                {progress.errors.map((err, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    {err}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
