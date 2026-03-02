'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatMrr } from '@/lib/format';
import type { PipelineDeal } from '@/lib/pipeline-types';

export type ForecastCategory = 'commit' | 'realistic' | 'upside' | 'risk';

interface TeamForecastGridProps {
  deals: PipelineDeal[];
  onCellClick?: (teamLead: string | null, category: string | null) => void;
  activeTeamLead?: string | null;
  activeForecastCategory?: string | null;
}

interface TeamRow {
  team_lead: string;
  commit: number;
  realistic: number;
  upside: number;
  risk: number;
  total: number;
  deals: number;
}

const CATEGORIES: { key: ForecastCategory; label: string }[] = [
  { key: 'commit', label: 'Commit' },
  { key: 'realistic', label: 'Realistic' },
  { key: 'upside', label: 'Upside' },
  { key: 'risk', label: 'Risk' },
];

function buildTeamRows(deals: PipelineDeal[]): TeamRow[] {
  const map = new Map<string, TeamRow>();

  for (const deal of deals) {
    const lead = deal.team_lead || 'Unassigned';
    if (!map.has(lead)) {
      map.set(lead, { team_lead: lead, commit: 0, realistic: 0, upside: 0, risk: 0, total: 0, deals: 0 });
    }
    const row = map.get(lead)!;
    const mrr = deal.cp_estimate || 0;
    const cat = (deal.ai_forecast_category || '').toLowerCase().replace(' ', '_').replace('at_risk', 'risk');

    if (cat === 'commit') row.commit += mrr;
    else if (cat === 'realistic') row.realistic += mrr;
    else if (cat === 'upside') row.upside += mrr;
    else row.risk += mrr;

    row.total += mrr;
    row.deals += 1;
  }

  return Array.from(map.values()).sort((a, b) => b.total - a.total);
}

export function TeamForecastGrid({
  deals,
  onCellClick,
  activeTeamLead,
  activeForecastCategory,
}: TeamForecastGridProps) {
  const rows = buildTeamRows(deals);

  if (rows.length === 0) return null;

  const totals = rows.reduce(
    (acc, r) => ({
      commit: acc.commit + r.commit,
      realistic: acc.realistic + r.realistic,
      upside: acc.upside + r.upside,
      risk: acc.risk + r.risk,
      total: acc.total + r.total,
      deals: acc.deals + r.deals,
    }),
    { commit: 0, realistic: 0, upside: 0, risk: 0, total: 0, deals: 0 },
  );

  const hasActiveFilter = activeTeamLead != null || activeForecastCategory != null;

  const isRowActive = (teamLead: string) => activeTeamLead === teamLead;
  const isCellExactMatch = (teamLead: string, category: ForecastCategory) =>
    activeTeamLead === teamLead && activeForecastCategory === category;
  const isColumnActive = (category: ForecastCategory) => activeForecastCategory === category;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Team Forecast
        </h2>
        {hasActiveFilter && (
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => onCellClick?.(null, null)}
          >
            All Teams / All Forecasts
          </Button>
        )}
      </div>
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap">
                Team
              </TableHead>
              {CATEGORIES.map(({ key, label }) => (
                <TableHead
                  key={key}
                  className={cn(
                    'text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right',
                    onCellClick && 'cursor-pointer hover:text-brand-700',
                    isColumnActive(key) && !activeTeamLead && 'font-bold text-brand-700',
                  )}
                  onClick={() => onCellClick?.(null, key)}
                >
                  {label}
                </TableHead>
              ))}
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">
                Total
              </TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">
                Deals
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => {
              const rowActive = isRowActive(row.team_lead);

              return (
                <TableRow
                  key={row.team_lead}
                  className={cn(
                    'transition-colors',
                    rowActive && !activeForecastCategory && 'bg-brand-50/50',
                  )}
                >
                  {/* Team name cell */}
                  <TableCell
                    className={cn(
                      'font-medium whitespace-nowrap',
                      onCellClick && 'cursor-pointer hover:bg-muted/50',
                      rowActive && 'font-semibold text-brand-700',
                    )}
                    onClick={() => onCellClick?.(row.team_lead, null)}
                  >
                    {row.team_lead}
                  </TableCell>

                  {/* Category cells */}
                  {CATEGORIES.map(({ key }) => {
                    const colorClass =
                      key === 'commit' ? 'text-forecast-commit' :
                      key === 'realistic' ? 'text-forecast-realistic' :
                      key === 'upside' ? 'text-forecast-upside' :
                      'text-forecast-risk';

                    return (
                      <TableCell
                        key={key}
                        className={cn(
                          'text-right font-mono tabular-nums',
                          colorClass,
                          onCellClick && 'cursor-pointer hover:bg-muted/50',
                          isCellExactMatch(row.team_lead, key) && 'ring-2 ring-brand-500 bg-brand-50',
                          !isCellExactMatch(row.team_lead, key) && rowActive && 'bg-brand-50/50',
                          !isCellExactMatch(row.team_lead, key) && isColumnActive(key) && !activeTeamLead && 'bg-brand-50/50',
                        )}
                        onClick={() => onCellClick?.(row.team_lead, key)}
                      >
                        {formatMrr(row[key])}
                      </TableCell>
                    );
                  })}

                  {/* Total cell */}
                  <TableCell
                    className={cn(
                      'text-right font-mono tabular-nums font-semibold',
                      onCellClick && 'cursor-pointer hover:bg-muted/50',
                      rowActive && 'bg-brand-50/50',
                    )}
                    onClick={() => onCellClick?.(row.team_lead, null)}
                  >
                    {formatMrr(row.total)}
                  </TableCell>

                  {/* Deals cell */}
                  <TableCell
                    className={cn(
                      'text-right text-muted-foreground',
                      onCellClick && 'cursor-pointer hover:bg-muted/50',
                      rowActive && 'bg-brand-50/50',
                    )}
                    onClick={() => onCellClick?.(row.team_lead, null)}
                  >
                    {row.deals}
                  </TableCell>
                </TableRow>
              );
            })}

            {/* Totals row — not clickable */}
            <TableRow className="bg-muted/20 font-semibold border-t-2">
              <TableCell>Total</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.commit)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.realistic)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.upside)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.risk)}</TableCell>
              <TableCell className="text-right font-mono tabular-nums">{formatMrr(totals.total)}</TableCell>
              <TableCell className="text-right">{totals.deals}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
