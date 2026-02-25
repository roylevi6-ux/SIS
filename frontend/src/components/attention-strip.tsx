'use client';

import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react';
import { formatMrr } from '@/lib/format';
import type { AttentionItem } from '@/lib/pipeline-types';

interface AttentionStripProps {
  items: AttentionItem[];
}

function typeIcon(type: string): string {
  switch (type) {
    case 'declining': return '\u2193';
    case 'divergent': return '\u21C4';
    case 'stale': return '\u23F8';
    default: return '\u2022';
  }
}

export function AttentionStrip({ items }: AttentionStripProps) {
  const [expanded, setExpanded] = useState(items.length > 0);

  if (items.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-healthy/30 bg-healthy-light/30 px-4 py-3">
        <CheckCircle className="size-4 text-healthy" />
        <span className="text-sm font-medium text-healthy">All clear — no deals need immediate attention</span>
      </div>
    );
  }

  const totalAtRisk = items.reduce((sum, i) => sum + i.cp_estimate, 0);

  return (
    <div className="rounded-lg border-l-4 border-l-at-risk border bg-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="size-4 text-at-risk" />
          <span className="text-sm font-semibold">
            {items.length} {items.length === 1 ? 'deal needs' : 'deals need'} attention
          </span>
          <span className="text-sm text-muted-foreground">
            ({formatMrr(totalAtRisk)} at risk)
          </span>
        </div>
        {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
      </button>

      {expanded && (
        <div className="border-t divide-y">
          {items.map((item) => (
            <div key={item.account_id} className="flex items-center gap-3 px-4 py-2.5">
              <span className="text-sm">{typeIcon(item.type)}</span>
              <a
                href={`/deals/${item.account_id}`}
                className="text-sm font-medium hover:text-primary hover:underline"
              >
                {item.account_name}
              </a>
              <span className="font-mono text-sm tabular-nums text-muted-foreground">
                {formatMrr(item.cp_estimate)}
              </span>
              <span className="text-xs text-muted-foreground flex-1">
                — {item.reason}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
