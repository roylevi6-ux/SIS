'use client';

import { Fragment, useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatMrr } from '@/lib/format';
import type { PipelineDeal } from '@/lib/pipeline-types';

export type ForecastCategory = 'commit' | 'realistic' | 'upside' | 'risk';

interface TeamForecastGridProps {
  deals: PipelineDeal[];
  onCellClick?: (teamLead: string | null, category: string | null) => void;
  onRepClick?: (aeOwner: string) => void;
  activeTeamLead?: string | null;
  activeForecastCategory?: string | null;
  activeRepFilter?: string | null;
}

interface RepRow {
  ae_owner: string;
  commit: number;
  realistic: number;
  upside: number;
  risk: number;
  total: number;
  deals: number;
}

interface TeamRow {
  team_lead: string;
  commit: number;
  realistic: number;
  upside: number;
  risk: number;
  total: number;
  deals: number;
  reps: RepRow[];
}

const CATEGORIES: { key: ForecastCategory; label: string }[] = [
  { key: 'commit', label: 'Commit' },
  { key: 'realistic', label: 'Realistic' },
  { key: 'upside', label: 'Upside' },
  { key: 'risk', label: 'Risk' },
];

function categorizeDeal(deal: PipelineDeal): ForecastCategory {
  const cat = (deal.ai_forecast_category || '').toLowerCase().replace(' ', '_').replace('at_risk', 'risk');
  if (cat === 'commit' || cat === 'realistic' || cat === 'upside') return cat;
  return 'risk';
}

function buildTeamRows(deals: PipelineDeal[]): TeamRow[] {
  const map = new Map<string, TeamRow>();

  for (const deal of deals) {
    const lead = deal.team_lead || 'Unassigned';
    if (!map.has(lead)) {
      map.set(lead, { team_lead: lead, commit: 0, realistic: 0, upside: 0, risk: 0, total: 0, deals: 0, reps: [] });
    }
    const row = map.get(lead)!;
    const mrr = deal.cp_estimate || 0;
    const cat = categorizeDeal(deal);

    row[cat] += mrr;
    row.total += mrr;
    row.deals += 1;
  }

  // Build rep rows within each team
  for (const [lead, teamRow] of map) {
    const teamDeals = deals.filter((d) => (d.team_lead || 'Unassigned') === lead);
    const repMap = new Map<string, RepRow>();

    for (const deal of teamDeals) {
      const rep = deal.ae_owner || 'Unassigned';
      if (!repMap.has(rep)) {
        repMap.set(rep, { ae_owner: rep, commit: 0, realistic: 0, upside: 0, risk: 0, total: 0, deals: 0 });
      }
      const repRow = repMap.get(rep)!;
      const mrr = deal.cp_estimate || 0;
      const cat = categorizeDeal(deal);

      repRow[cat] += mrr;
      repRow.total += mrr;
      repRow.deals += 1;
    }

    teamRow.reps = Array.from(repMap.values()).sort((a, b) => b.total - a.total);
  }

  return Array.from(map.values()).sort((a, b) => b.total - a.total);
}

