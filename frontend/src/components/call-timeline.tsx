'use client';

import { Phone } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Participant {
  name: string;
  affiliation?: string;
  title?: string;
}

interface CallEntry {
  id: string;
  call_date: string;
  duration_minutes: number | null;
  participants: Participant[] | null;
  call_title: string | null;
  call_topics?: Array<{ name: string; duration: number }> | null;
  analyzed: boolean;
  is_active: boolean;
}

interface CallTimelineProps {
  transcripts: CallEntry[];
}

interface TopicLabel {
  primary: string;
  secondary?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseDate(dateStr: string): Date {
  return new Date(dateStr + 'T12:00:00');
}

function formatShortDate(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatFullDate(d: Date): string {
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDuration(minutes: number | null): string {
  if (!minutes) return '';
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function getExternalNames(participants: Participant[] | null): string {
  if (!participants) return '';
  return participants
    .filter((p) => p.affiliation !== 'Internal')
    .map((p) => {
      const parts = [p.name];
      if (p.title) parts.push(`(${p.title})`);
      return parts.join(' ');
    })
    .join(', ');
}

function getInternalNames(participants: Participant[] | null): string {
  if (!participants) return '';
  return participants
    .filter((p) => p.affiliation === 'Internal')
    .map((p) => p.name)
    .join(', ');
}

/** Fallback: extract a topic word from call title when no AI topics available. */
function extractTopicWordFallback(title: string | null): string | null {
  if (!title) return null;
  const cleaned = title
    .replace(/\/\//g, ' ')
    .replace(/<>/g, ' ')
    .replace(/[–—-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const words = cleaned.split(' ');
  const fillers = new Set([
    'the', 'a', 'an', 'for', 'on', 'in', 'of', 'to', 'up', 'and', 'or',
    'with', 'catch', 'quick', 'progress',
  ]);
  // Last word that's 4+ chars and not filler
  for (let i = words.length - 1; i >= 0; i--) {
    const w = words[i].toLowerCase().replace(/[^a-z]/g, '');
    if (w.length >= 4 && !fillers.has(w)) {
      return w.charAt(0).toUpperCase() + w.slice(1);
    }
  }
  return null;
}

/** Build topic label from AI topics, falling back to title keyword. */
function getTopicLabel(call: CallEntry): TopicLabel | null {
  if (!call.analyzed) return null;

  if (call.call_topics && call.call_topics.length > 0) {
    return {
      primary: call.call_topics[0].name,
      secondary: call.call_topics[1]?.name,
    };
  }

  // Fallback to title keyword
  const fallback = extractTopicWordFallback(call.call_title);
  return fallback ? { primary: fallback } : null;
}

// ---------------------------------------------------------------------------
// Generate adaptive axis tick marks
// ---------------------------------------------------------------------------

const DAY_MS = 86_400_000;

function getAxisTicks(
  sorted: CallEntry[],
  axisStart: number,
  axisRange: number,
): { label: string; pct: number }[] {
  if (sorted.length === 0 || axisRange <= 0) return [];

  const rangeDays = axisRange / DAY_MS;
  let ticks: { label: string; pct: number }[] = [];

  if (rangeDays < 90) {
    // Short range: show each unique call date
    const seen = new Set<string>();
    for (const call of sorted) {
      if (seen.has(call.call_date)) continue;
      seen.add(call.call_date);
      const ms = parseDate(call.call_date).getTime();
      const pct = ((ms - axisStart) / axisRange) * 100;
      ticks.push({ label: formatShortDate(parseDate(call.call_date)), pct });
    }
  } else {
    // Longer range: month boundary ticks
    const start = new Date(axisStart);
    let cursor = new Date(start.getFullYear(), start.getMonth() + 1, 1);
    while (cursor.getTime() <= axisStart + axisRange) {
      const pct = ((cursor.getTime() - axisStart) / axisRange) * 100;
      ticks.push({
        label: cursor.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
        pct,
      });
      cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    }

    // Always add first and last call dates
    const firstMs = parseDate(sorted[0].call_date).getTime();
    const lastMs = parseDate(sorted[sorted.length - 1].call_date).getTime();
    ticks.unshift({
      label: formatShortDate(parseDate(sorted[0].call_date)),
      pct: ((firstMs - axisStart) / axisRange) * 100,
    });
    ticks.push({
      label: formatShortDate(parseDate(sorted[sorted.length - 1].call_date)),
      pct: ((lastMs - axisStart) / axisRange) * 100,
    });
  }

  // Remove ticks that overlap (within 8% of each other), keep first occurrence
  ticks.sort((a, b) => a.pct - b.pct);
  const filtered: typeof ticks = [];
  for (const t of ticks) {
    if (filtered.length === 0 || t.pct - filtered[filtered.length - 1].pct > 8) {
      filtered.push(t);
    }
  }
  return filtered;
}

// ---------------------------------------------------------------------------
// Collision detection
// ---------------------------------------------------------------------------

/** Returns a set of indices where the secondary topic should be suppressed. */
function getDenseIndices(pcts: number[], threshold: number = 10): Set<number> {
  const dense = new Set<number>();
  for (let i = 1; i < pcts.length; i++) {
    if (pcts[i] - pcts[i - 1] < threshold) {
      dense.add(i);
    }
  }
  return dense;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CallTimeline({ transcripts }: CallTimelineProps) {
  if (!transcripts || transcripts.length === 0) return null;

  // Sort chronologically (oldest first for left-to-right)
  const sorted = [...transcripts].sort(
    (a, b) => a.call_date.localeCompare(b.call_date),
  );

  const analyzedCount = sorted.filter((t) => t.analyzed).length;

  // Compute time range with padding
  const dates = sorted.map((t) => parseDate(t.call_date).getTime());
  const minDate = Math.min(...dates);
  const maxDate = Math.max(...dates);
  const range = maxDate - minDate || 1;
  // Add 5% padding on each side
  const padMs = range * 0.05;
  const axisStart = minDate - padMs;
  const axisEnd = maxDate + padMs;
  const axisRange = axisEnd - axisStart;

  const axisTicks = getAxisTicks(sorted, axisStart, axisRange);

  // Precompute pct positions for collision detection
  const pcts = sorted.map((t) => {
    const ms = parseDate(t.call_date).getTime();
    return ((ms - axisStart) / axisRange) * 100;
  });
  const denseIndices = getDenseIndices(pcts);

  // Today marker
  const today = Date.now();
  const todayPct = ((today - axisStart) / axisRange) * 100;
  const showToday = todayPct >= 0 && todayPct <= 100;

  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        {/* Header row */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Phone className="size-4 text-muted-foreground" />
            Call Timeline
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="inline-block size-2.5 rounded-full bg-violet-500" />
              Analyzed ({analyzedCount})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block size-2.5 rounded-full border-2 border-muted-foreground/30" />
              Not analyzed ({sorted.length - analyzedCount})
            </span>
          </div>
        </div>

        {/* Timeline */}
        <TooltipProvider delayDuration={100}>
          <div className="relative h-24">
            {/* Horizontal axis line */}
            <div className="absolute left-0 right-0 top-1/2 -translate-y-px h-px bg-border" />

            {/* Today marker */}
            {showToday && (
              <div
                className="absolute top-0 bottom-0 w-px bg-rose-400/60"
                style={{ left: `${todayPct}%` }}
              >
                <span className="absolute -top-0.5 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-rose-500 whitespace-nowrap">
                  Today
                </span>
              </div>
            )}

            {/* Call dots — labels alternate above/below the line */}
            {sorted.map((call, idx) => {
              const pct = pcts[idx];
              const d = parseDate(call.call_date);
              const labelAbove = idx % 2 === 0;

              // Build topic label
              const topicLabel = getTopicLabel(call);
              // Suppress secondary topic when calls are too close
              const suppressSecondary = denseIndices.has(idx);

              // Build tooltip — topics first, then date, then participants
              const external = getExternalNames(call.participants);
              const internal = getInternalNames(call.participants);

              const tooltipLines: string[] = [];
              if (topicLabel) {
                const topicStr = topicLabel.secondary
                  ? `${topicLabel.primary}, ${topicLabel.secondary}`
                  : topicLabel.primary;
                tooltipLines.push(topicStr);
              } else if (call.call_title) {
                tooltipLines.push(call.call_title);
              }
              tooltipLines.push(formatFullDate(d));
              if (call.duration_minutes) tooltipLines.push(formatDuration(call.duration_minutes));
              if (external) tooltipLines.push(`With: ${external}`);
              if (internal) tooltipLines.push(`Internal: ${internal}`);
              if (call.analyzed) tooltipLines.push('Included in analysis');

              return (
                <Tooltip key={call.id}>
                  <TooltipTrigger asChild>
                    {/* Flex column: label-above → dot → label-below. No absolute positioning on labels. */}
                    <div
                      className="absolute flex flex-col items-center cursor-default"
                      style={{ left: `${pct}%`, top: '50%', transform: 'translate(-50%, -50%)' }}
                    >
                      {/* Label ABOVE */}
                      {labelAbove && topicLabel && (
                        <div className="mb-1 text-center pointer-events-none">
                          <span className="text-[10px] leading-tight font-medium text-foreground/70 whitespace-nowrap">
                            {topicLabel.primary}
                          </span>
                          {topicLabel.secondary && !suppressSecondary && (
                            <>
                              <br />
                              <span className="text-[10px] leading-tight text-muted-foreground whitespace-nowrap">
                                {topicLabel.secondary}
                              </span>
                            </>
                          )}
                        </div>
                      )}

                      {/* Dot */}
                      {call.analyzed ? (
                        <div className="flex items-center justify-center size-7 rounded-full bg-violet-500 shadow-sm shadow-violet-200 dark:shadow-violet-900 transition-transform hover:scale-110">
                          <Phone className="size-3 text-white" />
                        </div>
                      ) : (
                        <div className="size-5 rounded-full border-2 border-muted-foreground/30 bg-transparent transition-transform hover:scale-125 hover:border-muted-foreground/50" />
                      )}

                      {/* Label BELOW */}
                      {!labelAbove && topicLabel && (
                        <div className="mt-1 text-center pointer-events-none">
                          <span className="text-[10px] leading-tight font-medium text-foreground/70 whitespace-nowrap">
                            {topicLabel.primary}
                          </span>
                          {topicLabel.secondary && !suppressSecondary && (
                            <>
                              <br />
                              <span className="text-[10px] leading-tight text-muted-foreground whitespace-nowrap">
                                {topicLabel.secondary}
                              </span>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side={labelAbove ? 'bottom' : 'top'} className="max-w-xs">
                    {tooltipLines.map((line, i) => (
                      <p key={i} className={i === 0 ? 'font-medium' : 'text-muted-foreground'}>
                        {line}
                      </p>
                    ))}
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>

          {/* Date axis labels */}
          <div className="relative h-4 mt-0.5">
            {axisTicks.map((tick, i) => (
              <span
                key={i}
                className="absolute text-[10px] text-muted-foreground -translate-x-1/2 whitespace-nowrap"
                style={{ left: `${tick.pct}%` }}
              >
                {tick.label}
              </span>
            ))}
          </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  );
}
