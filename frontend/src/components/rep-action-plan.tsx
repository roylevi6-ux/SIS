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

function getOwner(item: ActionItem): string | null {
  return typeof item === 'object' ? (item.owner as string | null) ?? null : null;
}

function getPriority(item: ActionItem): string | null {
  return typeof item === 'object' ? (item.priority as string | null) ?? null : null;
}

const PRIORITY_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2 };
const OWNER_GROUPS = ['AE', 'SE', 'Manager', 'Other'];

export function RepActionPlan({ actions }: RepActionPlanProps) {
  if (!actions || actions.length === 0) return null;

  const sorted = [...actions].sort((a, b) => {
    const pa = PRIORITY_ORDER[getPriority(a) ?? ''] ?? 99;
    const pb = PRIORITY_ORDER[getPriority(b) ?? ''] ?? 99;
    return pa - pb;
  });

  const grouped: Record<string, ActionItem[]> = {};
  for (const action of sorted) {
    const owner = getOwner(action) ?? 'Other';
    const group = OWNER_GROUPS.includes(owner) ? owner : 'Other';
    (grouped[group] ??= []).push(action);
  }

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Rep Action Plan
        </h3>
        {OWNER_GROUPS.filter((g) => grouped[g]?.length).map((group) => (
          <div key={group} className="space-y-1.5">
            <p className="text-xs font-semibold text-muted-foreground">{group}</p>
            <ul className="space-y-1">
              {grouped[group]!.map((action, i) => {
                const priority = getPriority(action);
                return (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    {priority && (
                      <Badge
                        variant={priority === 'P0' ? 'destructive' : 'outline'}
                        className="text-[10px] px-1 py-0 shrink-0 mt-0.5"
                      >
                        {priority}
                      </Badge>
                    )}
                    <span className="leading-relaxed">{getActionText(action)}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
