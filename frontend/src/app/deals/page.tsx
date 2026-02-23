'use client';

import { useState, useMemo } from 'react';
import { useAccounts } from '@/lib/hooks/use-accounts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { DealTable } from '@/components/deal-table';
import type { PipelineDeal } from '@/lib/pipeline-types';

function PageSkeleton() {
  return (
    <div className="p-6 space-y-4 animate-pulse">
      <div className="h-8 w-32 rounded bg-muted" />
      <div className="h-64 rounded-xl border bg-muted/20" />
    </div>
  );
}

export default function DealsPage() {
  const [search, setSearch] = useState('');
  const { data: rawData, isLoading, isError, error } = useAccounts();

  const deals = useMemo<PipelineDeal[]>(() => {
    if (!rawData) return [];
    return rawData as PipelineDeal[];
  }, [rawData]);

  const filtered = useMemo(() => {
    if (!search.trim()) return deals;
    const q = search.toLowerCase();
    return deals.filter(
      (d) =>
        d.account_name?.toLowerCase().includes(q) ||
        d.ae_owner?.toLowerCase().includes(q) ||
        d.team_name?.toLowerCase().includes(q),
    );
  }, [deals, search]);

  if (isLoading) return <PageSkeleton />;

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Deals</h1>
          <p className="text-sm text-muted-foreground">
            {filtered.length} deal{filtered.length !== 1 ? 's' : ''}
            {search.trim() ? ` matching "${search}"` : ''}
          </p>
        </div>
        <Input
          placeholder="Search by account, AE, or team..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:w-[260px]"
        />
      </div>

      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load deals</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {!isError && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">All Deals</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <DealTable deals={filtered} />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
