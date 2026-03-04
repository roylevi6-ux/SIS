'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  Upload,
  CheckCircle2,
  FileText,
  Loader2,
  HardDrive,
  Play,
  Trash2,
  Eye,
  Search,
  ChevronRight,
  X,
  Info,
} from 'lucide-react';
import { useAccounts, useUploadTranscript } from '@/lib/hooks';
import { useICUsers } from '@/lib/hooks/use-admin';
import { api } from '@/lib/api';
import type {
  ICUser,
  EnrichedDriveAccount,
  EnrichedCall,
  BatchItemRequest,
  Account,
} from '@/lib/api-types';
import { AnalysisProgressDetail } from '@/components/analysis-progress-detail';
import { BatchProgressView } from '@/components/batch-progress-view';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toTitleCase(s: string): string {
  return s.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
}

function generateCloseQuarters(): string[] {
  const now = new Date();
  const currentQ = Math.ceil((now.getMonth() + 1) / 3);
  const currentY = now.getFullYear();
  const quarters: string[] = [];
  for (let i = 0; i < 5; i++) {
    const q = ((currentQ - 1 + i) % 4) + 1;
    const y = currentY + Math.floor((currentQ - 1 + i) / 4);
    quarters.push(`Q${q} ${y}`);
  }
  return quarters;
}

const DEAL_TYPES = [
  'New Logo',
  'Expansion - Upsell',
  'Expansion - Cross Sell',
  'Expansion - Both',
  'Renewal',
];

const DEAL_TYPE_ABBREV: Record<string, string> = {
  'New Logo': 'NL',
  'Expansion - Upsell': 'EX-U',
  'Expansion - Cross Sell': 'EX-X',
  'Expansion - Both': 'EX-B',
  'Renewal': 'RN',
};

