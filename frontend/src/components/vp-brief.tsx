'use client';

import { AlertTriangle, Eye } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface VPBriefProps {
  brief: string | null;
  attentionLevel: string | null;
  fallbackMemo?: string | null;
}

function truncateFallback(text: string): string {
  const sentences = text.match(/[^.!?]+[.!?]+/g);
  if (sentences && sentences.length >= 3) return sentences.slice(0, 3).join('').trim();
  return text.slice(0, 500);
}

export function VPBrief({ brief, attentionLevel, fallbackMemo }: VPBriefProps) {
  const level = attentionLevel ?? 'none';
  const text = brief || (fallbackMemo ? truncateFallback(fallbackMemo) : null);

  if (!text) return null;

  const isFallback = !brief && !!fallbackMemo;

  return (
    <Card
      className={cn(
        'transition-colors',
        level === 'act' && 'border-red-500/60 bg-red-50/50 dark:bg-red-950/20',
        level === 'watch' && 'border-amber-400/60 bg-amber-50/50 dark:bg-amber-950/20',
      )}
    >
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-3">
          {level === 'act' && <AlertTriangle className="size-5 text-red-500 shrink-0 mt-0.5" />}
          {level === 'watch' && <Eye className="size-5 text-amber-500 shrink-0 mt-0.5" />}
          <div className="space-y-1.5 min-w-0">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              VP Brief
            </h3>
            <p className="text-sm leading-relaxed">{text}</p>
            {isFallback && (
              <p className="text-xs text-muted-foreground italic">
                Auto-generated summary — re-run analysis for full VP brief
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
