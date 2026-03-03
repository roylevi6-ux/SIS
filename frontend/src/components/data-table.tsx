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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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

function rowTintClass(deal: PipelineDeal): string {
  const tier = healthTier(deal.health_score);
  if (tier === 'needs_attention') return 'bg-needs-attention-light/40';
  if (tier === 'neutral') return 'bg-neutral-light/30';
  return '';
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
    header: 'Account',
    cell: ({ row }) => {
      const deal = row.original;
      return (
        <div className="min-w-[160px]" title={deal.deal_memo_preview || undefined}>
          <a
            href={`/deals/${deal.account_id}`}
            className="font-medium text-foreground hover:text-primary hover:underline"
          >
            {deal.account_name}
          </a>
          {deal.ae_owner && (
            <div className="text-xs text-muted-foreground">{deal.ae_owner}</div>
          )}
        </div>
      );
    },
    size: 200,
  },
  {
    accessorKey: 'cp_estimate',
    header: 'CP Est.',
    cell: ({ getValue }) => (
      <span className="font-mono tabular-nums text-right block">
        {formatMrr(getValue() as number | null)}
      </span>
    ),
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
            ? 'bg-brand-100 text-brand-700'
            : 'bg-muted text-muted-foreground'
        )}>
          {val}
        </span>
      );
    },
    size: 80,
  },
  {
    accessorKey: 'stage_name',
    header: 'Stage',
    cell: ({ getValue, row }) => {
      const name = getValue() as string | null;
      const num = row.original.inferred_stage;
      return <span className="text-sm">{name || (num ? `S${num}` : '--')}</span>;
    },
    size: 100,
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
          divergent && 'rounded px-1.5 py-0.5 bg-neutral-light/50'
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
    id: 'sf_gap',
    header: 'SF Gap',
    cell: ({ row }) => {
      const deal = row.original;
      const stageDir = deal.stage_gap_direction;
      const forecastDir = deal.forecast_gap_direction;

      if (!stageDir && !forecastDir) {
        return <span className="text-muted-foreground">—</span>;
      }

      const stageText = !stageDir
        ? null
        : stageDir === 'Aligned'
          ? '='
          : stageDir === 'SF-ahead'
            ? `SF +${deal.stage_gap_magnitude}`
            : `SIS +${deal.stage_gap_magnitude}`;

      const forecastText = !forecastDir
        ? null
        : forecastDir === 'Aligned'
          ? '='
          : forecastDir === 'SF-more-optimistic'
            ? 'SF > AI'
            : 'AI > SF';

      return (
        <div className="text-xs space-y-0.5">
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Stg</span>{' '}
            <span className={cn(
              'font-medium',
              stageText === '=' ? 'text-muted-foreground' : 'text-foreground',
            )}>
              {stageText ?? '—'}
            </span>
          </div>
          <div>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Fct</span>{' '}
            <span className={cn(
              'font-medium',
              forecastText === '=' ? 'text-muted-foreground' : 'text-foreground',
            )}>
              {forecastText ?? '—'}
            </span>
          </div>
        </div>
      );
    },
    size: 90,
  },
  {
    accessorKey: 'health_score',
    header: 'Health',
    cell: ({ getValue }) => <HealthBadge score={getValue() as number | null} />,
    size: 80,
  },
  {
    accessorKey: 'momentum_direction',
    header: 'Momentum',
    cell: ({ getValue }) => <MomentumIndicator direction={getValue() as 'Improving' | 'Stable' | 'Declining' | null} />,
    size: 90,
  },
  {
    accessorKey: 'overall_confidence',
    header: 'Conf.',
    cell: ({ getValue }) => {
      const val = getValue() as number | null;
      if (val === null || val === undefined) return <span className="text-muted-foreground">--</span>;
      return <span className="font-mono tabular-nums text-sm">{(val * 100).toFixed(0)}%</span>;
    },
    size: 60,
  },
  {
    accessorKey: 'last_call_date',
    header: 'Last Call',
    cell: ({ getValue }) => {
      const val = getValue() as string | null;
      return <span className={cn('text-sm', daysAgoColor(val))}>{daysAgo(val)}</span>;
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
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/30">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap cursor-pointer select-none hover:bg-muted/50"
                    onClick={header.column.getToggleSortingHandler()}
                    style={{ width: header.getSize() }}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      <ArrowUpDown className="size-3 text-muted-foreground/50" />
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={dealColumns.length} className="h-24 text-center text-muted-foreground">
                  No deals found
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row, idx) => (
                <TableRow
                  key={row.id}
                  className={cn(
                    'transition-colors hover:bg-brand-50/50',
                    idx % 2 === 1 && 'bg-muted/15',
                    rowTintClass(row.original),
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="whitespace-normal align-top py-2.5">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between px-2 py-3">
          <span className="text-xs text-muted-foreground">
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
            <span className="text-sm font-medium">
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
  );
}
