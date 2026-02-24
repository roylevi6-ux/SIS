'use client';

import Link from 'next/link';
import { TrendingDown, TrendingUp, ArrowLeftRight, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useInsights } from '@/lib/hooks/use-dashboard';
import type { PipelineInsight } from '@/lib/api-types';

// ---------------------------------------------------------------------------
// Section sub-component
// ---------------------------------------------------------------------------

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  items: PipelineInsight[];
  colorClass: string;
  renderDetail: (item: PipelineInsight) => React.ReactNode;
}

function MoverSection({ title, icon, items, colorClass, renderDetail }: SectionProps) {
  if (items.length === 0) return null;

  return (
    <div>
      <h4 className={`text-xs font-semibold uppercase tracking-wide mb-2 flex items-center gap-1.5 ${colorClass}`}>
        {icon}
        {title} ({items.length})
      </h4>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.account_id} className="text-sm flex items-center justify-between">
            <Link
              href={`/deals/${item.account_id}`}
              className="font-medium hover:underline truncate max-w-[60%]"
            >
              {item.account_name}
            </Link>
            <span className="text-xs text-muted-foreground shrink-0 ml-2">
              {renderDetail(item)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function PipelineMovers() {
  const { data: insights } = useInsights();

  if (!insights) return null;

  const { declining, improving, forecast_flips, stale } = insights;

  // Don't render if no movements at all
  const totalMovers =
    (declining?.length ?? 0) +
    (improving?.length ?? 0) +
    (forecast_flips?.length ?? 0) +
    (stale?.length ?? 0);

  if (totalMovers === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Pipeline Movements</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <MoverSection
            title="Declining"
            icon={<TrendingDown className="size-3" />}
            items={declining ?? []}
            colorClass="text-red-600 dark:text-red-400"
            renderDetail={(item) =>
              item.previous_health_score != null && item.health_score != null ? (
                <span className="text-red-600 dark:text-red-400">
                  {item.previous_health_score} → {item.health_score}
                  {item.delta != null && ` (${item.delta > 0 ? '+' : ''}${item.delta})`}
                </span>
              ) : (
                item.description
              )
            }
          />
          <MoverSection
            title="Improving"
            icon={<TrendingUp className="size-3" />}
            items={improving ?? []}
            colorClass="text-emerald-600 dark:text-emerald-400"
            renderDetail={(item) =>
              item.previous_health_score != null && item.health_score != null ? (
                <span className="text-emerald-600 dark:text-emerald-400">
                  {item.previous_health_score} → {item.health_score}
                  {item.delta != null && ` (+${item.delta})`}
                </span>
              ) : (
                item.description
              )
            }
          />
          <MoverSection
            title="Forecast Flips"
            icon={<ArrowLeftRight className="size-3" />}
            items={forecast_flips ?? []}
            colorClass="text-amber-600 dark:text-amber-400"
            renderDetail={(item) =>
              item.previous_forecast && item.current_forecast ? (
                <span className="text-amber-600 dark:text-amber-400">
                  {item.previous_forecast} → {item.current_forecast}
                </span>
              ) : (
                item.description
              )
            }
          />
          <MoverSection
            title="Stale"
            icon={<Clock className="size-3" />}
            items={stale ?? []}
            colorClass="text-muted-foreground"
            renderDetail={(item) =>
              item.days_since_call != null ? (
                <span>{item.days_since_call} days</span>
              ) : (
                item.description
              )
            }
          />
        </div>
      </CardContent>
    </Card>
  );
}
