'use client';

import { AlertTriangle, Zap, HelpCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface KeyMetricsRowProps {
  topRisk: { risk?: string; text?: string; severity?: string } | string | null;
  topAction: { action?: string; text?: string; priority?: string; owner?: string } | string | null;
  keyUnknown: string | null;
}

function getText(item: unknown): string | null {
  if (!item) return null;
  if (typeof item === 'string') return item;
  if (typeof item === 'object') {
    const obj = item as Record<string, unknown>;
    return (obj.risk ?? obj.action ?? obj.text ?? obj.description ?? '') as string;
  }
  return null;
}

export function KeyMetricsRow({ topRisk, topAction, keyUnknown }: KeyMetricsRowProps) {
  const riskText = getText(topRisk);
  const actionText = getText(topAction);
  const actionOwner = typeof topAction === 'object' && topAction
    ? (topAction as Record<string, unknown>).owner as string | undefined
    : undefined;
  const actionPriority = typeof topAction === 'object' && topAction
    ? (topAction as Record<string, unknown>).priority as string | undefined
    : undefined;

  if (!riskText && !actionText && !keyUnknown) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {riskText && (
        <Card className="py-0">
          <CardContent className="pt-3 pb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlertTriangle className="size-3.5 text-red-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">Top Risk</span>
            </div>
            <p className="text-sm leading-snug line-clamp-3">{riskText}</p>
          </CardContent>
        </Card>
      )}
      {actionText && (
        <Card className="py-0">
          <CardContent className="pt-3 pb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Zap className="size-3.5 text-blue-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">Top Action</span>
              {actionPriority && <Badge variant="outline" className="text-[10px] px-1 py-0">{actionPriority}</Badge>}
              {actionOwner && <Badge variant="secondary" className="text-[10px] px-1 py-0">{actionOwner}</Badge>}
            </div>
            <p className="text-sm leading-snug line-clamp-3">{actionText}</p>
          </CardContent>
        </Card>
      )}
      {keyUnknown && (
        <Card className="py-0">
          <CardContent className="pt-3 pb-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <HelpCircle className="size-3.5 text-purple-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">Key Unknown</span>
            </div>
            <p className="text-sm leading-snug line-clamp-3">{keyUnknown}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