const SF_STAGES = [
  { value: '1', label: '1 – Qualify' },
  { value: '2', label: '2 – Establish Business Case' },
  { value: '3', label: '3 – Scope' },
  { value: '4', label: '4 – Proposal' },
  { value: '5', label: '5 – Negotiate' },
  { value: '6', label: '6 – Contract' },
  { value: '7', label: '7 – Implement' },
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DealConfig {
  dealType: string;
  ownerId: string;
  buyingCulture: string;
  sfStage: string;
  sfForecast: string;
  sfCloseQuarter: string;
  cpEstimate: string;
}

interface QueueItem {
  accountName: string;
  drivePath: string;
  newCallCount: number;
  dealConfig: DealConfig;
  selectedCallIds: string[];
}

interface UploadResult {
  id?: string;
  token_count?: number;
  [key: string]: unknown;
}

interface ImportResult {
  account_id: string;
  account_name: string;
  imported_count: number;
  skipped_count: number;
  calls: Array<{ date: string; title: string; token_count: number | null; status: string }>;
}

// ---------------------------------------------------------------------------
// CallStatusBadge
// ---------------------------------------------------------------------------

function CallStatusBadge({ status }: { status: 'new' | 'active' | 'imported' }) {
  if (status === 'new') {
    return (
      <Badge className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs">
        NEW
      </Badge>
    );
  }
  if (status === 'active') {
    return (
      <Badge className="bg-sky-500/20 text-sky-400 border border-sky-500/30 text-xs">
        ACTIVE
      </Badge>
    );
  }
  return (
    <Badge className="bg-muted text-muted-foreground text-xs">
      IMPORTED
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Empty DealConfig
// ---------------------------------------------------------------------------

function emptyDealConfig(): DealConfig {
  return {
    dealType: '',
    ownerId: '',
    buyingCulture: 'direct',
    sfStage: '',
    sfForecast: '',
    sfCloseQuarter: '',
    cpEstimate: '',
  };
}

function dealConfigFromAccount(account: Account, icUsers: ICUser[]): DealConfig {
  // Find owner_id from ae_owner name if we have it
  let ownerId = (account.owner_id as string | undefined) ?? '';
  if (!ownerId && account.ae_owner) {
    const match = icUsers.find((u) => u.name === account.ae_owner);
    if (match) ownerId = match.id;
  }

  return {
    dealType: (account.deal_type as string | undefined) ?? '',
    ownerId,
    buyingCulture: (account.buying_culture as string | undefined) ?? 'direct',
    sfStage: '',
    sfForecast: '',
    sfCloseQuarter: '',
    cpEstimate: account.cp_estimate != null ? String(account.cp_estimate) : '',
  };
}

// ---------------------------------------------------------------------------
// InfoBanner
// ---------------------------------------------------------------------------

function InfoBanner({ newSelected, activeCallCount }: { newSelected: number; activeCallCount: number }) {
  if (newSelected === 0) return null;

  let message: string;
  if (newSelected > 0 && activeCallCount > 0) {
    const totalForAnalysis = Math.min(newSelected + activeCallCount, 5);
    const newUsed = Math.min(newSelected, totalForAnalysis - Math.min(activeCallCount, totalForAnalysis - 1));
    const activeUsed = totalForAnalysis - newUsed;
    message = `Importing ${newSelected} new call${newSelected !== 1 ? 's' : ''}. Analysis will run on the ${totalForAnalysis} most recent calls (${newUsed} new + ${activeUsed} currently active).`;
    if (newSelected > 5) {
      message = `Importing ${newSelected} new calls. Analysis will use the 5 most recent. Older calls will be stored but inactive.`;
    }
  } else {
    message = `New account. Importing ${newSelected} call${newSelected !== 1 ? 's' : ''} for first analysis.`;
    if (newSelected > 5) {
      message = `Importing ${newSelected} new calls. Analysis will use the 5 most recent. Older calls will be stored but inactive.`;
    }
  }

  return (
    <div className="flex items-start gap-2 rounded-md border border-sky-500/20 bg-sky-500/10 px-3 py-2.5 text-xs text-sky-300">
      <Info className="mt-0.5 size-3.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AccountListPanel
// ---------------------------------------------------------------------------

interface AccountListPanelProps {
  accounts: EnrichedDriveAccount[];
  selectedName: string | null;
  queuedNames: Set<string>;
  search: string;
  onSearchChange: (s: string) => void;
  onSelect: (name: string) => void;
}

function AccountListPanel({
  accounts,
  selectedName,
  queuedNames,
  search,
  onSearchChange,
  onSelect,
}: AccountListPanelProps) {
  const filtered = useMemo(
    () =>
      accounts.filter((a) =>
        toTitleCase(a.name).toLowerCase().includes(search.toLowerCase()),
      ),
    [accounts, search],
  );

  return (
    <div className="flex flex-col h-full border-r border-border">
      {/* Header */}
      <div className="px-3 py-3 border-b border-border shrink-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Accounts
        </p>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search..."
            className="h-8 pl-8 text-xs bg-muted/30"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <p className="text-xs text-muted-foreground px-3 py-4">No accounts found.</p>
        ) : (
          filtered.map((account) => {
            const isSelected = account.name === selectedName;
            const isQueued = queuedNames.has(account.name);
            const displayName = toTitleCase(account.name);

            return (
              <button
                key={account.name}
                onClick={() => onSelect(account.name)}
                className={[
                  'w-full flex items-center gap-2 px-3 py-2.5 text-left transition-colors',
                  'hover:bg-accent/10',
                  isSelected
                    ? 'border-l-2 border-accent bg-accent/5'
                    : 'border-l-2 border-transparent',
                ].join(' ')}
              >
                {/* Queued checkmark */}
                <div className="shrink-0 size-4 flex items-center justify-center">
                  {isQueued && <CheckCircle2 className="size-3.5 text-emerald-400" />}
                </div>

                {/* Name */}
                <span className="flex-1 min-w-0 truncate text-sm">{displayName}</span>

                {/* New count badge */}
                {account.new_count > 0 ? (
                  <Badge className="shrink-0 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs px-1.5 py-0">
                    {account.new_count} new
                  </Badge>
                ) : (
                  <span className="shrink-0 text-xs text-muted-foreground">Up to date</span>
                )}

                <ChevronRight className="shrink-0 size-3.5 text-muted-foreground" />
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AccountDetailPanel
// ---------------------------------------------------------------------------

interface AccountDetailPanelProps {
  accountName: string | null;
  calls: EnrichedCall[];
  loadingCalls: boolean;
  selectedCallIds: Set<string>;
  onToggleCall: (id: string) => void;
  dealConfig: DealConfig;
  onDealConfigChange: (updates: Partial<DealConfig>) => void;
  onAddToQueue: () => void;
  icUsers: ICUser[];
}

function AccountDetailPanel({
  accountName,
  calls,
  loadingCalls,
  selectedCallIds,
  onToggleCall,
  dealConfig,
  onDealConfigChange,
  onAddToQueue,
  icUsers,
}: AccountDetailPanelProps) {
  const newCalls = useMemo(() => calls.filter((c) => c.status === 'new'), [calls]);
  const activeCalls = useMemo(() => calls.filter((c) => c.status === 'active'), [calls]);
  const newSelected = useMemo(
    () => newCalls.filter((c) => c.gong_call_id && selectedCallIds.has(c.gong_call_id)).length,
    [newCalls, selectedCallIds],
  );

  const configComplete =
    dealConfig.dealType !== '' &&
    dealConfig.ownerId !== '' &&
    dealConfig.sfStage !== '' &&
    dealConfig.sfForecast !== '' &&
    dealConfig.sfCloseQuarter !== '' &&
    dealConfig.cpEstimate !== '';

  const canAdd = newSelected > 0 && configComplete;

  if (!accountName) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
        <p className="text-sm text-muted-foreground">
          Select an account from the left panel to view its calls.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-w-0 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Calls for
        </p>
        <h3 className="text-base font-semibold">{toTitleCase(accountName)}</h3>
        {!loadingCalls && calls.length > 0 && (
          <p className="text-xs text-muted-foreground">
            {calls.length} total &middot; {newCalls.length} new &middot; {activeCalls.length} active
          </p>
        )}
      </div>

      {/* Calls section — scrollable */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {loadingCalls ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="size-4 animate-spin" />
            Loading calls...
          </div>
        ) : calls.length === 0 ? (
          <p className="text-sm text-muted-foreground">No calls found for this account.</p>
        ) : (
          <>
            <InfoBanner newSelected={newSelected} activeCallCount={activeCalls.length} />

            <div className="border border-border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead className="w-24">Date</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead className="w-20">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {calls.map((call, i) => {
                    const callId = call.gong_call_id ?? `__idx_${i}`;
                    const isNew = call.status === 'new';
                    const isChecked = isNew && selectedCallIds.has(callId);

                    return (
                      <TableRow
                        key={callId}
                        className={isChecked ? 'bg-accent/5' : ''}
                      >
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={isChecked}
                            disabled={!isNew}
                            onChange={() => isNew && onToggleCall(callId)}
                            className="size-4 rounded border-border accent-emerald-500 disabled:opacity-30"
                          />
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {call.date}
                        </TableCell>
                        <TableCell className="whitespace-normal text-sm">
                          {call.title || '—'}
                        </TableCell>
                        <TableCell>
                          <CallStatusBadge status={call.status} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </div>

      {/* Deal Config — pinned at bottom */}
      {!loadingCalls && calls.length > 0 && (
        <div className="border-t border-border px-4 py-3 space-y-3 shrink-0 bg-card">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Deal Config
          </p>

          {/* Row 1: Auto-filled */}
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Deal Type</label>
              <Select
                value={dealConfig.dealType}
                onValueChange={(v) => onDealConfigChange({ dealType: v })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Select" />
                </SelectTrigger>
                <SelectContent>
                  {DEAL_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">AE Owner</label>
              <Select
                value={dealConfig.ownerId}
                onValueChange={(v) => onDealConfigChange({ ownerId: v })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Select AE" />
                </SelectTrigger>
                <SelectContent>
                  {icUsers.map((ic) => (
                    <SelectItem key={ic.id} value={ic.id}>
                      {ic.name}{ic.team_name ? ` (${ic.team_name})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Buying Culture</label>
              <Select
                value={dealConfig.buyingCulture}
                onValueChange={(v) => onDealConfigChange({ buyingCulture: v })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="direct">Direct</SelectItem>
                  <SelectItem value="proxy_delegated">Proxy-Delegated</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Row 2: Required pipeline fields */}
          <div className="grid grid-cols-4 gap-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">SF Stage *</label>
              <Select
                value={dealConfig.sfStage}
                onValueChange={(v) => onDealConfigChange({ sfStage: v })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {SF_STAGES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">SF Forecast *</label>
              <Select
                value={dealConfig.sfForecast}
                onValueChange={(v) => onDealConfigChange({ sfForecast: v })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {['Commit', 'Realistic', 'Upside', 'At Risk'].map((f) => (
                    <SelectItem key={f} value={f}>{f}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Close Quarter *</label>
              <Select
                value={dealConfig.sfCloseQuarter}
                onValueChange={(v) => onDealConfigChange({ sfCloseQuarter: v })}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {generateCloseQuarters().map((q) => (
                    <SelectItem key={q} value={q}>{q}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">CP Estimate *</label>
              <Input
                type="number"
                placeholder="$"
                value={dealConfig.cpEstimate}
                onChange={(e) => onDealConfigChange({ cpEstimate: e.target.value })}
                className="h-8 text-xs"
              />
            </div>
          </div>

          <Button
            onClick={onAddToQueue}
            disabled={!canAdd}
            size="sm"
            className="w-full"
          >
            Add to Queue
            <ChevronRight className="size-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// QueuePanel
// ---------------------------------------------------------------------------

interface QueuePanelProps {
  queue: QueueItem[];
  onRemove: (accountName: string) => void;
  onRunAnalysis: () => void;
  isRunning: boolean;
}

function QueuePanel({ queue, onRemove, onRunAnalysis, isRunning }: QueuePanelProps) {
  return (
    <div className="flex flex-col h-full border-l border-border">
      {/* Header */}
      <div className="px-3 py-3 border-b border-border shrink-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Queue ({queue.length})
        </p>
      </div>

      {/* Queue items */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {queue.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-6">
            Select accounts and add them to the queue
          </p>
        ) : (
          queue.map((item) => {
            const abbrev = DEAL_TYPE_ABBREV[item.dealConfig.dealType] ?? item.dealConfig.dealType;
            return (
              <div
                key={item.accountName}
                className="bg-muted/50 border border-border rounded-lg px-3 py-2.5 flex items-start justify-between gap-2"
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold truncate">
                    {toTitleCase(item.accountName)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {item.newCallCount} new &middot; {abbrev}
                  </p>
                </div>
                <button
                  onClick={() => onRemove(item.accountName)}
                  className="shrink-0 text-muted-foreground hover:text-foreground mt-0.5"
                  aria-label="Remove from queue"
                >
                  <X className="size-4" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Run button */}
      <div className="px-3 pb-4 shrink-0">
        <Button
          onClick={onRunAnalysis}
          disabled={queue.length === 0 || isRunning}
          className="w-full"
        >
          {isRunning ? (
            <>
              <Loader2 className="size-4 animate-spin mr-2" />
              Running...
            </>
          ) : (
            <>
              <Play className="size-4 mr-2" />
              Run Analysis ({queue.length} account{queue.length !== 1 ? 's' : ''})
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// LocalFolderModal
// ---------------------------------------------------------------------------

function LocalFolderModal({ onClose, onImportComplete }: { onClose: () => void; onImportComplete?: () => void }) {
  const [folderPath, setFolderPath] = useState('');
  const [pathValidated, setPathValidated] = useState(false);
  const [pathMessage, setPathMessage] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const [driveAccounts, setDriveAccounts] = useState<Array<{ name: string; path: string; call_count: number }>>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);

  const [selectedAccount, setSelectedAccount] = useState<{ name: string; path: string; call_count: number } | null>(null);
  const [recentCalls, setRecentCalls] = useState<Array<{ date: string; title: string; has_transcript: boolean }>>([]);
  const [isLoadingCalls, setIsLoadingCalls] = useState(false);

  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState('');

  const [maxCalls, setMaxCalls] = useState<number>(5);

  const [analysisRunId, setAnalysisRunId] = useState<string | null>(null);
  const [analysisAccountId, setAnalysisAccountId] = useState<string | null>(null);

  const [dealType, setDealType] = useState<string>('');
  const [buyingCulture, setBuyingCulture] = useState<string>('direct');
  const [cpEstimate, setCpEstimate] = useState<string>('');
  const [selectedOwnerId, setSelectedOwnerId] = useState<string>('');
  const [selectedIC, setSelectedIC] = useState<ICUser | null>(null);
  const [sfStage, setSfStage] = useState<string>('');
  const [sfForecast, setSfForecast] = useState<string>('');
  const [sfCloseQuarter, setSfCloseQuarter] = useState<string>('');

  const { data: icUsers = [] } = useICUsers();

  function handleICSelect(userId: string) {
    setSelectedOwnerId(userId);
    const ic = icUsers.find((u: ICUser) => u.id === userId) ?? null;
    setSelectedIC(ic);
  }

  async function handleScanFolder() {
    if (!folderPath.trim()) return;
    setIsValidating(true);
    setPathValidated(false);
    setPathMessage('');
    setDriveAccounts([]);
    setSelectedAccount(null);
    setRecentCalls([]);
    setImportResult(null);

    try {
      const result = await api.gdrive.validate(folderPath.trim());
      setPathValidated(result.is_valid);
      setPathMessage(result.message);

      if (result.is_valid) {
        setIsLoadingAccounts(true);
        const accounts = await api.gdrive.listAccounts(folderPath.trim());
        setDriveAccounts(accounts);
        setIsLoadingAccounts(false);
      }
    } catch (err) {
      setPathMessage(err instanceof Error ? err.message : 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  }

  async function handleSelectAccount(accountName: string) {
    const account = driveAccounts.find((a) => a.name === accountName);
    if (!account) return;

    setSelectedAccount(account);
    setRecentCalls([]);
    setImportResult(null);
    setImportError('');
    setIsLoadingCalls(true);

    try {
      const calls = await api.gdrive.listCalls(account.name, account.path, maxCalls);
      setRecentCalls(calls as unknown as Array<{ date: string; title: string; has_transcript: boolean }>);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Failed to load calls');
    } finally {
      setIsLoadingCalls(false);
    }
  }

  async function handleImport() {
    if (!selectedAccount) return;
    if (!selectedOwnerId) {
      setImportError('Please select an AE before importing');
      return;
    }
    setIsImporting(true);
    setImportError('');
    setImportResult(null);
    setAnalysisRunId(null);
    setAnalysisAccountId(null);

    try {
      const dealArgs = {
        deal_type: dealType || undefined,
        buying_culture: buyingCulture || 'direct',
        cp_estimate: cpEstimate ? parseFloat(cpEstimate) : undefined,
        owner_id: selectedOwnerId || undefined,
        sf_stage: sfStage ? parseInt(sfStage) : undefined,
        sf_forecast_category: sfForecast || undefined,
        sf_close_quarter: sfCloseQuarter || undefined,
      };
      const result = await api.gdrive.import(toTitleCase(selectedAccount.name), selectedAccount.path, maxCalls, dealArgs);
      setImportResult(result as unknown as ImportResult);
      onImportComplete?.();

      const analysisResult = await api.analyses.run((result as unknown as ImportResult).account_id);
      setAnalysisRunId(analysisResult.run_id);
      setAnalysisAccountId((result as unknown as ImportResult).account_id);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Import & Analysis failed');
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-3xl max-h-[80vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>Import from Local Folder</CardTitle>
            <CardDescription>
              Enter the path to any local folder containing account sub-folders with Gong JSON exports.
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="shrink-0 -mt-1 -mr-1">
            <X className="size-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-5">
          {analysisRunId && analysisAccountId ? (
            <div className="space-y-4">
              {importResult && (
                <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-4 text-emerald-400 shrink-0" />
                    <p className="text-sm font-medium text-emerald-300">
                      Imported {importResult.imported_count} call{importResult.imported_count !== 1 ? 's' : ''} for {importResult.account_name}
                      {importResult.skipped_count > 0 && (
                        <span className="text-amber-400"> ({importResult.skipped_count} skipped)</span>
                      )}
                    </p>
                  </div>
                </div>
              )}
              <AnalysisProgressDetail runId={analysisRunId} accountId={analysisAccountId} />
            </div>
          ) : (
            <>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="local-path">Folder Path</label>
                <div className="flex gap-2">
                  <Input
                    id="local-path"
                    placeholder="/path/to/transcripts"
                    value={folderPath}
                    onChange={(e) => {
                      setFolderPath(e.target.value);
                      setPathValidated(false);
                      setDriveAccounts([]);
                      setSelectedAccount(null);
                    }}
                    className="flex-1"
                  />
                  <Button onClick={handleScanFolder} disabled={!folderPath.trim() || isValidating} variant="secondary">
                    {isValidating ? <Loader2 className="size-4 animate-spin" /> : 'Scan'}
                  </Button>
                </div>
                {pathMessage && (
                  <p className={`text-sm ${pathValidated ? 'text-emerald-400' : 'text-destructive'}`}>
                    {pathValidated ? '✓' : '✗'} {pathMessage}
                  </p>
                )}
              </div>

              {(isLoadingAccounts || driveAccounts.length > 0) && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium">Select Account</label>
                  {isLoadingAccounts ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="size-4 animate-spin" /> Scanning folders...
                    </div>
                  ) : (
                    <Select onValueChange={handleSelectAccount}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Choose an account to import" />
                      </SelectTrigger>
                      <SelectContent>
                        {driveAccounts.map((a) => (
                          <SelectItem key={a.name} value={a.name}>
                            {toTitleCase(a.name)} ({a.call_count} calls)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              )}

              {selectedAccount && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Max calls to import</label>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    value={maxCalls}
                    onChange={(e) => {
                      const v = parseInt(e.target.value, 10);
                      if (!isNaN(v) && v >= 1 && v <= 20) setMaxCalls(v);
                    }}
                    className="w-24"
                  />
                </div>
              )}

              {isLoadingCalls && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Loading recent calls...
                </div>
              )}

              {recentCalls.length > 0 && selectedAccount && (
                <div className="space-y-3">
                  <p className="text-sm font-medium">
                    {recentCalls.length} most recent calls for <strong>{toTitleCase(selectedAccount.name)}</strong>:
                  </p>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Title</TableHead>
                        <TableHead className="text-center">Transcript</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {recentCalls.map((call, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-mono text-xs">{call.date}</TableCell>
                          <TableCell className="whitespace-normal">{call.title}</TableCell>
                          <TableCell className="text-center">
                            {call.has_transcript ? (
                              <Badge className="bg-emerald-900/30 text-emerald-300">✓</Badge>
                            ) : (
                              <Badge variant="secondary">—</Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  <div className="space-y-4 py-4 border-y border-border/50">
                    <h3 className="text-sm font-semibold">Deal Configuration</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium">Deal Type</label>
                        <Select value={dealType} onValueChange={setDealType}>
                          <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                          <SelectContent>
                            {DEAL_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium">Buying Culture</label>
                        <Select value={buyingCulture} onValueChange={setBuyingCulture}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="direct">Direct</SelectItem>
                            <SelectItem value="proxy_delegated">Proxy-Delegated</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium">CP Estimate ($)</label>
                        <Input type="number" min="0" step="1000" placeholder="Optional" value={cpEstimate} onChange={e => setCpEstimate(e.target.value)} />
                      </div>
                      <div className="col-span-2 space-y-1.5">
                        <label className="text-xs font-medium">AE Owner</label>
                        <Select value={selectedOwnerId} onValueChange={handleICSelect}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Select AE owner" />
                          </SelectTrigger>
                          <SelectContent>
                            {icUsers.map((ic: ICUser) => (
                              <SelectItem key={ic.id} value={ic.id}>
                                {ic.name}{ic.team_name ? ` (${ic.team_name})` : ''}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      {selectedIC && (
                        <>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-muted-foreground">Team Lead</label>
                            <p className="text-sm">{selectedIC.team_lead || '—'}</p>
                          </div>
                          <div className="space-y-1">
                            <label className="text-xs font-medium text-muted-foreground">Team Name</label>
                            <p className="text-sm">{selectedIC.team_name || '—'}</p>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <h4 className="text-sm font-medium">SF Indication</h4>
                      <p className="text-xs text-muted-foreground">Salesforce values at day of last analysis</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs font-medium">SF Stage</label>
                        <Select value={sfStage} onValueChange={setSfStage}>
                          <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select stage" /></SelectTrigger>
                          <SelectContent>
                            {SF_STAGES.map((s) => (
                              <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-medium">SF Forecast</label>
                        <Select value={sfForecast} onValueChange={setSfForecast}>
                          <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select forecast" /></SelectTrigger>
                          <SelectContent>
                            {['Commit', 'Realistic', 'Upside', 'At Risk'].map((f) => (
                              <SelectItem key={f} value={f}>{f}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-medium">Close Quarter</label>
                        <Select value={sfCloseQuarter} onValueChange={setSfCloseQuarter}>
                          <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select quarter" /></SelectTrigger>
                          <SelectContent>
                            {generateCloseQuarters().map((q) => (
                              <SelectItem key={q} value={q}>{q}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

                  <Button onClick={handleImport} disabled={isImporting || !selectedOwnerId} className="w-full">
                    {isImporting ? (
                      <><Loader2 className="size-4 animate-spin mr-2" /> Importing & Analyzing...</>
                    ) : (
                      <><Play className="size-4 mr-2" /> Import & Run Analysis</>
                    )}
                  </Button>
                </div>
              )}

              {importError && (
                <div className="rounded-md border border-destructive bg-destructive/5 p-3">
                  <p className="text-sm text-destructive">{importError}</p>
                </div>
              )}

              {importResult && !analysisRunId && (
                <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="size-5 text-emerald-400 mt-0.5 shrink-0" />
                    <p className="font-medium text-emerald-300">
                      Imported {importResult.imported_count} new call{importResult.imported_count !== 1 ? 's' : ''} for {importResult.account_name}
                      {importResult.skipped_count > 0 && (
                        <span className="text-amber-400"> ({importResult.skipped_count} already imported)</span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ManualUploadModal
// ---------------------------------------------------------------------------

function ManualUploadModal({ onClose }: { onClose: () => void }) {
  const { data: accountsData, isLoading: accountsLoading } = useAccounts();
  const accounts = (accountsData ?? []) as Array<{ id: string; account_name: string }>;
  const uploadMutation = useUploadTranscript();

  const [accountId, setAccountId] = useState('');
  const [callDate, setCallDate] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('');
  const [rawText, setRawText] = useState('');
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  const isValid = accountId !== '' && callDate !== '' && rawText.trim() !== '';

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;

    setUploadResult(null);
    uploadMutation.mutate(
      {
        account_id: accountId,
        raw_text: rawText,
        call_date: callDate,
        duration_minutes: durationMinutes ? Number(durationMinutes) : null,
      },
      {
        onSuccess: (data) => {
          setUploadResult(data as unknown as UploadResult);
          setRawText('');
          setDurationMinutes('');
        },
      },
    );
  }

  function handleReset() {
    setUploadResult(null);
    uploadMutation.reset();
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>Paste Transcript</CardTitle>
            <CardDescription>
              Paste the full call transcript and fill in the metadata.
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="shrink-0 -mt-1 -mr-1">
            <X className="size-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="account-select">Account</label>
              <Select
                value={accountId}
                onValueChange={(v) => { setAccountId(v); handleReset(); }}
                disabled={accountsLoading}
              >
                <SelectTrigger id="account-select" className="w-full">
                  <SelectValue placeholder={accountsLoading ? 'Loading accounts...' : 'Select an account'} />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((a) => (
                    <SelectItem key={a.id} value={a.id}>{a.account_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="call-date">Call Date</label>
              <Input id="call-date" type="date" value={callDate} onChange={(e) => setCallDate(e.target.value)} required />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="duration">Duration (mins)</label>
              <Input id="duration" type="number" min={1} placeholder="Optional" value={durationMinutes} onChange={(e) => setDurationMinutes(e.target.value)} />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="transcript-text">Transcript Text</label>
              <Textarea
                id="transcript-text"
                placeholder="Paste the full call transcript here..."
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={12}
                className="min-h-[200px] font-mono text-xs"
                required
              />
            </div>

            <Button type="submit" disabled={!isValid || uploadMutation.isPending} className="w-full sm:w-auto">
              {uploadMutation.isPending ? (
                <><Upload className="size-4 animate-pulse mr-2" />Uploading...</>
              ) : (
                <><Upload className="size-4 mr-2" />Upload Transcript</>
              )}
            </Button>

            {uploadMutation.isError && (
              <div className="rounded-md border border-destructive bg-destructive/5 p-3">
                <p className="text-sm text-destructive">
                  {uploadMutation.error instanceof Error ? uploadMutation.error.message : 'Upload failed. Please try again.'}
                </p>
              </div>
            )}

            {uploadResult && (
              <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-start gap-2">
                <CheckCircle2 className="size-4 text-emerald-400 mt-0.5 shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-emerald-300">Transcript uploaded successfully!</p>
                  {uploadResult.token_count != null && (
                    <p className="text-emerald-400">Token count: {uploadResult.token_count.toLocaleString()}</p>
                  )}
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PastUploadsTable
// ---------------------------------------------------------------------------

interface PastUploadAccount {
  id: string;
  account_name: string;
  health_score: number | null;
  inferred_stage: number | null;
  stage_name: string | null;
  ai_forecast_category: string | null;
  last_assessed: string | null;
}

function PastUploadsTable({ refreshKey }: { refreshKey: number }) {
  const [accounts, setAccounts] = useState<PastUploadAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadAccounts = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.accounts.list();
      setAccounts(data as unknown as PastUploadAccount[]);
    } catch {
      // Silently fail — list is supplementary
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts, refreshKey]);

  async function handleDelete(account: PastUploadAccount) {
    if (!window.confirm(`Delete "${account.account_name}" and all analysis data?`)) return;
    setDeletingId(account.id);
    try {
      await api.accounts.delete(account.id);
      setAccounts((prev) => prev.filter((a) => a.id !== account.id));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeletingId(null);
    }
  }

  function healthBadge(score: number | null) {
    if (score == null) return <Badge variant="secondary">--</Badge>;
    if (score >= 70) return <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">{score}</Badge>;
    if (score >= 40) return <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">{score}</Badge>;
    return <Badge className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">{score}</Badge>;
  }

  return (
    <Card className="mt-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Past Uploads</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="size-4 animate-spin" /> Loading accounts...
          </div>
        ) : accounts.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">No accounts imported yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account Name</TableHead>
                <TableHead className="text-center">Health</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Forecast</TableHead>
                <TableHead>Last Analyzed</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((acct) => (
                <TableRow key={acct.id}>
                  <TableCell className="font-medium">{acct.account_name}</TableCell>
                  <TableCell className="text-center">{healthBadge(acct.health_score)}</TableCell>
                  <TableCell className="text-sm">{acct.stage_name ?? '--'}</TableCell>
                  <TableCell className="text-sm">{acct.ai_forecast_category ?? '--'}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {acct.last_assessed ? new Date(acct.last_assessed).toLocaleDateString() : 'Not analyzed'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button asChild variant="ghost" size="sm">
                        <Link href={`/deals/${acct.id}`}>
                          <Eye className="size-4" />
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(acct)}
                        disabled={deletingId === acct.id}
                        className="text-destructive hover:text-destructive"
                      >
                        {deletingId === acct.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Trash2 className="size-4" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Page: UploadPage
// ---------------------------------------------------------------------------

export default function UploadPage() {
  // Drive scanning
  const [drivePath, setDrivePath] = useState('');
  const [scanning, setScanning] = useState(false);
  const [driveAccounts, setDriveAccounts] = useState<EnrichedDriveAccount[]>([]);
  const [scanError, setScanError] = useState('');
  const [accountSearch, setAccountSearch] = useState('');

  // Account selection
  const [selectedAccountName, setSelectedAccountName] = useState<string | null>(null);
  const [accountCalls, setAccountCalls] = useState<EnrichedCall[]>([]);
  const [loadingCalls, setLoadingCalls] = useState(false);
  const [selectedCallIds, setSelectedCallIds] = useState<Set<string>>(new Set());

  // Deal config
  const [dealConfig, setDealConfig] = useState<DealConfig>(emptyDealConfig());

  // Queue
  const [queue, setQueue] = useState<QueueItem[]>([]);

  // Batch run
  const [batchId, setBatchId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState('');

  // Modals
  const [showLocalModal, setShowLocalModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);

  // Past uploads refresh
  const [refreshKey, setRefreshKey] = useState(0);

  const { data: icUsers = [] } = useICUsers();

  // Auto-load drive path on mount
  useEffect(() => {
    api.gdrive.config().then((cfg) => {
      if (cfg.path) {
        setDrivePath(cfg.path);
      }
    }).catch(() => { /* ignore */ });
  }, []);

  // Scan drive
  const handleScan = useCallback(async () => {
    if (!drivePath.trim()) return;
    setScanning(true);
    setScanError('');
    setDriveAccounts([]);
    setSelectedAccountName(null);
    setAccountCalls([]);

    try {
      const result = await api.gdrive.validate(drivePath.trim());
      if (!result.is_valid) {
        setScanError(result.message);
        return;
      }
      const accounts = await api.gdrive.listAccounts(drivePath.trim());
      setDriveAccounts(accounts);
    } catch (err) {
      setScanError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  }, [drivePath]);

  // Select account
  const handleSelectAccount = useCallback(async (name: string) => {
    setSelectedAccountName(name);
    setAccountCalls([]);
    setSelectedCallIds(new Set());
    setDealConfig(emptyDealConfig());
    setLoadingCalls(true);

    const driveAccount = driveAccounts.find((a) => a.name === name);
    if (!driveAccount) {
      setLoadingCalls(false);
      return;
    }

    try {
      const { calls } = await api.gdrive.callsStatus(
        driveAccount.path,
        driveAccount.name,
        driveAccount.db_account_id ?? undefined,
      );
      setAccountCalls(calls);

      // Auto-select NEW calls
      const newIds = new Set(
        calls
          .filter((c) => c.status === 'new' && c.gong_call_id)
          .map((c) => c.gong_call_id as string),
      );
      setSelectedCallIds(newIds);

      // Auto-fill deal config from existing DB account
      if (driveAccount.db_account_id) {
        try {
          const dbAccount = await api.accounts.get(driveAccount.db_account_id);
          setDealConfig(dealConfigFromAccount(dbAccount, icUsers as ICUser[]));
        } catch {
          // Not critical — just leave empty
        }
      }
    } catch (err) {
      console.error('Failed to load calls:', err);
    } finally {
      setLoadingCalls(false);
    }
  }, [driveAccounts, icUsers]);

  // Toggle call selection
  const handleToggleCall = useCallback((callId: string) => {
    setSelectedCallIds((prev) => {
      const next = new Set(prev);
      if (next.has(callId)) {
        next.delete(callId);
      } else {
        next.add(callId);
      }
      return next;
    });
  }, []);

  // Update deal config
  const handleDealConfigChange = useCallback((updates: Partial<DealConfig>) => {
    setDealConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  // Add to queue
  const handleAddToQueue = useCallback(() => {
    if (!selectedAccountName) return;
    const driveAccount = driveAccounts.find((a) => a.name === selectedAccountName);
    if (!driveAccount) return;

    const newCallCount = accountCalls.filter(
      (c) => c.status === 'new' && c.gong_call_id && selectedCallIds.has(c.gong_call_id),
    ).length;

    const item: QueueItem = {
      accountName: selectedAccountName,
      drivePath: driveAccount.path,
      newCallCount,
      dealConfig: { ...dealConfig },
      selectedCallIds: Array.from(selectedCallIds),
    };

    setQueue((prev) => {
      // Replace if already in queue
      const exists = prev.findIndex((q) => q.accountName === selectedAccountName);
      if (exists >= 0) {
        const next = [...prev];
        next[exists] = item;
        return next;
      }
      return [...prev, item];
    });

    // Clear the detail panel
    setSelectedAccountName(null);
    setAccountCalls([]);
    setSelectedCallIds(new Set());
    setDealConfig(emptyDealConfig());
  }, [selectedAccountName, driveAccounts, accountCalls, selectedCallIds, dealConfig]);

  // Remove from queue
  const handleRemoveFromQueue = useCallback((accountName: string) => {
    setQueue((prev) => prev.filter((q) => q.accountName !== accountName));
  }, []);

  // Run analysis
  const handleRunAnalysis = useCallback(async () => {
    if (queue.length === 0) return;
    setIsRunning(true);
    setRunError('');

    try {
      const items: BatchItemRequest[] = queue.map((q) => ({
        account_name: toTitleCase(q.accountName),
        drive_path: q.drivePath,
        max_calls: Math.max(q.selectedCallIds.length, 5),
        deal_type: q.dealConfig.dealType || undefined,
        buying_culture: q.dealConfig.buyingCulture,
        owner_id: q.dealConfig.ownerId || undefined,
        sf_stage: q.dealConfig.sfStage ? parseInt(q.dealConfig.sfStage) : undefined,
        sf_forecast_category: q.dealConfig.sfForecast || undefined,
        sf_close_quarter: q.dealConfig.sfCloseQuarter || undefined,
        cp_estimate: q.dealConfig.cpEstimate ? parseFloat(q.dealConfig.cpEstimate) : undefined,
      }));

      const result = await api.analyses.batch(items);
      sessionStorage.setItem('sis_batch_id', result.batch_id);
      setBatchId(result.batch_id);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Batch submission failed');
    } finally {
      setIsRunning(false);
    }
  }, [queue]);

  // Dismiss batch progress
  const handleBatchDismiss = useCallback(() => {
    setBatchId(null);
    setQueue([]);
    sessionStorage.removeItem('sis_batch_id');
    setRefreshKey((k) => k + 1);
  }, []);

  const queuedNames = useMemo(
    () => new Set(queue.map((q) => q.accountName)),
    [queue],
  );

  // Show BatchProgressView when running
  if (batchId) {
    return (
      <div className="p-6 max-w-full">
        <BatchProgressView batchId={batchId} onDismiss={handleBatchDismiss} />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-full space-y-4">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight mb-0.5">Recording Browser</h1>
        <p className="text-sm text-muted-foreground">
          Browse your Google Drive, select accounts and calls, configure deals, then run batch analysis.
        </p>
      </div>

      {/* Drive path bar */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="~/Library/CloudStorage/GoogleDrive-.../My Drive/Transcripts"
          value={drivePath}
          onChange={(e) => setDrivePath(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleScan()}
          className="flex-1 h-9 text-sm"
        />
        <Button
          onClick={handleScan}
          disabled={!drivePath.trim() || scanning}
          variant="secondary"
          size="sm"
          className="h-9"
        >
          {scanning ? <Loader2 className="size-4 animate-spin" /> : 'Scan'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-9"
          onClick={() => setShowLocalModal(true)}
        >
          <HardDrive className="size-4 mr-1.5" />
          Local
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-9"
          onClick={() => setShowManualModal(true)}
        >
          <FileText className="size-4 mr-1.5" />
          Manual
        </Button>
      </div>

      {scanError && (
        <div className="rounded-md border border-destructive bg-destructive/5 px-3 py-2">
          <p className="text-sm text-destructive">{scanError}</p>
        </div>
      )}

      {runError && (
        <div className="rounded-md border border-destructive bg-destructive/5 px-3 py-2">
          <p className="text-sm text-destructive">{runError}</p>
        </div>
      )}

      {/* 3-panel browser */}
      {(driveAccounts.length > 0 || scanning) && (
        <Card className="overflow-hidden">
          <div
            className="grid min-h-[600px]"
            style={{ gridTemplateColumns: '220px 1fr 260px' }}
          >
            {/* Left: Account list */}
            <AccountListPanel
              accounts={driveAccounts}
              selectedName={selectedAccountName}
              queuedNames={queuedNames}
              search={accountSearch}
              onSearchChange={setAccountSearch}
              onSelect={handleSelectAccount}
            />

            {/* Middle: Account detail */}
            <AccountDetailPanel
              accountName={selectedAccountName}
              calls={accountCalls}
              loadingCalls={loadingCalls}
              selectedCallIds={selectedCallIds}
              onToggleCall={handleToggleCall}
              dealConfig={dealConfig}
              onDealConfigChange={handleDealConfigChange}
              onAddToQueue={handleAddToQueue}
              icUsers={icUsers as ICUser[]}
            />

            {/* Right: Queue */}
            <QueuePanel
              queue={queue}
              onRemove={handleRemoveFromQueue}
              onRunAnalysis={handleRunAnalysis}
              isRunning={isRunning}
            />
          </div>
        </Card>
      )}

      {/* Empty state when no scan yet */}
      {driveAccounts.length === 0 && !scanning && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Search className="size-10 text-muted-foreground/40 mb-3" />
            <p className="text-sm font-medium text-muted-foreground">
              Enter your Google Drive path above and click Scan
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Or use Local / Manual buttons to import transcripts another way
            </p>
          </CardContent>
        </Card>
      )}

      {/* Past uploads */}
      <PastUploadsTable refreshKey={refreshKey} />

      {/* Modals */}
      {showLocalModal && (
        <LocalFolderModal
          onClose={() => setShowLocalModal(false)}
          onImportComplete={() => setRefreshKey((k) => k + 1)}
        />
      )}
      {showManualModal && (
        <ManualUploadModal onClose={() => setShowManualModal(false)} />
      )}
    </div>
  );
}
