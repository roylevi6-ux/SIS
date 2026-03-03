'use client';

import { useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatMrr } from '@/lib/format';
import { HealthBadge } from '@/components/health-badge';
import { MomentumIndicator } from '@/components/momentum-indicator';
import { ForecastBadge } from '@/components/forecast-badge';
import type { PipelineDeal } from '@/lib/pipeline-types';

function daysAgo(dateStr: string | null): string {
  if (!dateStr) return 'N/A';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff === 0) return 'Today';
  if (diff === 1) return '1d ago';
  return `${diff}d ago`;
}

function daysAgoColor(dateStr: string | null): string {
  if (!dateStr) return 'text-muted-foreground';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff <= 14) return 'text-healthy';
  if (diff <= 30) return 'text-neutral';
  return 'text-needs-attention';
}

function healthTier(score: number | null): string {
  if (score === null) return '';
  if (score >= 70) return 'healthy';
  if (score >= 40) return 'neutral';
  return 'needs_attention';
}

const dealColumns: ColumnDef<PipelineDeal>[] = [
  {
    accessorKey: 'attention_level',
    header: '',
    cell: ({ getValue }) => {
      const level = getValue() as string | null;
      if (!level || level === 'none') return null;
      if (level === 'act')
        return (
          <span className="inline-flex size-2.5 rounded-full bg-red-500" title="VP action needed" />
        );
      return (
        <span className="inline-flex size-2.5 rounded-full bg-amber-400" title="Watch" />
      );
    },
    size: 32,
    enableSorting: true,
  },
  {
    accessorKey: 'account_name',
    header: 'Deal',
    cell: ({ row }) => {
      const deal = row.original;
      return (
        <div className="min-w-[160px]" title={deal.deal_memo_preview || undefined}>
          <a
            href={`/deals/${deal.account_id}`}
            className="text-[13.5px] font-semibold text-foreground hover:text-brand-400 hover:underline"
          >
            {deal.account_name}
          </a>
          {deal.ae_owner && (
            <div className="text-[11.5px] text-muted-foreground mt-0.5">{deal.ae_owner}</div>
          )}
        </div>
      );
    },
    size: 200,
  },
  {
    accessorKey: 'cp_estimate',
    header: 'Amount',
    cell: ({ getValue }) => (
      <span className="font-mono font-medium tabular-nums text-[13.5px]">
        {formatMrr(getValue() as number | null)}
      </span>
    ),
    size: 90,
  },
  {
    accessorKey: 'health_score',
    header: 'Health',
    cell: ({ getValue }) => <HealthBadge score={getValue() as number | null} />,
    size: 80,
  },
  {
    id: 'forecast',
    header: 'Forecast',
    accessorFn: (row) => row.ai_forecast_category,
    cell: ({ row }) => {
      const deal = row.original;
      const ai = deal.ai_forecast_category;
      const sf = deal.sf_forecast_category;
      const divergent = deal.divergence_flag;

      return (
        <div className={cn(
          'flex flex-col gap-0.5',
          divergent && 'rounded px-1.5 py-0.5 bg-neutral-bg'
        )}>
          <ForecastBadge category={ai} />
          {divergent && sf && (
            <span className="text-[10px] text-neutral">SF: {sf}</span>
          )}
        </div>
      );
    },
    size: 120,
  },
  {
    accessorKey: 'stage_name',
    header: 'Stage',
    cell: ({ getValue, row }) => {
      const name = getValue() as string | null;
      const num = row.original.inferred_stage;
      return <span className="text-[13.5px] text-[#86efac]">{name || (num ? `S${num}` : '--')}</span>;
    },
    size: 100,
  },
  {
    accessorKey: 'momentum_direction',
    header: 'Momentum',
    cell: ({ getValue }) => <MomentumIndicator direction={getValue() as 'Improving' | 'Stable' | 'Declining' | null} />,
    size: 90,
  },
  {
    accessorKey: 'deal_type',
    header: 'Type',
    cell: ({ getValue }) => {
      const val = getValue() as string | null;
      if (!val) return <span className="text-muted-foreground">--</span>;
      return (
        <span className={cn(
          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
          val.toLowerCase() === 'expansion'
            ? 'bg-brand-500/15 text-brand-400'
            : 'bg-muted text-muted-foreground'
        )}>
          {val}
        </span>
      );
    },
    size: 80,
  },
  {
    accessorKey: 'overall_confidence',
    header: 'Conf.',
    cell: ({ getValue }) => {
      const val = getValue() as number | null;
      if (val === null || val === undefined) return <span className="text-muted-foreground">--</span>;
      return <span className="font-mono tabular-nums text-[13.5px]">{(val * 100).toFixed(0)}%</span>;
    },
    size: 60,
  },
  {
    accessorKey: 'last_call_date',
    header: 'Last Call',
    cell: ({ getValue }) => {
      const val = getValue() as string | null;
      return <span className={cn('text-[13.5px]', daysAgoColor(val))}>{daysAgo(val)}</span>;
    },
    size: 80,
  },
];

interface DataTableProps {
  deals: PipelineDeal[];
  pageSize?: number;
}

export function DataTable({ deals, pageSize = 25 }: DataTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'cp_estimate', desc: true },
  ]);

  const table = useReactTable({
    data: deals,
    columns: dealColumns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize },
    },
  });

  return (
    <div>
      {/* Table card wrapper — matches mockup bg-surface-1 with border + radius */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="relative w-full overflow-x-auto">
          <table className="w-full caption-bottom">
            {/* Header — surface-2 background, mockup typography */}
            <thead>
              <tr className="border-b border-border">
                {table.getHeaderGroups().map((headerGroup) =>
                  headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground px-4 py-3.5 text-left bg-muted cursor-pointer select-none hover:bg-accent transition-colors whitespace-nowrap"
                      onClick={header.column.getToggleSortingHandler()}
                      style={{ width: header.getSize() }}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        <ArrowUpDown className="size-3 text-muted-foreground/50" />
                      </div>
                    </th>
                  ))
                )}
              </tr>
            </thead>

            {/* Body — mockup-style rows */}
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td colSpan={dealColumns.length} className="h-24 text-center text-muted-foreground px-4 py-3.5">
                    No deals found
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row, idx) => {
                  const tier = healthTier(row.original.health_score);
                  const tintClass = tier === 'needs_attention' ? 'bg-needs-attention-bg' : '';
                  return (
                    <tr
                      key={row.id}
                      className={cn(
                        'border-b border-border/50 transition-colors hover:bg-[rgba(16,185,129,0.08)] animate-row-reveal',
                        tintClass,
                      )}
                      style={{ animationDelay: `${idx * 20}ms` }}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td
                          key={cell.id}
                          className="px-4 py-3.5 align-middle whitespace-normal"
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
        {table.getPageCount() > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border text-xs text-muted-foreground">
            <span>
              Showing {table.getState().pagination.pageIndex * pageSize + 1}–
              {Math.min(
                (table.getState().pagination.pageIndex + 1) * pageSize,
                deals.length,
              )}{' '}
              of {deals.length} deals
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <ChevronLeft className="size-4" />
              </Button>
              <span className="text-sm font-medium text-foreground">
                {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
