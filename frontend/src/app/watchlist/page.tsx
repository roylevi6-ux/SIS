'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  Trash2,
  Plus,
  RefreshCw,
  ScanLine,
  Search,
  Check,
  Loader2,
} from 'lucide-react';

import { api } from '@/lib/api';
import type { WatchlistAccount, Account, SyncJob } from '@/lib/api-types';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { SyncProgressModal } from '@/components/sync-progress-modal';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeTime(isoString: string | null): string {
  if (!isoString) return 'Never';
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

function HealthDisplay({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground font-mono">--</span>;
  const color =
    score >= 70
      ? 'text-healthy'
      : score >= 40
        ? 'text-neutral'
        : 'text-needs-attention';
  return <span className={cn('font-mono font-medium', color)}>{score}</span>;
}

function StatusDisplay({ account }: { account: WatchlistAccount }) {
  if (account.last_analyzed === null) {
    return <span className="text-muted-foreground text-sm">Never analyzed</span>;
  }
  if (account.has_new_calls) {
    return (
      <span className="text-sm text-healthy">
        {account.transcript_count > 0 ? `${account.transcript_count} call${account.transcript_count !== 1 ? 's' : ''} new` : 'New calls'}
      </span>
    );
  }
  return <span className="text-muted-foreground text-sm">Up to date</span>;
}

// ---------------------------------------------------------------------------
// Inline SF Name editor
// ---------------------------------------------------------------------------

function SFNameCell({
  accountId,
  current,
  onSave,
}: {
  accountId: string;
  current: string;
  onSave: (accountId: string, sfName: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(current);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      onSave(accountId, value);
      setEditing(false);
    }
    if (e.key === 'Escape') {
      setValue(current);
      setEditing(false);
    }
  }

  function handleBlur() {
    onSave(accountId, value);
    setEditing(false);
  }

  if (editing) {
    return (
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        autoFocus
        className="h-8 text-sm bg-muted border-primary"
      />
    );
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className={cn(
        'text-sm text-left w-full rounded px-1 py-0.5 transition-colors min-h-[32px]',
        'hover:bg-accent hover:text-accent-foreground',
        current ? 'text-foreground' : 'text-muted-foreground italic'
      )}
      title="Click to edit Salesforce account name"
    >
      {current || 'Click to set'}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Add Accounts Dialog
// ---------------------------------------------------------------------------

function AddAccountsDialog({
  open,
  onOpenChange,
  watchlistIds,
  onAdd,
  onAddAllComplete,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  watchlistIds: Set<string>;
  onAdd: (accountIds: string[]) => void;
  onAddAllComplete?: () => void;
}) {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [adding, setAdding] = useState(false);

  const { data: accounts, isLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => api.accounts.list(),
    enabled: open,
    staleTime: 60_000,
  });

  const filtered = useMemo(() => {
    if (!accounts) return [];
    const q = search.toLowerCase();
    return accounts.filter(
      (a) => !watchlistIds.has(a.id) && a.account_name.toLowerCase().includes(q)
    );
  }, [accounts, watchlistIds, search]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(filtered.map((a) => a.id)));
  }

  function clearAll() {
    setSelected(new Set());
  }

  async function handleAdd() {
    if (selected.size === 0) return;
    setAdding(true);
    try {
      onAdd(Array.from(selected));
      setSelected(new Set());
      onOpenChange(false);
    } finally {
      setAdding(false);
    }
  }

  async function handleAddAll() {
    setAdding(true);
    try {
      await api.watchlist.addAll();
      onAddAllComplete?.();
      onOpenChange(false);
    } finally {
      setAdding(false);
    }
  }

  function handleOpenChange(v: boolean) {
    if (!v) {
      setSearch('');
      setSelected(new Set());
    }
    onOpenChange(v);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg bg-card border-border">
        <DialogHeader>
          <DialogTitle>Add Accounts to Watchlist</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search accounts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-muted border-border"
            />
          </div>

          {/* Select all / clear */}
          {filtered.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={selectAll}
                className="text-primary hover:underline"
              >
                Select all ({filtered.length})
              </button>
              {selected.size > 0 && (
                <>
                  <span className="text-muted-foreground">·</span>
                  <button onClick={clearAll} className="text-muted-foreground hover:text-foreground">
                    Clear
                  </button>
                </>
              )}
            </div>
          )}

          {/* Account list */}
          <div className="max-h-72 overflow-y-auto rounded-lg border border-border divide-y divide-border/50">
            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="size-4 animate-spin text-primary" />
              </div>
            )}
            {!isLoading && filtered.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                {accounts?.length === 0
                  ? 'No accounts found'
                  : 'All accounts are already on the watchlist'}
              </div>
            )}
            {filtered.map((account) => {
              const isSelected = selected.has(account.id);
              return (
                <button
                  key={account.id}
                  onClick={() => toggleSelect(account.id)}
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors min-h-[44px]',
                    isSelected
                      ? 'bg-primary/10'
                      : 'hover:bg-accent/60'
                  )}
                >
                  <div
                    className={cn(
                      'size-4 rounded shrink-0 border transition-colors flex items-center justify-center',
                      isSelected
                        ? 'border-primary bg-primary'
                        : 'border-border'
                    )}
                  >
                    {isSelected && <Check className="size-3 text-white" />}
                  </div>
                  <span className="text-sm text-foreground whitespace-normal">
                    {account.account_name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleAddAll}
            disabled={adding}
            className="border-border"
          >
            Add All Current Accounts
          </Button>
          <Button
            size="sm"
            onClick={handleAdd}
            disabled={selected.size === 0 || adding}
            className="bg-primary hover:bg-primary/90 min-w-[120px]"
          >
            {adding ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              `Add Selected (${selected.size})`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-10 w-64 animate-pulse rounded-lg bg-muted" />
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function WatchlistPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [syncJobId, setSyncJobId] = useState<string | null>(null);
  const [syncModalOpen, setSyncModalOpen] = useState(false);

  // Detect running sync job on mount (e.g. user left page and came back)
  const { data: syncHistory } = useQuery<SyncJob[]>({
    queryKey: ['sync-history'],
    queryFn: () => api.sync.history(),
    staleTime: 10_000,
  });

  useEffect(() => {
    if (!syncJobId && syncHistory?.length) {
      const running = syncHistory.find(
        (j) => j.status === 'pending' || j.status === 'running' || j.status === 'scanning' || j.status === 'importing'
      );
      if (running) {
        setSyncJobId(running.job_id);
      }
    }
  }, [syncHistory, syncJobId]);

  const { data: watchlist, isLoading, isError, error } = useQuery<WatchlistAccount[]>({
    queryKey: ['watchlist'],
    queryFn: () => api.watchlist.list(),
    staleTime: 30_000,
  });

  const addMutation = useMutation({
    mutationFn: (accountIds: string[]) => api.watchlist.add(accountIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const removeMutation = useMutation({
    mutationFn: (accountId: string) => api.watchlist.remove(accountId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const updateSFNameMutation = useMutation({
    mutationFn: ({ accountId, sfName }: { accountId: string; sfName: string }) =>
      api.watchlist.updateSFName(accountId, sfName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  const handleSFNameSave = useCallback(
    (accountId: string, sfName: string) => {
      updateSFNameMutation.mutate({ accountId, sfName });
    },
    [updateSFNameMutation]
  );

  async function handleSyncAll(skipN8n = false) {
    try {
      const result = await api.sync.start({ skip_n8n: skipN8n });
      setSyncJobId(result.job_id);
      setSyncModalOpen(true);
    } catch (err) {
      console.error('Failed to start sync:', err);
    }
  }

  function handleSyncComplete() {
    setSyncJobId(null);
    qc.invalidateQueries({ queryKey: ['watchlist'] });
    qc.invalidateQueries({ queryKey: ['sync-history'] });
  }

  const watchlistIds = useMemo(
    () => new Set((watchlist ?? []).map((a) => a.account_id)),
    [watchlist]
  );

  const sorted = useMemo(() => {
    if (!watchlist) return [];
    return [...watchlist].sort((a, b) => {
      // NEW calls first
      if (a.has_new_calls && !b.has_new_calls) return -1;
      if (!a.has_new_calls && b.has_new_calls) return 1;
      return a.account_name.localeCompare(b.account_name);
    });
  }, [watchlist]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return sorted.filter((a) => a.account_name.toLowerCase().includes(q));
  }, [sorted, search]);

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Watchlist</h1>
          <p className="text-sm text-muted-foreground">
            {watchlist
              ? `${watchlist.length} account${watchlist.length !== 1 ? 's' : ''} tracked`
              : 'Track accounts for automatic Gong sync'}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAddDialogOpen(true)}
            className="border-border min-h-[44px] gap-1.5"
          >
            <Plus className="size-4" />
            Add Accounts
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleSyncAll(true)}
            className="border-border min-h-[44px] gap-1.5"
          >
            <ScanLine className="size-4" />
            Scan Only
          </Button>
          <Button
            size="sm"
            onClick={() => handleSyncAll(false)}
            className="bg-primary hover:bg-primary/90 min-h-[44px] gap-1.5"
          >
            <RefreshCw className="size-4" />
            Sync All
          </Button>
        </div>
      </div>

      {/* Search */}
      {(watchlist?.length ?? 0) > 0 && (
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            placeholder="Search watchlist..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-card border-border"
          />
        </div>
      )}

      {/* Sync in progress banner */}
      {syncJobId && !syncModalOpen && (
        <button
          onClick={() => setSyncModalOpen(true)}
          className="w-full flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-left transition-colors hover:bg-primary/15"
        >
          <Loader2 className="size-4 animate-spin text-primary shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">Sync in progress</p>
            <p className="text-xs text-muted-foreground">Click to view progress</p>
          </div>
        </button>
      )}

      {/* Loading */}
      {isLoading && <LoadingSkeleton />}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-4">
          <p className="text-sm font-medium text-destructive">Failed to load watchlist</p>
          <p className="text-xs text-destructive/70 mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && watchlist?.length === 0 && (
        <div className="rounded-lg border border-border bg-card px-6 py-12 text-center">
          <p className="text-muted-foreground">No accounts on watchlist yet.</p>
          <p className="text-sm text-muted-foreground mt-1">
            Add accounts to start tracking Gong sync status.
          </p>
          <Button
            size="sm"
            onClick={() => setAddDialogOpen(true)}
            className="mt-4 bg-primary hover:bg-primary/90 gap-1.5"
          >
            <Plus className="size-4" />
            Add Accounts
          </Button>
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (watchlist?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-muted-foreground text-xs uppercase tracking-wider whitespace-normal">
                  Account
                </TableHead>
                <TableHead className="text-muted-foreground text-xs uppercase tracking-wider whitespace-normal">
                  SF Name
                </TableHead>
                <TableHead className="text-muted-foreground text-xs uppercase tracking-wider whitespace-normal">
                  Status
                </TableHead>
                <TableHead className="text-muted-foreground text-xs uppercase tracking-wider whitespace-normal text-right">
                  Health
                </TableHead>
                <TableHead className="text-muted-foreground text-xs uppercase tracking-wider whitespace-normal">
                  Last Analyzed
                </TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center text-muted-foreground py-8 whitespace-normal"
                  >
                    No accounts match your search.
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((account) => (
                <TableRow
                  key={account.account_id}
                  className="border-border hover:bg-accent/30 animate-row-reveal align-top"
                >
                  {/* Account name */}
                  <TableCell className="py-3 whitespace-normal">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={`/deals/${account.account_id}`}
                        className="text-sm font-medium text-foreground hover:text-primary transition-colors"
                      >
                        {account.account_name}
                      </Link>
                      {account.has_new_calls && (
                        <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-400 shrink-0">
                          NEW
                        </span>
                      )}
                    </div>
                  </TableCell>

                  {/* SF Name (inline editable) */}
                  <TableCell className="py-3 min-w-[160px] whitespace-normal">
                    <SFNameCell
                      accountId={account.account_id}
                      current={account.sf_account_name}
                      onSave={handleSFNameSave}
                    />
                  </TableCell>

                  {/* Status */}
                  <TableCell className="py-3 whitespace-normal">
                    <StatusDisplay account={account} />
                  </TableCell>

                  {/* Health */}
                  <TableCell className="py-3 text-right whitespace-normal">
                    <HealthDisplay score={account.health_score} />
                  </TableCell>

                  {/* Last analyzed */}
                  <TableCell className="py-3 whitespace-normal">
                    <span className="text-sm text-muted-foreground">
                      {relativeTime(account.last_analyzed)}
                    </span>
                  </TableCell>

                  {/* Actions */}
                  <TableCell className="py-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      onClick={() => removeMutation.mutate(account.account_id)}
                      aria-label={`Remove ${account.account_name} from watchlist`}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Add Accounts Dialog */}
      <AddAccountsDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        watchlistIds={watchlistIds}
        onAdd={(ids) => addMutation.mutate(ids)}
        onAddAllComplete={() => qc.invalidateQueries({ queryKey: ['watchlist'] })}
      />

      {/* Sync Progress Modal */}
      <SyncProgressModal
        jobId={syncJobId}
        open={syncModalOpen}
        onOpenChange={setSyncModalOpen}
        onComplete={handleSyncComplete}
      />
    </div>
  );
}
