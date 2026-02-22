import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// recommended_actions can be string[] or object[] — handle both
type ActionItem = string | { text?: string; action?: string; description?: string; priority?: string; category?: string; [key: string]: unknown };

interface ActionsListProps {
  actions: ActionItem[] | null | undefined;
}

function getActionText(item: ActionItem): string {
  if (typeof item === 'string') return item;
  return item.text || item.action || item.description || JSON.stringify(item);
}

function getActionMeta(item: ActionItem): { priority?: string; category?: string } | null {
  if (typeof item === 'string') return null;
  const meta: { priority?: string; category?: string } = {};
  if (item.priority) meta.priority = item.priority;
  if (item.category) meta.category = item.category;
  return Object.keys(meta).length > 0 ? meta : null;
}

export function ActionsList({ actions }: ActionsListProps) {
  if (!actions || actions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recommended Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No actions recommended.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recommended Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {actions.map((item, i) => {
            const text = getActionText(item);
            const meta = getActionMeta(item);

            return (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-1 text-muted-foreground shrink-0">
                  {i + 1}.
                </span>
                <div>
                  <p>{text}</p>
                  {meta && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {meta.priority && <span>Priority: {meta.priority}</span>}
                      {meta.priority && meta.category && <span> / </span>}
                      {meta.category && <span>Category: {meta.category}</span>}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
