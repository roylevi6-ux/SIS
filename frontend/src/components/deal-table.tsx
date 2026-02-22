'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertTriangle, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { HealthBadge } from '@/components/health-badge';
import { MomentumIndicator } from '@/components/momentum-indicator';
import { ForecastBadge } from '@/components/forecast-badge';
import type { PipelineDeal } from '@/lib/pipeline-types';

interface DealTableProps {
  deals: PipelineDeal[];
}

type SortKey =
  | 'account_name'
  | 'mrr_estimate'
  | 'inferred_stage'
  | 'health_score'
  | 'momentum_direction'
  | 'ai_forecast_category'
  | 'ic_forecast_category'
  | 'days_since_call';

type SortDirection = 'asc' | 'desc';

function formatMrr(value: number | null): string {
  if (value === null || value === undefined) return '--';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toLocaleString()}`;
}

function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const callDate = new Date(dateStr);
  if (isNaN(callDate.getTime())) return null;
  const now = new Date();
  const diffMs = now.getTime() - callDate.getTime();
  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

function formatDaysSince(dateStr: string | null): string {
  const days = daysSince(dateStr);
  if (days === null) return '--';
  if (days === 0) return 'Today';
  if (days === 1) return '1 day';
  return `${days} days`;
}

const momentumOrder: Record<string, number> = {
  Improving: 3,
  Stable: 2,
  Declining: 1,
};

function SortableHeader({
  label,
  sortKey,
  currentSort,
  currentDirection,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  currentSort: SortKey;
  currentDirection: SortDirection;
  onSort: (key: SortKey) => void;
}) {
  const isActive = currentSort === sortKey;

  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
    >
      {label}
      {isActive ? (
        currentDirection === 'asc' ? (
          <ArrowUp className="size-3.5" />
        ) : (
          <ArrowDown className="size-3.5" />
        )
      ) : (
        <ArrowUpDown className="size-3.5 opacity-40" />
      )}
    </button>
  );
}

export function DealTable({ deals }: DealTableProps) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>('health_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDirection(key === 'account_name' ? 'asc' : 'desc');
    }
  }

  const sorted = useMemo(() => {
    const copy = [...deals];
    copy.sort((a, b) => {
      let aVal: string | number | null;
      let bVal: string | number | null;

      switch (sortKey) {
        case 'account_name':
          aVal = a.account_name?.toLowerCase() ?? '';
          bVal = b.account_name?.toLowerCase() ?? '';
          break;
        case 'mrr_estimate':
          aVal = a.mrr_estimate;
          bVal = b.mrr_estimate;
          break;
        case 'inferred_stage':
          aVal = a.inferred_stage;
          bVal = b.inferred_stage;
          break;
        case 'health_score':
          aVal = a.health_score;
          bVal = b.health_score;
          break;
        case 'momentum_direction':
          aVal = momentumOrder[a.momentum_direction ?? ''] ?? 0;
          bVal = momentumOrder[b.momentum_direction ?? ''] ?? 0;
          break;
        case 'ai_forecast_category':
          aVal = a.ai_forecast_category?.toLowerCase() ?? '';
          bVal = b.ai_forecast_category?.toLowerCase() ?? '';
          break;
        case 'ic_forecast_category':
          aVal = a.ic_forecast_category?.toLowerCase() ?? '';
          bVal = b.ic_forecast_category?.toLowerCase() ?? '';
          break;
        case 'days_since_call':
          aVal = daysSince(a.last_call_date);
          bVal = daysSince(b.last_call_date);
          break;
        default:
          return 0;
      }

      // Nulls always sort last
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1;
      if (bVal === null) return -1;

      let cmp: number;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        cmp = aVal.localeCompare(bVal);
      } else {
        cmp = (aVal as number) - (bVal as number);
      }

      return sortDirection === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [deals, sortKey, sortDirection]);

  if (deals.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        No deals to display.
      </div>
    );
  }

  return (
    <TooltipProvider delayDuration={300}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>
              <SortableHeader
                label="Account"
                sortKey="account_name"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead className="text-right">
              <SortableHeader
                label="MRR"
                sortKey="mrr_estimate"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead>
              <SortableHeader
                label="Stage"
                sortKey="inferred_stage"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead>
              <SortableHeader
                label="Health"
                sortKey="health_score"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead>
              <SortableHeader
                label="Momentum"
                sortKey="momentum_direction"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead>
              <SortableHeader
                label="AI Forecast"
                sortKey="ai_forecast_category"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead>
              <SortableHeader
                label="IC Forecast"
                sortKey="ic_forecast_category"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
            <TableHead className="text-right">
              <SortableHeader
                label="Last Call"
                sortKey="days_since_call"
                currentSort={sortKey}
                currentDirection={sortDirection}
                onSort={handleSort}
              />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((deal) => (
            <TableRow
              key={deal.account_id}
              className="cursor-pointer"
              onClick={() => router.push(`/deals/${deal.account_id}`)}
            >
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <Link
                    href={`/deals/${deal.account_id}`}
                    className="hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {deal.account_name}
                  </Link>
                  {deal.divergence_flag && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <AlertTriangle className="size-4 text-at-risk shrink-0" />
                      </TooltipTrigger>
                      <TooltipContent>
                        IC and AI forecasts diverge
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatMrr(deal.mrr_estimate)}
              </TableCell>
              <TableCell>
                {deal.stage_name ?? (deal.inferred_stage !== null ? `S${deal.inferred_stage}` : '--')}
              </TableCell>
              <TableCell>
                <HealthBadge score={deal.health_score} />
              </TableCell>
              <TableCell>
                <MomentumIndicator direction={deal.momentum_direction as 'Improving' | 'Stable' | 'Declining' | null} />
              </TableCell>
              <TableCell>
                <ForecastBadge category={deal.ai_forecast_category} />
              </TableCell>
              <TableCell>
                <ForecastBadge category={deal.ic_forecast_category} />
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatDaysSince(deal.last_call_date)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TooltipProvider>
  );
}
