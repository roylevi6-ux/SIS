'use client';

import { Phone, CheckCircle2, Circle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
  analyzed: boolean;
  is_active: boolean;
}

interface CallTimelineProps {
  transcripts: CallEntry[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-US', {
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

function daysAgo(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff === 0) return 'Today';
  if (diff === 1) return '1 day ago';
  if (diff < 7) return `${diff} days ago`;
  if (diff < 30) return `${Math.floor(diff / 7)}w ago`;
  if (diff < 365) return `${Math.floor(diff / 30)}mo ago`;
  return `${Math.floor(diff / 365)}y ago`;
}

function getExternalParticipants(participants: Participant[] | null): Participant[] {
  if (!participants) return [];
  return participants.filter((p) => p.affiliation !== 'Internal');
}

function getInternalParticipants(participants: Participant[] | null): Participant[] {
  if (!participants) return [];
  return participants.filter((p) => p.affiliation === 'Internal');
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CallTimeline({ transcripts }: CallTimelineProps) {
  if (!transcripts || transcripts.length === 0) return null;

  // Sort by call_date descending (most recent first)
  const sorted = [...transcripts].sort(
    (a, b) => b.call_date.localeCompare(a.call_date),
  );

  const analyzedCount = sorted.filter((t) => t.analyzed).length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Phone className="size-4" />
            Call Timeline
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            {analyzedCount} of {sorted.length} analyzed
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="relative">
          {sorted.map((call, i) => {
            const external = getExternalParticipants(call.participants);
            const internal = getInternalParticipants(call.participants);
            const isLast = i === sorted.length - 1;

            return (
              <div key={call.id} className="flex gap-3 group">
                {/* Timeline rail */}
                <div className="flex flex-col items-center">
                  {call.analyzed ? (
                    <CheckCircle2 className="size-4 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="size-4 text-muted-foreground/40 shrink-0 mt-0.5" />
                  )}
                  {!isLast && (
                    <div
                      className={`w-px flex-1 min-h-[16px] ${
                        call.analyzed
                          ? 'bg-emerald-200 dark:bg-emerald-900'
                          : 'bg-border'
                      }`}
                    />
                  )}
                </div>

                {/* Call content */}
                <div
                  className={`flex-1 pb-4 ${
                    call.analyzed ? '' : 'opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium">
                      {formatDate(call.call_date)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {daysAgo(call.call_date)}
                    </span>
                    {call.duration_minutes && (
                      <span className="text-xs text-muted-foreground">
                        · {formatDuration(call.duration_minutes)}
                      </span>
                    )}
                    {call.analyzed && (
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1.5 py-0 h-4 border-emerald-300 text-emerald-700 dark:border-emerald-800 dark:text-emerald-400"
                      >
                        Analyzed
                      </Badge>
                    )}
                    {!call.is_active && (
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1.5 py-0 h-4 opacity-50"
                      >
                        Archived
                      </Badge>
                    )}
                  </div>

                  {/* Participants */}
                  {(external.length > 0 || internal.length > 0) && (
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
                      {external.length > 0 && (
                        <TooltipProvider>
                          <div className="flex items-center gap-1 text-xs">
                            <span className="text-muted-foreground">With:</span>
                            {external.map((p, j) => (
                              <Tooltip key={j}>
                                <TooltipTrigger asChild>
                                  <span className="font-medium cursor-default">
                                    {p.name}{j < external.length - 1 ? ',' : ''}
                                  </span>
                                </TooltipTrigger>
                                {p.title && (
                                  <TooltipContent side="top">
                                    <p>{p.title}</p>
                                  </TooltipContent>
                                )}
                              </Tooltip>
                            ))}
                          </div>
                        </TooltipProvider>
                      )}
                      {internal.length > 0 && (
                        <span className="text-xs text-muted-foreground">
                          Internal: {internal.map((p) => p.name).join(', ')}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
