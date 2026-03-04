'use client';

import { useEffect, useRef, useState } from 'react';
import type { BatchAnalysisResponse } from '@/lib/api-types';

// SSE connections must bypass Next.js rewrite proxy (which buffers streams).
// Use the direct backend URL for EventSource connections.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_SSE_URL || 'http://localhost:8000';

// Terminal statuses that indicate no further SSE events will arrive.
const TERMINAL_STATUSES = new Set([
  'completed',
  'failed',
  'partial',
  'not_found',
  'timeout',
]);

const CACHE_KEY = 'sis_batch_snapshot';

/** Read cached batch snapshot from sessionStorage. */
function readCache(batchId: string): BatchAnalysisResponse | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const data: BatchAnalysisResponse = JSON.parse(raw);
    return data.batch_id === batchId ? data : null;
  } catch {
    return null;
  }
}

/** Write batch snapshot to sessionStorage. */
function writeCache(data: BatchAnalysisResponse) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(data));
  } catch {
    // sessionStorage full or unavailable — ignore
  }
}

/** Clear cached batch snapshot from sessionStorage. */
export function clearBatchCache() {
  try {
    sessionStorage.removeItem(CACHE_KEY);
  } catch {
    // ignore
  }
}

/**
 * Hook that connects to the batch SSE endpoint and returns live progress.
 * Initializes from a sessionStorage cache so the UI renders immediately
 * on page return, then SSE updates override as they arrive.
 *
 * @param batchId - The batch ID returned by POST /api/analyses/batch.
 *                  Pass null to keep the hook idle (no connection opened).
 */
export function useBatchProgress(batchId: string | null) {
  const [batch, setBatch] = useState<BatchAnalysisResponse | null>(() => {
    if (typeof window === 'undefined' || !batchId) return null;
    return readCache(batchId);
  });
  const [error, setError] = useState<string | null>(null);
  const retryCountRef = useRef(0);

  useEffect(() => {
    if (!batchId) return;

    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      es = new EventSource(`${API_BASE}/api/sse/batch/${batchId}`);

      es.onmessage = (event) => {
        try {
          const data: BatchAnalysisResponse = JSON.parse(event.data);
          setBatch(data);
          writeCache(data);
          retryCountRef.current = 0; // Success — reset retry counter
          setError(null); // Clear any previous error

          if (TERMINAL_STATUSES.has(data.status as string)) {
            es?.close();
            sessionStorage.setItem('sis_batch_terminal', 'true');
          }
        } catch {
          // Malformed JSON — ignore and wait for next event
        }
      };

      es.onerror = () => {
        es?.close();

        if (retryCountRef.current < 1) {
          // Retry once after 2s (handles transient disconnects like laptop sleep)
          retryCountRef.current += 1;
          retryTimeout = setTimeout(connect, 2000);
        } else {
          setError('Connection to batch progress stream lost');
          // Don't remove sis_batch_id — keep cached state visible.
          // The user can dismiss manually via "Start New Batch".
        }
      };
    }

    connect();

    return () => {
      es?.close();
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [batchId]);

  const isTerminal = batch != null && TERMINAL_STATUSES.has(batch.status as string);

  return { batch, error, isTerminal };
}
