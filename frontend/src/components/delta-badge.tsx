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
    const sign = field.delta > 0 ? '+' : '';
    const color = field.delta > 0
      ? 'text-emerald-600 dark:text-emerald-400'
      : 'text-red-600 dark:text-red-400';

    return (
      <span className={`text-xs font-medium ${color}`}>
        {String(field.previous)} → {String(field.current)} ({sign}{field.delta})
      </span>
    );
  }

  // Categorical delta (stage, forecast, momentum)
  return (
    <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
      {String(field.previous)} → {String(field.current)}
    </span>
  );
}
