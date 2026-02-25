'use client';

import { useEffect, useState } from 'react';
import type { BatchAnalysisResponse } from '@/lib/api-types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Terminal statuses that indicate no further SSE events will arrive.
// 'not_found' and 'timeout' are included as forward-compatibility guards
// in case the backend adds them — the current BatchAnalysisResponse type
// covers 'completed' | 'partial' | 'failed'.
const TERMINAL_STATUSES = new Set([
  'completed',
  'failed',
  'partial',
  'not_found',
  'timeout',
]);

/**
 * Hook that connects to the batch SSE endpoint and returns live progress.
 * Automatically closes the EventSource when all items reach a terminal status.
 *
 * @param batchId - The batch ID returned by POST /api/analyses/batch.
 *                  Pass null to keep the hook idle (no connection opened).
 */
export function useBatchProgress(batchId: string | null) {
  const [batch, setBatch] = useState<BatchAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!batchId) return;

    const es = new EventSource(`${API_BASE}/api/sse/batch/${batchId}`);

    es.onmessage = (event) => {
      try {
        const data: BatchAnalysisResponse = JSON.parse(event.data);
        setBatch(data);
        if (TERMINAL_STATUSES.has(data.status as string)) {
          es.close();
        }
      } catch {
        // Malformed JSON — ignore and wait for next event
      }
    };

    es.onerror = () => {
      es.close();
      setError('Connection to batch progress stream lost');
    };

    return () => {
      es.close();
    };
  }, [batchId]);

  const isTerminal =
    batch?.status === 'completed' ||
    batch?.status === 'failed' ||
    batch?.status === 'partial';

  return { batch, error, isTerminal };
}
