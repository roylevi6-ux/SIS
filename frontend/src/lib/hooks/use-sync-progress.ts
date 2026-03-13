import { useEffect, useRef, useState } from 'react';
import type { SyncProgress } from '../api-types';

// SSE connections must bypass Next.js rewrite proxy (which buffers streams).
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_SSE_URL || 'http://localhost:8000';

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

interface UseSyncProgressResult {
  progress: SyncProgress | null;
  isRunning: boolean;
  error: boolean;
}

/**
 * Subscribes to SSE progress events for a sync job.
 *
 * Connects to `GET /api/sse/sync/{jobId}`.
 * Auto-closes the EventSource when the job reaches a terminal status
 * (completed / failed / cancelled).
 */
export function useSyncProgress(jobId: string | null): UseSyncProgressResult {
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) {
      setProgress(null);
      setIsRunning(false);
      setError(false);
      return;
    }

    setIsRunning(true);
    setError(false);

    const es = new EventSource(`${API_BASE}/api/sse/sync/${jobId}`);
    esRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: SyncProgress = JSON.parse(event.data);
        setProgress(data);

        if (TERMINAL_STATUSES.has(data.status)) {
          setIsRunning(false);
          es.close();
          esRef.current = null;
        }
      } catch {
        // Malformed JSON — ignore
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      setIsRunning(false);
      setError(true);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [jobId]);

  return { progress, isRunning, error };
}
