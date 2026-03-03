'use client';

/**
 * Inline delta badge showing change between two assessment runs.
 *
 * Numeric: "72 → 78 (+6)" in green/red
 * Categorical: "Discovery → Validation" in blue
 */

interface DeltaFieldData {
  previous: unknown;
  current: unknown;
  changed: boolean;
  delta?: number;
}

export function DeltaBadge({ field }: { field: DeltaFieldData | undefined }) {
  if (!field || !field.changed) return null;

  // Numeric delta (health score, confidence)
  if (typeof field.delta === 'number') {
    const prev = Number(field.previous);
    const curr = Number(field.current);

    // Values in 0-1 range are percentages stored as decimals (e.g. confidence 0.82)
    const isDecimal = Math.abs(prev) <= 1 && Math.abs(curr) <= 1 && prev !== 0;
    const displayPrev = isDecimal ? Math.round(prev * 100) : prev;
    const displayCurr = isDecimal ? Math.round(curr * 100) : curr;
    const displayDelta = isDecimal ? Math.round(field.delta * 100) : Math.round(field.delta);

    const sign = displayDelta > 0 ? '+' : '';
    const color = displayDelta > 0
      ? 'text-brand-400'
      : 'text-needs-attention';

    return (
      <span className={`text-xs font-medium ${color}`}>
        {displayPrev} → {displayCurr} ({sign}{displayDelta})
      </span>
    );
  }

  // Categorical delta (stage, forecast, momentum)
  return (
    <span className="text-xs font-medium text-blue-400">
      {String(field.previous)} → {String(field.current)}
    </span>
  );
}
