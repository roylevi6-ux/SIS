'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import Link from 'next/link';
import {
  Play,
  Search,
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  Check,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useICUsers } from '@/lib/hooks/use-admin';
import { api } from '@/lib/api';
import type { Account, AnalysisRunResponse, ICUser } from '@/lib/api-types';
import { AnalysisProgressDetail } from '@/components/analysis-progress-detail';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEAL_TYPES = [
  { value: 'new_logo', label: 'New Logo' },
  { value: 'expansion_upsell', label: 'Expansion – Upsell' },
  { value: 'expansion_cross_sell', label: 'Expansion – Cross Sell' },
  { value: 'expansion_both', label: 'Expansion – Both' },
  { value: 'renewal', label: 'Renewal' },
];

const SF_STAGES = [
  { value: '1', label: '1 – Qualify' },
  { value: '2', label: '2 – Establish Business Case' },
  { value: '3', label: '3 – Scope' },
  { value: '4', label: '4 – Proposal' },
  { value: '5', label: '5 – Negotiate' },
  { value: '6', label: '6 – Contract' },
  { value: '7', label: '7 – Implement' },
];

const FORECAST_CATEGORIES = [
  { value: 'Commit', label: 'Commit' },
  { value: 'Realistic', label: 'Realistic' },
  { value: 'Upside', label: 'Upside' },
  { value: 'At Risk', label: 'At Risk' },
  { value: 'Pipeline', label: 'Pipeline' },
];

const BUYING_CULTURES = [
  { value: 'direct', label: 'Direct' },
  { value: 'proxy_delegated', label: 'Proxy / Delegated' },
];

function generateCloseQuarters(): string[] {
  const quarters: string[] = [];
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentQ = Math.ceil((now.getMonth() + 1) / 3);
  for (let i = 0; i < 8; i++) {
    const q = ((currentQ - 1 + i) % 4) + 1;
    const y = currentYear + Math.floor((currentQ - 1 + i) / 4);
    quarters.push(`Q${q} ${y}`);
  }
  return quarters;
}

const CLOSE_QUARTERS = generateCloseQuarters();

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AccountConfig {
  owner_id: string;
  deal_type: string;
  cp_estimate: string;
  sf_stage: string;
  sf_forecast_category: string;
  sf_close_quarter: string;
  buying_culture: string;
  prior_contract_value: string;
}

