'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

type ActionItem = string | {
  action?: string; text?: string; description?: string;
  priority?: string; owner?: string; rationale?: string;
  [key: string]: unknown;
};

interface RepActionPlanProps {
  actions: ActionItem[];
}

function getActionText(item: ActionItem): string {
  if (typeof item === 'string') return item;
  return (item.action ?? item.text ?? item.description ?? JSON.stringify(item)) as string;
}

function getPriority(item: ActionItem): string | null {
  return typeof item === 'object' ? (item.priority as string | null) ?? null : null;
}

const PRIORITY_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2 };

export function RepActionPlan({ actions }: RepActionPlanProps) {
  if (!actions || actions.length === 0) return null;

  const sorted = [...actions].sort((a, b) => {
    const pa = PRIORITY_ORDER[getPriority(a) ?? ''] ?? 99;
    const pb = PRIORITY_ORDER[getPriority(b) ?? ''] ?? 99;
    return pa - pb;
  });

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Rep Action Plan
        </h3>
        <ul className="space-y-1">
          {sorted.map((action, i) => {
            const priority = getPriority(action);
            return (
              <li key={i} className="flex items-start gap-2 text-sm">
                {priority && (
                  <Badge
                    variant="outline"
                    className={`text-[10px] px-1 py-0 shrink-0 mt-0.5 ${
                      priority === 'P0'
                        ? 'bg-orange-500/15 text-orange-400 border-orange-500/30'
                        : priority === 'P1'
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : 'bg-slate-500/15 text-slate-400 border-slate-500/30'
                    }`}
                  >
                    {priority}
                  </Badge>
                )}
                <span className="leading-relaxed">{getActionText(action)}</span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
