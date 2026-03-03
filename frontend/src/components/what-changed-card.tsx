'use client';

import { useMemo } from 'react';
import { ArrowRight, AlertTriangle, CircleAlert } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAssessmentDelta } from '@/lib/hooks/use-analyses';
import { useCarryForwardActions } from '@/lib/hooks/use-analyses';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DeltaField {
  previous: unknown;
  current: unknown;
  changed: boolean;
  delta?: number;
}

interface RiskItem {
  risk?: string;
  severity?: string;
  text?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getRiskText(item: string | RiskItem): string {
  if (typeof item === 'string') return item;
  return (item.risk || item.text || JSON.stringify(item)) as string;
}

/** Find risks in current that don't appear in previous (fuzzy match). */
function findNewRisks(
  currentRisks: Array<string | RiskItem> | undefined,
  previousRisks: Array<string | RiskItem> | undefined,
): Array<{ text: string; severity?: string }> {
  if (!currentRisks || currentRisks.length === 0) return [];
  if (!previousRisks || previousRisks.length === 0) {
    return currentRisks.map((r) => ({
      text: getRiskText(r),
      severity: typeof r === 'object' ? (r.severity as string | undefined) : undefined,
    }));
  }

  const prevTexts = previousRisks.map((r) => getRiskText(r).toLowerCase());

  return currentRisks
    .filter((r) => {
      const text = getRiskText(r).toLowerCase();
      // Not in previous if no previous text shares 3+ significant words
      return !prevTexts.some((pt) => {
        const wordsA = new Set(text.split(/\s+/).filter((w) => w.length > 3));
        const wordsB = new Set(pt.split(/\s+/).filter((w) => w.length > 3));
        let overlap = 0;
        for (const w of wordsA) {
          if (wordsB.has(w)) overlap++;
        }
        return overlap >= 2;
      });
    })
    .map((r) => ({
      text: getRiskText(r),
      severity: typeof r === 'object' ? (r.severity as string | undefined) : undefined,
    }));
}

// ---------------------------------------------------------------------------
// Metric badge sub-component
// ---------------------------------------------------------------------------

/** Convert 0.0–1.0 decimal to whole-number percentage. */
function toDisplayPercent(val: unknown): number {
  const n = Number(val);
  return Math.round(n <= 1 ? n * 100 : n);
}

function MetricChip({
  label,
  field,
  percent,
}: {
  label: string;
  field: DeltaField | undefined;
  /** When true, convert 0.0–1.0 values to whole-number percentages. */
  percent?: boolean;
}) {
  if (!field || !field.changed) return null;

  const isNumeric = typeof field.delta === 'number';
  const isPositive = isNumeric && (field.delta as number) > 0;

  // Choose color based on metric semantics
  let colorClasses: string;
  if (isNumeric) {
    // For health_score: up = good. For confidence: up = good.
    colorClasses = isPositive
      ? 'bg-brand-500/10 text-brand-400 border-brand-500/20'
      : 'bg-needs-attention-bg text-needs-attention border-red-500/20';
  } else {
    colorClasses =
      'bg-blue-500/10 text-blue-400 border-blue-500/20';
  }

  let valueText: string;
  if (isNumeric && percent) {
    const prev = toDisplayPercent(field.previous);
    const curr = toDisplayPercent(field.current);
    const delta = curr - prev;
    valueText = `${prev}% → ${curr}% (${delta > 0 ? '+' : ''}${delta})`;
  } else if (isNumeric) {
    valueText = `${String(field.previous)} → ${String(field.current)} (${isPositive ? '+' : ''}${field.delta})`;
  } else {
    valueText = `${String(field.previous)} → ${String(field.current)}`;
  }

  return (
    <Badge variant="outline" className={`text-xs font-medium ${colorClasses}`}>
      {label}: {valueText}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function WhatChangedCard({ accountId }: { accountId: string }) {
  const { data: deltaData } = useAssessmentDelta(accountId);
  const { data: carryForward } = useCarryForwardActions(accountId);

  const deltaFields = deltaData?.fields as
    | Record<string, DeltaField>
    | undefined;

  // Don't render if no delta (less than 2 runs)
  if (!deltaFields) return null;

  // Check if anything actually changed
  const changedFields = deltaFields
    ? Object.entries(deltaFields).filter(([, v]) => v.changed)
    : [];
  if (changedFields.length === 0 && (!carryForward || carryForward.length === 0))
    return null;

  // Detect new risks
  const topRisksField = deltaFields?.top_risks as
    | { previous: Array<string | RiskItem>; current: Array<string | RiskItem>; changed: boolean }
    | undefined;
  const newRisks = useMemo(
    () => findNewRisks(topRisksField?.current, topRisksField?.previous),
    [topRisksField],
  );

  // Date range for header
  const currentDate = deltaData?.current_run_id
    ? formatDate(new Date().toISOString())
    : '';
  const previousDate = deltaData?.previous_run_id ? 'prior run' : '';

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <ArrowRight className="size-4 text-blue-500" />
            What Changed
          </CardTitle>
          {currentDate && (
            <span className="text-xs text-muted-foreground">
              {previousDate} → {currentDate}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Metric chips */}
        {changedFields.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <MetricChip label="Health" field={deltaFields?.health_score} />
            <MetricChip label="Stage" field={deltaFields?.stage_name ?? deltaFields?.inferred_stage} />
            <MetricChip label="Forecast" field={deltaFields?.ai_forecast_category} />
            <MetricChip label="Momentum" field={deltaFields?.momentum_direction} />
            <MetricChip label="Confidence" field={deltaFields?.overall_confidence} percent />
          </div>
        )}

        {/* New risks */}
        {newRisks.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-needs-attention mb-2 flex items-center gap-1.5">
              <AlertTriangle className="size-3" />
              New Risks
            </h4>
            <ul className="space-y-1.5">
              {newRisks.map((risk, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 shrink-0 text-red-500">-</span>
                  <span>
                    {risk.text}
                    {risk.severity && (
                      <Badge
                        variant="outline"
                        className="ml-2 text-[10px] py-0 border-red-500/20 text-needs-attention"
                      >
                        {risk.severity}
                      </Badge>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Unfollowed actions */}
        {carryForward && carryForward.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral mb-2 flex items-center gap-1.5">
              <CircleAlert className="size-3" />
              Unfollowed Actions
            </h4>
            <ul className="space-y-1.5">
              {carryForward.map((action, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 shrink-0 text-amber-500">-</span>
                  <span>
                    {action.action}
                    {action.priority && (
                      <Badge
                        variant="outline"
                        className="ml-2 text-[10px] py-0 border-amber-500/20 text-neutral"
                      >
                        {action.priority}
                      </Badge>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
