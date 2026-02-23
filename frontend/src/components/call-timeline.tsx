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

// ---------------------------------------------------------------------------
// Generate month tick marks for the time axis
// ---------------------------------------------------------------------------

function getMonthTicks(startMs: number, endMs: number): { label: string; pct: number }[] {
  const ticks: { label: string; pct: number }[] = [];
  const range = endMs - startMs;
  if (range <= 0) return ticks;

  const start = new Date(startMs);
  // Start from the first day of the month after the start date
  let cursor = new Date(start.getFullYear(), start.getMonth() + 1, 1);

  while (cursor.getTime() <= endMs) {
    const pct = ((cursor.getTime() - startMs) / range) * 100;
    ticks.push({
      label: cursor.toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
      pct,
    });
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
  }
  return ticks;
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

  const monthTicks = getMonthTicks(axisStart, axisEnd);

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
              <span className="inline-block size-2 rounded-full bg-muted-foreground/30" />
              Not analyzed ({sorted.length - analyzedCount})
            </span>
          </div>
        </div>

        {/* Timeline */}
        <TooltipProvider delayDuration={100}>
          <div className="relative h-14">
            {/* Horizontal axis line */}
            <div className="absolute left-0 right-0 top-1/2 -translate-y-px h-px bg-border" />

            {/* Today marker */}
            {showToday && (
              <div
                className="absolute top-0 bottom-0 w-px bg-rose-400/60"
                style={{ left: `${todayPct}%` }}
              >
                <span className="absolute -top-0.5 left-1/2 -translate-x-1/2 text-[9px] font-medium text-rose-500 whitespace-nowrap">
                  Today
                </span>
              </div>
            )}

            {/* Call dots */}
            {sorted.map((call) => {
              const dateMs = parseDate(call.call_date).getTime();
              const pct = ((dateMs - axisStart) / axisRange) * 100;
              const d = parseDate(call.call_date);

              const external = getExternalNames(call.participants);
              const internal = getInternalNames(call.participants);

              const tooltipLines: string[] = [];
              if (call.call_title) tooltipLines.push(call.call_title);
              tooltipLines.push(formatFullDate(d));
              if (call.duration_minutes) tooltipLines.push(formatDuration(call.duration_minutes));
              if (external) tooltipLines.push(`With: ${external}`);
              if (internal) tooltipLines.push(`Internal: ${internal}`);
              if (call.analyzed) tooltipLines.push('Included in analysis');

              // Short label for below the dot (truncate to ~12 chars)
              const shortLabel = call.call_title
                ? call.call_title.length > 14
                  ? call.call_title.slice(0, 12) + '…'
                  : call.call_title
                : null;

              return (
                <Tooltip key={call.id}>
                  <TooltipTrigger asChild>
                    <div
                      className="absolute -translate-x-1/2 cursor-default flex flex-col items-center"
                      style={{ left: `${pct}%`, top: '50%', transform: `translateX(-50%) translateY(-50%)` }}
                    >
                      {call.analyzed ? (
                        /* Analyzed: larger circle with phone icon */
                        <div className="relative flex items-center justify-center size-7 rounded-full bg-violet-500 shadow-sm shadow-violet-200 dark:shadow-violet-900 transition-transform hover:scale-110">
                          <Phone className="size-3 text-white" />
                        </div>
                      ) : (
                        /* Not analyzed: smaller muted dot */
                        <div className="size-3 rounded-full bg-muted-foreground/30 transition-transform hover:scale-125 hover:bg-muted-foreground/50" />
                      )}
                      {shortLabel && (
                        <span className="mt-1 text-[9px] leading-tight text-muted-foreground whitespace-nowrap max-w-[60px] truncate text-center">
                          {shortLabel}
                        </span>
                      )}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
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
            {/* Month ticks */}
            {monthTicks.map((tick, i) => (
              <span
                key={i}
                className="absolute text-[10px] text-muted-foreground -translate-x-1/2 whitespace-nowrap"
                style={{ left: `${tick.pct}%` }}
              >
                {tick.label}
              </span>
            ))}

            {/* First and last date labels if no month ticks */}
            {monthTicks.length === 0 && sorted.length >= 2 && (
              <>
                <span className="absolute left-0 text-[10px] text-muted-foreground whitespace-nowrap">
                  {formatShortDate(parseDate(sorted[0].call_date))}
                </span>
                <span className="absolute right-0 text-[10px] text-muted-foreground whitespace-nowrap">
                  {formatShortDate(parseDate(sorted[sorted.length - 1].call_date))}
                </span>
              </>
            )}
          </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  );
}