export function TeamForecastGrid({
  deals,
  onCellClick,
  onRepClick,
  activeTeamLead,
  activeForecastCategory,
  activeRepFilter,
}: TeamForecastGridProps) {
  const [expandedTeams, setExpandedTeams] = useState<Set<string>>(new Set());
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

  const hasActiveFilter = activeTeamLead != null || activeForecastCategory != null || activeRepFilter != null;

  const isRowActive = (teamLead: string) => activeTeamLead === teamLead;
  const isCellExactMatch = (teamLead: string, category: ForecastCategory) =>
    activeTeamLead === teamLead && activeForecastCategory === category;
  const isColumnActive = (category: ForecastCategory) => activeForecastCategory === category;

  const toggleExpand = (teamLead: string) => {
    setExpandedTeams((prev) => {
      const next = new Set(prev);
      if (next.has(teamLead)) next.delete(teamLead);
      else next.add(teamLead);
      return next;
    });
  };

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
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap">
                Team
              </TableHead>
              {CATEGORIES.map(({ key, label }) => (
                <TableHead
                  key={key}
                  className={cn(
                    'text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right',
                    onCellClick && 'cursor-pointer hover:text-brand-400',
                    isColumnActive(key) && !activeTeamLead && 'font-bold text-brand-400',
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
              const isExpanded = expandedTeams.has(row.team_lead);
              const hasReps = row.reps.length > 1;

              return (
                <Fragment key={row.team_lead}>
                  {/* Team lead row */}
                  <TableRow
                    className={cn(
                      'transition-colors',
                      rowActive && !activeForecastCategory && 'bg-brand-500/10',
                    )}
                  >
                    {/* Team name cell with chevron */}
                    <TableCell
                      className={cn(
                        'font-medium whitespace-nowrap',
                        onCellClick && 'cursor-pointer hover:bg-brand-500/8',
                        rowActive && 'font-semibold text-brand-400',
                      )}
                    >
                      <div className="flex items-center gap-1">
                        {hasReps ? (
                          <button
                            type="button"
                            className="shrink-0 rounded p-0.5 hover:bg-brand-500/10 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleExpand(row.team_lead);
                            }}
                          >
                            <ChevronRight
                              className={cn(
                                'size-3.5 text-muted-foreground transition-transform duration-150',
                                isExpanded && 'rotate-90',
                              )}
                            />
                          </button>
                        ) : (
                          <span className="w-[22px]" />
                        )}
                        <span onClick={() => onCellClick?.(row.team_lead, null)}>
                          {row.team_lead}
                        </span>
                      </div>
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
                            isCellExactMatch(row.team_lead, key) && 'ring-1 ring-brand-500/30 bg-brand-500/15',
                            !isCellExactMatch(row.team_lead, key) && rowActive && 'bg-brand-500/10',
                            !isCellExactMatch(row.team_lead, key) && isColumnActive(key) && !activeTeamLead && 'bg-brand-500/10',
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
                        onCellClick && 'cursor-pointer hover:bg-brand-500/8',
                        rowActive && 'bg-brand-500/10',
                      )}
                      onClick={() => onCellClick?.(row.team_lead, null)}
                    >
                      {formatMrr(row.total)}
                    </TableCell>

                    {/* Deals cell */}
                    <TableCell
                      className={cn(
                        'text-right text-muted-foreground',
                        onCellClick && 'cursor-pointer hover:bg-brand-500/8',
                        rowActive && 'bg-brand-500/10',
                      )}
                      onClick={() => onCellClick?.(row.team_lead, null)}
                    >
                      {row.deals}
                    </TableCell>
                  </TableRow>

                  {/* Rep rows (expanded) */}
                  {isExpanded && row.reps.map((rep) => {
                    const isRepActive = activeRepFilter === rep.ae_owner;

                    return (
                      <TableRow
                        key={`${row.team_lead}-${rep.ae_owner}`}
                        className={cn(
                          'transition-colors bg-muted/20',
                          isRepActive && 'bg-brand-500/12',
                        )}
                      >
                        <TableCell className="pl-10 whitespace-nowrap">
                          <span
                            className={cn(
                              'text-sm cursor-pointer hover:text-brand-400 transition-colors',
                              isRepActive && 'font-semibold text-brand-400',
                            )}
                            onClick={() => onRepClick?.(rep.ae_owner)}
                          >
                            {rep.ae_owner}
                          </span>
                        </TableCell>

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
                                'text-right font-mono tabular-nums text-sm',
                                colorClass,
                                onCellClick && 'cursor-pointer hover:bg-brand-500/8',
                              )}
                              onClick={() => onCellClick?.(row.team_lead, key)}
                            >
                              {rep[key] === 0 ? '—' : formatMrr(rep[key])}
                            </TableCell>
                          );
                        })}

                        <TableCell className="text-right font-mono tabular-nums text-sm font-medium">
                          {formatMrr(rep.total)}
                        </TableCell>

                        <TableCell className="text-right text-sm text-muted-foreground">
                          {rep.deals}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </Fragment>
              );
            })}

            {/* Totals row — not clickable */}
            <TableRow className="bg-muted/30 font-semibold border-t-2">
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
