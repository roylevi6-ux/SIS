'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { formatMrr } from '@/lib/format';
import type { PipelineDeal } from '@/lib/pipeline-types';

interface TeamForecastGridProps {
  deals: PipelineDeal[];
  onTeamClick?: (teamLead: string) => void;
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

export function TeamForecastGrid({ deals, onTeamClick }: TeamForecastGridProps) {
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

  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Team Forecast
      </h2>
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap">Team</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Commit</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Realistic</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Upside</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Risk</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Total</TableHead>
              <TableHead className="text-[11px] font-semibold uppercase tracking-wider whitespace-nowrap text-right">Deals</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={row.team_lead}
                className={cn(
                  'transition-colors',
                  onTeamClick && 'cursor-pointer hover:bg-brand-50/50',
                )}
                onClick={() => onTeamClick?.(row.team_lead)}
              >
                <TableCell className="font-medium whitespace-nowrap">{row.team_lead}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-commit">{formatMrr(row.commit)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-realistic">{formatMrr(row.realistic)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-upside">{formatMrr(row.upside)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums text-forecast-risk">{formatMrr(row.risk)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums font-semibold">{formatMrr(row.total)}</TableCell>
                <TableCell className="text-right text-muted-foreground">{row.deals}</TableCell>
              </TableRow>
            ))}
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
