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

function getTopicStrings(call: CallEntry): string[] {
  if (call.call_topics && call.call_topics.length > 0) {
    return call.call_topics.map((t) => t.name);
  }
  return [];
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
    const seen = new Set<string>();
    for (const call of sorted) {
      if (seen.has(call.call_date)) continue;
      seen.add(call.call_date);
      const ms = parseDate(call.call_date).getTime();
      const pct = ((ms - axisStart) / axisRange) * 100;
      ticks.push({ label: formatShortDate(parseDate(call.call_date)), pct });
    }
  } else {
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
// Component
// ---------------------------------------------------------------------------

export function CallTimeline({ transcripts }: CallTimelineProps) {
  if (!transcripts || transcripts.length === 0) return null;

  const sorted = [...transcripts].sort(
    (a, b) => a.call_date.localeCompare(b.call_date),
  );

  const analyzedCount = sorted.filter((t) => t.analyzed).length;

  const dates = sorted.map((t) => parseDate(t.call_date).getTime());
  const minDate = Math.min(...dates);
  const maxDate = Math.max(...dates);
  const range = maxDate - minDate || 1;
  const padMs = range * 0.05;
  const axisStart = minDate - padMs;
  const axisEnd = maxDate + padMs;
  const axisRange = axisEnd - axisStart;

  const axisTicks = getAxisTicks(sorted, axisStart, axisRange);

  const pcts = sorted.map((t) => {
    const ms = parseDate(t.call_date).getTime();
    return ((ms - axisStart) / axisRange) * 100;
  });

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

        <TooltipProvider delayDuration={100}>
          {/*
            Layout: 3 stacked layers, each positioned independently.
            ┌─────────────────────────────────────────┐
            │  Topic labels ABOVE (odd-indexed calls)  │  h-5  overflow-hidden
            ├─────────────────────────────────────────┤
            │  ●───●───○───●───●───○───●  dots+line  │  h-8  the axis
            ├─────────────────────────────────────────┤
            │  Topic labels BELOW (even-indexed calls) │  h-5  overflow-hidden
            ├─────────────────────────────────────────┤
            │  Date axis labels                        │  h-4
            └─────────────────────────────────────────┘
            Labels alternate above/below so adjacent calls don't overlap horizontally.
          */}

          {/* Topic labels ABOVE the line (odd-indexed calls) */}
          <div className="relative h-5 overflow-hidden">
            {sorted.map((call, idx) => {
              if (idx % 2 === 0) return null; // even = below
              if (!call.analyzed) return null;
              const topics = getTopicStrings(call);
              if (topics.length === 0) return null;
              return (
                <span
                  key={call.id}
                  className="absolute bottom-0 text-[10px] leading-tight font-medium text-foreground/70 whitespace-nowrap -translate-x-1/2 pointer-events-none"
                  style={{ left: `${pcts[idx]}%` }}
                >
                  {topics[0]}
                </span>
              );
            })}
          </div>

          {/* Dot layer — the axis line with dots */}
          <div className="relative h-8">
            {/* Horizontal axis line */}
            <div className="absolute left-0 right-0 top-1/2 -translate-y-px h-px bg-border" />

            {/* Today marker */}
            {showToday && (
              <div
                className="absolute top-0 bottom-0 w-px bg-rose-400/60"
                style={{ left: `${todayPct}%` }}
              >
                <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-rose-500 whitespace-nowrap">
                  Today
                </span>
              </div>
            )}

            {/* Call dots */}
            {sorted.map((call, idx) => {
              const pct = pcts[idx];
              const d = parseDate(call.call_date);
              const topics = getTopicStrings(call);
              const external = getExternalNames(call.participants);
              const internal = getInternalNames(call.participants);

              return (
                <Tooltip key={call.id}>
                  <TooltipTrigger asChild>
                    <div
                      className="absolute top-1/2 cursor-default"
                      style={{ left: `${pct}%`, transform: 'translate(-50%, -50%)' }}
                    >
                      {call.analyzed ? (
                        <div className="flex items-center justify-center size-7 rounded-full bg-violet-500 shadow-sm shadow-violet-200 dark:shadow-violet-900 transition-transform hover:scale-110">
                          <Phone className="size-3 text-white" />
                        </div>
                      ) : (
                        <div className="size-5 rounded-full border-2 border-muted-foreground/30 bg-transparent transition-transform hover:scale-125 hover:border-muted-foreground/50" />
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs text-xs">
                    {topics.length > 0 && (
                      <p className="font-semibold">{topics.join(' · ')}</p>
                    )}
                    {topics.length === 0 && call.call_title && (
                      <p className="font-semibold">{call.call_title}</p>
                    )}
                    <p className="text-muted-foreground">
                      {formatFullDate(d)}
                      {call.duration_minutes ? ` · ${formatDuration(call.duration_minutes)}` : ''}
                    </p>
                    {external && (
                      <p className="text-muted-foreground">With: {external}</p>
                    )}
                    {internal && (
                      <p className="text-muted-foreground">Internal: {internal}</p>
                    )}
                    {call.analyzed && (
                      <p className="text-violet-400 mt-0.5">Included in analysis</p>
                    )}
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>

          {/* Topic labels BELOW the line (even-indexed calls) */}
          <div className="relative h-5 overflow-hidden">
            {sorted.map((call, idx) => {
              if (idx % 2 !== 0) return null; // odd = above
              if (!call.analyzed) return null;
              const topics = getTopicStrings(call);
              if (topics.length === 0) return null;
              return (
                <span
                  key={call.id}
                  className="absolute top-0 text-[10px] leading-tight font-medium text-foreground/70 whitespace-nowrap -translate-x-1/2 pointer-events-none"
                  style={{ left: `${pcts[idx]}%` }}
                >
                  {topics[0]}
                </span>
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