interface RunResult {
  accountId: string;
  accountName: string;
  status: 'pending' | 'starting' | 'running' | 'completed' | 'failed';
  runId: string | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function configFromAccount(a: Account): AccountConfig {
  return {
    owner_id: a.owner_id ?? '',
    deal_type: a.deal_type ?? 'new_logo',
    cp_estimate: a.cp_estimate != null ? String(a.cp_estimate) : '',
    sf_stage: a.sf_stage != null ? String(a.sf_stage) : '',
    sf_forecast_category: a.sf_forecast_category ?? '',
    sf_close_quarter: a.sf_close_quarter ?? '',
    buying_culture: a.buying_culture ?? 'direct',
    prior_contract_value: a.prior_contract_value != null ? String(a.prior_contract_value) : '',
  };
}

function isExpansion(dealType: string): boolean {
  return dealType.startsWith('expansion');
}

function isConfigComplete(cfg: AccountConfig): boolean {
  if (!cfg.owner_id) return false;
  if (!cfg.deal_type) return false;
  if (!cfg.sf_stage) return false;
  if (!cfg.sf_forecast_category) return false;
  if (!cfg.sf_close_quarter) return false;
  if (!cfg.buying_culture) return false;
  if (!cfg.cp_estimate) return false;
  if (isExpansion(cfg.deal_type) && !cfg.prior_contract_value) return false;
  return true;
}

function relativeTime(isoString: string | null | undefined): string {
  if (!isoString) return '--';
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

// ---------------------------------------------------------------------------
// Compact inline select — native <select> for density
// ---------------------------------------------------------------------------

function InlineSelect({
  value,
  onChange,
  options,
  placeholder,
  required,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  const missing = required && !value;
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        'h-7 text-xs rounded border bg-card px-1.5 appearance-none cursor-pointer transition-colors',
        'focus:outline-none focus:ring-1 focus:ring-primary',
        missing
          ? 'border-destructive/50 text-destructive'
          : 'border-border text-foreground',
        className,
      )}
    >
      <option value="">{placeholder ?? 'Select...'}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function InlineNumber({
  value,
  onChange,
  placeholder,
  required,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  const missing = required && !value;
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder ?? '$'}
      className={cn(
        'h-7 text-xs rounded border bg-card px-1.5 w-20 font-mono transition-colors',
        'focus:outline-none focus:ring-1 focus:ring-primary',
        '[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none',
        missing
          ? 'border-destructive/50 placeholder:text-destructive/50'
          : 'border-border text-foreground',
        className,
      )}
    />
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Run progress row
// ---------------------------------------------------------------------------

function RunProgressRow({ run }: { run: RunResult }) {
  const [expanded, setExpanded] = useState(false);
  const canExpand = run.runId !== null && (run.status === 'running' || run.status === 'completed');

  return (
    <>
      <div
        className={cn(
          'flex items-center gap-3 px-4 py-3 text-sm border-b border-border/40 last:border-0 transition-colors',
          canExpand && 'cursor-pointer hover:bg-muted/40',
        )}
        onClick={canExpand ? () => setExpanded((v) => !v) : undefined}
        role={canExpand ? 'button' : undefined}
        tabIndex={canExpand ? 0 : undefined}
        onKeyDown={
          canExpand
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setExpanded((v) => !v);
                }
              }
            : undefined
        }
      >
        <div className="w-4 shrink-0 flex justify-center">
          {canExpand ? (
            expanded ? (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="size-3.5 text-muted-foreground" />
            )
          ) : null}
        </div>
        {run.status === 'completed' && <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />}
        {run.status === 'failed' && <XCircle className="size-4 shrink-0 text-destructive" />}
        {(run.status === 'running' || run.status === 'starting') && (
          <Loader2 className="size-4 shrink-0 text-primary animate-spin" />
        )}
        {run.status === 'pending' && (
          <div className="size-4 shrink-0 rounded-full border-2 border-muted-foreground/30" />
        )}
        <span className={cn('flex-1 min-w-0 truncate font-medium', run.status === 'pending' && 'text-muted-foreground')}>
          {run.accountName}
        </span>
        <span
          className={cn(
            'shrink-0 text-xs',
            run.status === 'completed' && 'text-emerald-600 dark:text-emerald-400',
            run.status === 'failed' && 'text-destructive',
            (run.status === 'running' || run.status === 'starting') && 'text-primary',
            run.status === 'pending' && 'text-muted-foreground/60',
          )}
        >
          {run.status === 'completed' && 'Done'}
          {run.status === 'failed' && 'Failed'}
          {run.status === 'running' && 'Analyzing...'}
          {run.status === 'starting' && 'Starting...'}
          {run.status === 'pending' && 'Queued'}
        </span>
        {run.status === 'completed' && run.accountId && (
          <Button asChild size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={(e) => e.stopPropagation()}>
            <Link href={`/deals/${run.accountId}`}>View &rarr;</Link>
          </Button>
        )}
      </div>
      {run.status === 'failed' && run.error && (
        <div className="px-10 pb-2 text-xs text-destructive">{run.error}</div>
      )}
      {expanded && canExpand && run.runId && (
        <div className="px-4 pb-4">
          <AnalysisProgressDetail runId={run.runId} accountId={run.accountId} />
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Account row with inline SF fields
// ---------------------------------------------------------------------------

function AccountRow({
  account,
  config,
  isSelected,
  onToggle,
  onConfigChange,
  icUsers,
}: {
  account: Account;
  config: AccountConfig;
  isSelected: boolean;
  onToggle: () => void;
  onConfigChange: (patch: Partial<AccountConfig>) => void;
  icUsers: ICUser[];
}) {
  const complete = isConfigComplete(config);

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 border-b border-border/50 transition-colors min-w-fit',
        isSelected && 'bg-primary/5',
      )}
    >
      {/* Checkbox */}
      <div
        onClick={onToggle}
        className={cn(
          'size-4 rounded border transition-colors flex items-center justify-center shrink-0 cursor-pointer',
          isSelected ? 'border-primary bg-primary' : 'border-border hover:border-primary/60',
        )}
      >
        {isSelected && <Check className="size-2.5 text-white" />}
      </div>

      {/* Account name + NEW badge */}
      <div className="flex items-center gap-1.5 w-36 shrink-0 min-w-0">
        <Link
          href={`/deals/${account.id}`}
          className="text-xs font-medium text-foreground hover:text-primary transition-colors truncate"
        >
          {account.account_name}
        </Link>
        {account.has_new_calls && (
          <span className="rounded-full bg-emerald-500/20 px-1.5 py-0 text-[10px] font-medium text-emerald-400 shrink-0 leading-4">
            NEW
          </span>
        )}
      </div>

      {/* AE Owner */}
      <InlineSelect
        value={config.owner_id}
        onChange={(v) => onConfigChange({ owner_id: v })}
        options={icUsers.map((u) => ({ value: u.id, label: u.name }))}
        placeholder="AE..."
        required
        className="w-24"
      />

      {/* Deal Type */}
      <InlineSelect
        value={config.deal_type}
        onChange={(v) => onConfigChange({ deal_type: v })}
        options={DEAL_TYPES}
        placeholder="Type..."
        required
        className="w-28"
      />

      {/* SF Stage */}
      <InlineSelect
        value={config.sf_stage}
        onChange={(v) => onConfigChange({ sf_stage: v })}
        options={SF_STAGES}
        placeholder="Stage..."
        required
        className="w-24"
      />

      {/* Forecast */}
      <InlineSelect
        value={config.sf_forecast_category}
        onChange={(v) => onConfigChange({ sf_forecast_category: v })}
        options={FORECAST_CATEGORIES}
        placeholder="FC..."
        required
        className="w-20"
      />

      {/* Close Quarter */}
      <InlineSelect
        value={config.sf_close_quarter}
        onChange={(v) => onConfigChange({ sf_close_quarter: v })}
        options={CLOSE_QUARTERS.map((q) => ({ value: q, label: q }))}
        placeholder="Close..."
        required
        className="w-18"
      />

      {/* Buying Culture */}
      <InlineSelect
        value={config.buying_culture}
        onChange={(v) => onConfigChange({ buying_culture: v })}
        options={BUYING_CULTURES}
        placeholder="Culture..."
        required
        className="w-24"
      />

      {/* CP Estimate */}
      <InlineNumber
        value={config.cp_estimate}
        onChange={(v) => onConfigChange({ cp_estimate: v })}
        placeholder="CP $"
        required
        className="w-16"
      />

      {/* Prior Contract Value — only for expansion */}
      {isExpansion(config.deal_type) && (
        <InlineNumber
          value={config.prior_contract_value}
          onChange={(v) => onConfigChange({ prior_contract_value: v })}
          placeholder="Prior $"
          required
          className="w-16"
        />
      )}

      {/* Completeness indicator */}
      {!complete && (
        <span className="shrink-0 text-[10px] text-destructive font-medium">!</span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AnalyzePage() {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [configs, setConfigs] = useState<Record<string, AccountConfig>>({});
  const [runs, setRuns] = useState<RunResult[] | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Data
  const { data: accounts, isLoading, isError, error } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => api.accounts.list(),
    staleTime: 30_000,
  });

  const { data: icUsersData, isLoading: usersLoading } = useICUsers();
  const icUsers: ICUser[] = icUsersData ?? [];

  // Initialize configs from DB data
  useEffect(() => {
    if (!accounts) return;
    setConfigs((prev) => {
      const next = { ...prev };
      for (const a of accounts) {
        if (!next[a.id]) {
          next[a.id] = configFromAccount(a);
        }
      }
      return next;
    });
  }, [accounts]);

  // Sort: has_new_calls first, then alphabetical
  const sorted = useMemo(() => {
    if (!accounts) return [];
    return [...accounts].sort((a, b) => {
      if (a.has_new_calls && !b.has_new_calls) return -1;
      if (!a.has_new_calls && b.has_new_calls) return 1;
      return a.account_name.localeCompare(b.account_name);
    });
  }, [accounts]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return sorted.filter((a) => a.account_name.toLowerCase().includes(q));
  }, [sorted, search]);

  // Selection
  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === filtered.length && filtered.length > 0) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map((a) => a.id)));
    }
  }

  const allSelected = filtered.length > 0 && selected.size === filtered.length;
  const someSelected = selected.size > 0 && !allSelected;

  // Config updates
  const handleConfigChange = useCallback((accountId: string, patch: Partial<AccountConfig>) => {
    setConfigs((prev) => ({
      ...prev,
      [accountId]: { ...prev[accountId], ...patch },
    }));
  }, []);

  // Validation — all selected accounts must have complete configs
  const selectedAccounts = useMemo(
    () => (accounts ?? []).filter((a) => selected.has(a.id)),
    [accounts, selected],
  );

  const allSelectedComplete = useMemo(
    () => selectedAccounts.every((a) => configs[a.id] && isConfigComplete(configs[a.id])),
    [selectedAccounts, configs],
  );

  const incompleteCount = useMemo(
    () => selectedAccounts.filter((a) => !configs[a.id] || !isConfigComplete(configs[a.id])).length,
    [selectedAccounts, configs],
  );

  // Analyze — update SF fields then run pipeline
  async function handleAnalyze() {
    if (selected.size === 0 || isSubmitting || !allSelectedComplete) return;

    const initialRuns: RunResult[] = selectedAccounts.map((a) => ({
      accountId: a.id,
      accountName: a.account_name,
      status: 'pending',
      runId: null,
      error: null,
    }));

    setRuns(initialRuns);
    setIsSubmitting(true);
    setSelected(new Set());

    await Promise.all(
      selectedAccounts.map(async (account, idx) => {
        setRuns((prev) =>
          prev ? prev.map((r, i) => (i === idx ? { ...r, status: 'starting' } : r)) : prev,
        );

        try {
          // Step 1: Update account SF fields
          const cfg = configs[account.id];
          await api.accounts.update(account.id, {
            sf_stage: cfg.sf_stage ? Number(cfg.sf_stage) : undefined,
            sf_forecast_category: cfg.sf_forecast_category || undefined,
            sf_close_quarter: cfg.sf_close_quarter || undefined,
            cp_estimate: cfg.cp_estimate ? Number(cfg.cp_estimate) : undefined,
            owner_id: cfg.owner_id || undefined,
            deal_type: cfg.deal_type || undefined,
            buying_culture: cfg.buying_culture || undefined,
            prior_contract_value: cfg.prior_contract_value ? Number(cfg.prior_contract_value) : undefined,
          });

          // Step 2: Start analysis
          const result: AnalysisRunResponse = await api.analyses.run(account.id);

          setRuns((prev) =>
            prev
              ? prev.map((r, i) =>
                  i === idx ? { ...r, status: 'running', runId: result.run_id } : r,
                )
              : prev,
          );
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Failed to start analysis';
          setRuns((prev) =>
            prev ? prev.map((r, i) => (i === idx ? { ...r, status: 'failed', error: message } : r)) : prev,
          );
        }
      }),
    );

    setIsSubmitting(false);
  }

  function handleNewBatch() {
    setRuns(null);
    setSelected(new Set());
  }

  // ---------------------------------------------------------------------------
  // Progress view (when runs in progress)
  // ---------------------------------------------------------------------------

  if (runs !== null) {
    const total = runs.length;
    const done = runs.filter((r) => r.status === 'completed' || r.status === 'failed').length;
    const failed = runs.filter((r) => r.status === 'failed').length;
    const allDone = done === total;

    return (
      <div className="p-6 space-y-5 max-w-[900px] mx-auto">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Analyze</h1>
            <p className="text-sm text-muted-foreground">
              {allDone
                ? `${done - failed}/${total} completed${failed > 0 ? ` · ${failed} failed` : ''}`
                : `${done}/${total} done — analysis running...`}
            </p>
          </div>
          {allDone && (
            <Button size="sm" onClick={handleNewBatch} className="bg-primary hover:bg-primary/90 min-h-[44px]">
              New Batch
            </Button>
          )}
        </div>
        <div className="rounded-lg border border-border overflow-hidden">
          {runs.map((run) => (
            <RunProgressRow key={run.accountId} run={run} />
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Selection view
  // ---------------------------------------------------------------------------

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Analyze</h1>
          <p className="text-sm text-muted-foreground">
            Select accounts, confirm SF data, then run the 10-agent analysis pipeline.
          </p>
        </div>

        <Button
          size="sm"
          disabled={selected.size === 0 || isSubmitting || !allSelectedComplete}
          onClick={handleAnalyze}
          className="bg-primary hover:bg-primary/90 min-h-[44px] gap-1.5 sm:self-start"
        >
          {isSubmitting ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Play className="size-4" />
          )}
          {selected.size > 0 ? `Analyze Selected (${selected.size})` : 'Analyze Selected'}
        </Button>
      </div>

      {/* Search + Select All */}
      {(accounts?.length ?? 0) > 0 && (
        <div className="flex items-center gap-4">
          <div className="relative max-w-sm flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Search accounts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-card border-border"
            />
          </div>
          <button
            onClick={toggleSelectAll}
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0 min-h-[44px] px-2"
          >
            <div
              className={cn(
                'size-4 rounded border transition-colors flex items-center justify-center shrink-0',
                allSelected
                  ? 'border-primary bg-primary'
                  : someSelected
                    ? 'border-primary bg-primary/30'
                    : 'border-border hover:border-primary/60',
              )}
            >
              {(allSelected || someSelected) && <Check className="size-2.5 text-white" />}
            </div>
            {allSelected ? 'Deselect all' : 'Select all'}
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading && <LoadingSkeleton />}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-4">
          <p className="text-sm font-medium text-destructive">Failed to load accounts</p>
          <p className="text-xs text-destructive/70 mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && accounts?.length === 0 && (
        <div className="rounded-lg border border-border bg-card px-6 py-12 text-center">
          <p className="text-muted-foreground">No accounts found.</p>
          <p className="text-sm text-muted-foreground mt-1">
            Add accounts via the Watchlist page and sync from Gong.
          </p>
        </div>
      )}

      {/* Account list */}
      {!isLoading && !isError && (accounts?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-border overflow-x-auto">
          {/* Column legend */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/30 min-w-fit">
            <div className="size-4 shrink-0" />
            <span className="w-36 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Account</span>
            <span className="w-24 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">AE</span>
            <span className="w-28 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Deal Type</span>
            <span className="w-24 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Stage</span>
            <span className="w-20 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Forecast</span>
            <span className="w-18 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Close Q</span>
            <span className="w-24 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Culture</span>
            <span className="w-16 shrink-0 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">CP $</span>
          </div>

          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No accounts match your search.
            </div>
          )}

          {filtered.map((account) => (
            <AccountRow
              key={account.id}
              account={account}
              config={configs[account.id] ?? configFromAccount(account)}
              isSelected={selected.has(account.id)}
              onToggle={() => toggleSelect(account.id)}
              onConfigChange={(patch) => handleConfigChange(account.id, patch)}
              icUsers={icUsers}
            />
          ))}
        </div>
      )}

      {/* Floating action bar */}
      {selected.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-3 rounded-full bg-card border border-border shadow-lg px-5 py-2.5 z-50">
          <span className="text-sm font-medium">{selected.size} selected</span>
          {incompleteCount > 0 && (
            <span className="text-xs text-destructive">
              {incompleteCount} missing fields
            </span>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="h-8 text-xs text-muted-foreground"
            onClick={() => setSelected(new Set())}
          >
            Clear
          </Button>
          <Button
            size="sm"
            onClick={handleAnalyze}
            disabled={isSubmitting || !allSelectedComplete}
            className="h-8 bg-primary hover:bg-primary/90 gap-1.5"
          >
            <Play className="size-3.5" />
            Analyze {selected.size}
          </Button>
        </div>
      )}
    </div>
  );
}
