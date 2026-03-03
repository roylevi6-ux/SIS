'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Upload, CheckCircle2, FolderOpen, FileText, Loader2, HardDrive, Play, Trash2, Eye } from 'lucide-react';
import { useAccounts, useUploadTranscript } from '@/lib/hooks';
import { useICUsers } from '@/lib/hooks/use-admin';
import { api } from '@/lib/api';
import type { ICUser } from '@/lib/api-types';
import { AnalysisProgressDetail } from '@/components/analysis-progress-detail';
import { BatchProgressView } from '@/components/batch-progress-view';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

const DEAL_TYPES = [
  "New Logo",
  "Expansion - Upsell",
  "Expansion - Cross Sell",
  "Expansion - Both",
  "Renewal",
];

interface Account {
  id: string;
  account_name: string;
  [key: string]: unknown;
}

interface UploadResult {
  id?: string;
  token_count?: number;
  [key: string]: unknown;
}

interface DriveAccount {
  name: string;
  path: string;
  call_count: number;
}

interface DriveCall {
  date: string;
  title: string;
  has_transcript: boolean;
}

interface ImportResult {
  account_id: string;
  account_name: string;
  imported_count: number;
  skipped_count: number;
  calls: Array<{ date: string; title: string; token_count: number | null; status: string }>;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function UploadPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const refreshAccounts = useCallback(() => setRefreshKey((k) => k + 1), []);

  return (
    <div className="p-6 max-w-full">
      <h1 className="text-2xl font-bold tracking-tight mb-1">
        Upload Transcript
      </h1>
      <p className="text-sm text-muted-foreground mb-6">
        Import transcripts from Google Drive, a local folder, or paste manually.
      </p>

      <Tabs defaultValue="drive" className="w-full">
        <TabsList className="w-full">
          <TabsTrigger value="drive" className="flex-1 gap-1.5">
            <FolderOpen className="size-4" />
            Google Drive
          </TabsTrigger>
          <TabsTrigger value="local" className="flex-1 gap-1.5">
            <HardDrive className="size-4" />
            Local Folder
          </TabsTrigger>
          <TabsTrigger value="manual" className="flex-1 gap-1.5">
            <FileText className="size-4" />
            Paste Text
          </TabsTrigger>
        </TabsList>

        <TabsContent value="drive" className="mt-4">
          <DriveImportTab onImportComplete={refreshAccounts} />
        </TabsContent>

        <TabsContent value="local" className="mt-4">
          <LocalFolderTab onImportComplete={refreshAccounts} />
        </TabsContent>

        <TabsContent value="manual" className="mt-4">
          <ManualUploadTab />
        </TabsContent>
      </Tabs>

      <PastUploadsTable refreshKey={refreshKey} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 1: Google Drive Import
// ---------------------------------------------------------------------------

interface BatchRow {
  account: DriveAccount;
  selected: boolean;
  maxCalls: number;
  dealType: string;
  buyingCulture: string;
  ownerId: string;
  sfStage?: number;
  sfForecast?: string;
  sfCloseQuarter?: string;
  cpEstimate?: number;
}

function DriveImportTab({ onImportComplete: _onImportComplete }: { onImportComplete?: () => void }) {
  const [drivePath, setDrivePath] = useState('');
  const [pathValidated, setPathValidated] = useState(false);
  const [pathMessage, setPathMessage] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const [driveAccounts, setDriveAccounts] = useState<DriveAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);

  const [batchRows, setBatchRows] = useState<BatchRow[]>([]);
  const [batchId, setBatchId] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('sis_batch_id');
    }
    return null;
  });
  const [batchError, setBatchError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const MAX_BATCH_SIZE = 10;

  const { data: icUsers = [] } = useICUsers();

  // Load saved config on mount
  useEffect(() => {
    api.gdrive.config().then((cfg) => {
      if (cfg.path) {
        setDrivePath(cfg.path);
      }
    }).catch(() => { /* ignore if backend not ready */ });
  }, []);

  async function handleValidatePath() {
    if (!drivePath.trim()) return;
    setIsValidating(true);
    setPathValidated(false);
    setPathMessage('');
    setDriveAccounts([]);
    setBatchRows([]);

    try {
      const result = await api.gdrive.validate(drivePath.trim());
      setPathValidated(result.is_valid);
      setPathMessage(result.message);

      if (result.is_valid) {
        setIsLoadingAccounts(true);
        const accounts = await api.gdrive.listAccounts(drivePath.trim());
        setDriveAccounts(accounts);
        setBatchRows(accounts.map((a) => ({
          account: a,
          selected: false,
          maxCalls: Math.min(5, a.call_count),
          dealType: '',
          buyingCulture: 'direct',
          ownerId: '',
        })));
        setIsLoadingAccounts(false);
      }
    } catch (err) {
      setPathMessage(err instanceof Error ? err.message : 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  }

  async function handleRescan() {
    if (!drivePath.trim()) return;
    setIsLoadingAccounts(true);
    setBatchRows([]);
    try {
      const result = await api.gdrive.validate(drivePath.trim());
      setPathValidated(result.is_valid);
      setPathMessage(result.message);
      if (result.is_valid) {
        const accounts = await api.gdrive.listAccounts(drivePath.trim());
        setDriveAccounts(accounts);
        setBatchRows(accounts.map((a) => ({
          account: a,
          selected: false,
          maxCalls: Math.min(5, a.call_count),
          dealType: '',
          buyingCulture: 'direct',
          ownerId: '',
        })));
      }
    } catch (err) {
      setPathMessage(err instanceof Error ? err.message : 'Rescan failed');
    } finally {
      setIsLoadingAccounts(false);
    }
  }

  const selectedCount = batchRows.filter((r) => r.selected).length;

  function updateRow(index: number, updates: Partial<BatchRow>) {
    setBatchRows((prev) => prev.map((r, i) => i === index ? { ...r, ...updates } : r));
  }

  const canSubmit = selectedCount > 0 && batchRows.every((r) =>
    !r.selected || (r.dealType && r.ownerId)
  );

  async function handleBatchSubmit() {
    const selected = batchRows.filter((r) => r.selected);
    if (selected.length === 0) return;

    setIsSubmitting(true);
    setBatchError('');

    try {
      const items = selected.map((r) => ({
        account_name: toTitleCase(r.account.name),
        drive_path: r.account.path,
        max_calls: r.maxCalls,
        deal_type: r.dealType || undefined,
        buying_culture: r.buyingCulture || 'direct',
        owner_id: r.ownerId || undefined,
        sf_stage: r.sfStage,
        sf_forecast_category: r.sfForecast,
        sf_close_quarter: r.sfCloseQuarter,
        cp_estimate: r.cpEstimate,
      }));

      const result = await api.analyses.batch(items);
      sessionStorage.setItem('sis_batch_id', result.batch_id);
      setBatchId(result.batch_id);
    } catch (err) {
      setBatchError(err instanceof Error ? err.message : 'Batch submission failed');
    } finally {
      setIsSubmitting(false);
    }
  }

  // If batch submitted, show batch progress view
  if (batchId) {
    return <BatchProgressView batchId={batchId} onDismiss={() => setBatchId(null)} />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import from Google Drive</CardTitle>
        <CardDescription>
          Enter the local path to your Google Drive folder containing account
          sub-folders with Gong JSON exports.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Step 1: Drive path */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium" htmlFor="drive-path">
            Google Drive Folder Path
          </label>
          <div className="flex gap-2">
            <Input
              id="drive-path"
              placeholder="~/Library/CloudStorage/GoogleDrive-you@company.com/My Drive/Transcripts"
              value={drivePath}
              onChange={(e) => {
                setDrivePath(e.target.value);
                setPathValidated(false);
                setDriveAccounts([]);
                setBatchRows([]);
              }}
              className="flex-1"
            />
            <Button
              onClick={handleValidatePath}
              disabled={!drivePath.trim() || isValidating}
              variant="secondary"
            >
              {isValidating ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                'Scan'
              )}
            </Button>
          </div>
          {pathMessage && (
            <p className={`text-sm ${pathValidated ? 'text-emerald-600' : 'text-destructive'}`}>
              {pathValidated ? '✅' : '❌'} {pathMessage}
            </p>
          )}
        </div>

        {/* Step 2: Account selection table */}
        {(isLoadingAccounts || batchRows.length > 0) && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">
                Select accounts to import ({selectedCount} of {batchRows.length} selected)
              </label>
              <Button variant="ghost" size="sm" onClick={handleRescan} disabled={isLoadingAccounts} className="text-xs">
                Rescan
              </Button>
            </div>

            {isLoadingAccounts ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Scanning folders...
              </div>
            ) : (
              <>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-10"></TableHead>
                        <TableHead>Account</TableHead>
                        <TableHead className="w-32">Calls</TableHead>
                        <TableHead className="w-40">Deal Type</TableHead>
                        <TableHead className="whitespace-normal">Culture</TableHead>
                        <TableHead className="w-44">AE Owner</TableHead>
                        <TableHead className="text-xs w-16">SF Stg</TableHead>
                        <TableHead className="text-xs w-20">SF Fct</TableHead>
                        <TableHead className="text-xs w-20">Close Q</TableHead>
                        <TableHead className="text-xs w-20">CP $</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {batchRows.map((row, index) => (
                        <TableRow key={row.account.name} className={row.selected ? 'bg-muted/30' : ''}>
                          <TableCell className="whitespace-normal">
                            <input
                              type="checkbox"
                              checked={row.selected}
                              disabled={!row.selected && selectedCount >= MAX_BATCH_SIZE}
                              onChange={(e) => updateRow(index, { selected: e.target.checked })}
                              className="size-4 rounded border-border"
                            />
                          </TableCell>
                          <TableCell className="whitespace-normal font-medium">{toTitleCase(row.account.name)}</TableCell>
                          <TableCell className="whitespace-normal">
                            {row.selected ? (
                              <div className="flex items-center gap-1">
                                <Input
                                  type="number"
                                  min={1}
                                  max={row.account.call_count}
                                  value={row.maxCalls}
                                  onChange={(e) => {
                                    const v = parseInt(e.target.value, 10);
                                    if (!isNaN(v) && v >= 1 && v <= row.account.call_count) {
                                      updateRow(index, { maxCalls: v });
                                    }
                                  }}
                                  className="w-16 h-8 text-xs"
                                />
                                <span className="text-xs text-muted-foreground">of {row.account.call_count}</span>
                              </div>
                            ) : (
                              <span className="text-xs text-muted-foreground">{row.account.call_count} avail</span>
                            )}
                          </TableCell>
                          <TableCell className="whitespace-normal">
                            {row.selected && (
                              <Select value={row.dealType} onValueChange={(v) => updateRow(index, { dealType: v })}>
                                <SelectTrigger className="h-8 text-xs">
                                  <SelectValue placeholder="Select" />
                                </SelectTrigger>
                                <SelectContent>
                                  {DEAL_TYPES.map((t) => (
                                    <SelectItem key={t} value={t}>{t}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </TableCell>
                          <TableCell className="whitespace-normal">
                            {row.selected && (
                              <Select
                                value={row.buyingCulture || 'direct'}
                                onValueChange={(v) => updateRow(index, { buyingCulture: v })}
                              >
                                <SelectTrigger className="h-8 w-[140px] text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="direct">Direct</SelectItem>
                                  <SelectItem value="proxy_delegated">Proxy-Delegated</SelectItem>
                                </SelectContent>
                              </Select>
                            )}
                          </TableCell>
                          <TableCell className="whitespace-normal">
                            {row.selected && (
                              <Select value={row.ownerId} onValueChange={(v) => updateRow(index, { ownerId: v })}>
                                <SelectTrigger className="h-8 text-xs">
                                  <SelectValue placeholder="Select AE" />
                                </SelectTrigger>
                                <SelectContent>
                                  {icUsers.map((ic: ICUser) => (
                                    <SelectItem key={ic.id} value={ic.id}>
                                      {ic.name}{ic.team_name ? ` (${ic.team_name})` : ''}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </TableCell>
                          {/* SF Stage */}
                          <TableCell className="p-1 whitespace-normal">
                            {row.selected ? (
                              <Select value={row.sfStage?.toString() ?? ""} onValueChange={(v) => updateRow(index, { sfStage: v ? parseInt(v) : undefined })}>
                                <SelectTrigger className="h-7 text-xs w-28"><SelectValue placeholder="—" /></SelectTrigger>
                                <SelectContent>
                                  {[{v:"1",l:"1 – Qualify"},{v:"2",l:"2 – Establish Business Case"},{v:"3",l:"3 – Scope"},{v:"4",l:"4 – Proposal"},{v:"5",l:"5 – Negotiate"},{v:"6",l:"6 – Contract"},{v:"7",l:"7 – Implement"}].map(s => (
                                    <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            ) : null}
                          </TableCell>
                          {/* SF Forecast */}
                          <TableCell className="p-1 whitespace-normal">
                            {row.selected ? (
                              <Select value={row.sfForecast ?? ""} onValueChange={(v) => updateRow(index, { sfForecast: v || undefined })}>
                                <SelectTrigger className="h-7 text-xs w-20"><SelectValue placeholder="—" /></SelectTrigger>
                                <SelectContent>
                                  {["Commit","Realistic","Upside","At Risk"].map(f => (
                                    <SelectItem key={f} value={f}>{f}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            ) : null}
                          </TableCell>
                          {/* Close Quarter */}
                          <TableCell className="p-1 whitespace-normal">
                            {row.selected ? (
                              <Select value={row.sfCloseQuarter ?? ""} onValueChange={(v) => updateRow(index, { sfCloseQuarter: v || undefined })}>
                                <SelectTrigger className="h-7 text-xs w-20"><SelectValue placeholder="—" /></SelectTrigger>
                                <SelectContent>
                                  {generateCloseQuarters().map(q => (
                                    <SelectItem key={q} value={q}>{q}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            ) : null}
                          </TableCell>
                          {/* CP Estimate */}
                          <TableCell className="p-1 whitespace-normal">
                            {row.selected ? (
                              <Input
                                type="number"
                                className="h-7 text-xs w-20"
                                placeholder="$"
                                value={row.cpEstimate ?? ""}
                                onChange={(e) => updateRow(index, { cpEstimate: e.target.value ? parseFloat(e.target.value) : undefined })}
                              />
                            ) : null}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Submit button */}
                <Button
                  onClick={handleBatchSubmit}
                  disabled={!canSubmit || isSubmitting}
                  className="w-full"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="size-4 animate-spin mr-2" />
                      Submitting batch...
                    </>
                  ) : (
                    <>
                      <Play className="size-4 mr-2" />
                      Import &amp; Analyze {selectedCount} Account{selectedCount !== 1 ? 's' : ''}
                    </>
                  )}
                </Button>

                {batchError && (
                  <div className="rounded-md border border-destructive bg-destructive/5 p-3">
                    <p className="text-sm text-destructive">{batchError}</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Local Folder Import
// ---------------------------------------------------------------------------

function LocalFolderTab({ onImportComplete }: { onImportComplete?: () => void }) {
  const [folderPath, setFolderPath] = useState('');
  const [pathValidated, setPathValidated] = useState(false);
  const [pathMessage, setPathMessage] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const [driveAccounts, setDriveAccounts] = useState<DriveAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);

  const [selectedAccount, setSelectedAccount] = useState<DriveAccount | null>(null);
  const [recentCalls, setRecentCalls] = useState<DriveCall[]>([]);
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
  const [sfStage, setSfStage] = useState<number | undefined>();
  const [sfForecast, setSfForecast] = useState<string | undefined>();
  const [sfCloseQuarter, setSfCloseQuarter] = useState<string | undefined>();

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
      setRecentCalls(calls as unknown as DriveCall[]);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Failed to load calls');
    } finally {
      setIsLoadingCalls(false);
    }
  }

  async function handleRescan() {
    if (!folderPath.trim()) return;
    setIsLoadingAccounts(true);
    setSelectedAccount(null);
    setRecentCalls([]);
    setImportResult(null);
    try {
      const result = await api.gdrive.validate(folderPath.trim());
      setPathValidated(result.is_valid);
      setPathMessage(result.message);
      if (result.is_valid) {
        const accounts = await api.gdrive.listAccounts(folderPath.trim());
        setDriveAccounts(accounts);
      }
    } catch (err) {
      setPathMessage(err instanceof Error ? err.message : 'Rescan failed');
    } finally {
      setIsLoadingAccounts(false);
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
        sf_stage: sfStage,
        sf_forecast_category: sfForecast,
        sf_close_quarter: sfCloseQuarter,
      };
      const result = await api.gdrive.import(toTitleCase(selectedAccount.name), selectedAccount.path, maxCalls, dealArgs);
      setImportResult(result as unknown as ImportResult);
      onImportComplete?.();

      // Trigger analysis pipeline — returns real run_id immediately
      const analysisResult = await api.analyses.run(result.account_id);
      setAnalysisRunId(analysisResult.run_id);
      setAnalysisAccountId(result.account_id);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Import & Analysis failed');
    } finally {
      setIsImporting(false);
    }
  }

  // If analysis is running, show only the progress component
  if (analysisRunId && analysisAccountId) {
    return (
      <div className="space-y-4">
        {importResult && (
          <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-emerald-400 shrink-0" />
              <p className="text-sm font-medium text-emerald-300">
                Imported {importResult.imported_count} call{importResult.imported_count !== 1 ? 's' : ''} for {importResult.account_name}
                {importResult.skipped_count > 0 && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {' '}({importResult.skipped_count} skipped)
                  </span>
                )}
              </p>
            </div>
          </div>
        )}
        <AnalysisProgressDetail
          runId={analysisRunId}
          accountId={analysisAccountId}
        />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import from Local Folder</CardTitle>
        <CardDescription>
          Enter the path to any local folder containing account sub-folders with
          Gong JSON exports (metadata + transcript file pairs).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-1.5">
          <label className="text-sm font-medium" htmlFor="local-path">
            Folder Path
          </label>
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
            <Button
              onClick={handleScanFolder}
              disabled={!folderPath.trim() || isValidating}
              variant="secondary"
            >
              {isValidating ? <Loader2 className="size-4 animate-spin" /> : 'Scan'}
            </Button>
          </div>
          {pathMessage && (
            <p className={`text-sm ${pathValidated ? 'text-emerald-600' : 'text-destructive'}`}>
              {pathValidated ? '✅' : '❌'} {pathMessage}
            </p>
          )}
        </div>

        {(isLoadingAccounts || driveAccounts.length > 0) && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Select Account</label>
              {pathValidated && !isLoadingAccounts && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRescan}
                  disabled={isLoadingAccounts}
                  className="text-xs"
                >
                  Rescan
                </Button>
              )}
            </div>
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

        {/* Max calls input */}
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
                    <TableCell>{call.title}</TableCell>
                    <TableCell className="text-center">
                      {call.has_transcript ? (
                        <Badge variant="default" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">✓</Badge>
                      ) : (
                        <Badge variant="secondary">—</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Deal Configuration */}
            <div className="space-y-4 py-4 border-y border-border/50 my-4">
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

            {/* SF Indication */}
            <div className="space-y-3">
              <div>
                <h4 className="text-sm font-medium">SF Indication</h4>
                <p className="text-xs text-muted-foreground">Salesforce values at day of last analysis</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium">SF Stage</label>
                  <Select value={sfStage?.toString() ?? ""} onValueChange={(v) => setSfStage(v ? parseInt(v) : undefined)}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select stage" /></SelectTrigger>
                    <SelectContent>
                      {[
                        { value: "1", label: "1 – Qualify" },
                        { value: "2", label: "2 – Establish Business Case" },
                        { value: "3", label: "3 – Scope" },
                        { value: "4", label: "4 – Proposal" },
                        { value: "5", label: "5 – Negotiate" },
                        { value: "6", label: "6 – Contract" },
                        { value: "7", label: "7 – Implement" },
                      ].map((s) => (
                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">SF Forecast</label>
                  <Select value={sfForecast ?? ""} onValueChange={(v) => setSfForecast(v || undefined)}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select forecast" /></SelectTrigger>
                    <SelectContent>
                      {["Commit", "Realistic", "Upside", "At Risk"].map((f) => (
                        <SelectItem key={f} value={f}>{f}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium">Close Quarter</label>
                  <Select value={sfCloseQuarter ?? ""} onValueChange={(v) => setSfCloseQuarter(v || undefined)}>
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

        {importResult && (
          <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="size-5 text-emerald-400 mt-0.5 shrink-0" />
              <p className="font-medium text-emerald-300">
                Imported {importResult.imported_count} new call{importResult.imported_count !== 1 ? 's' : ''} for {importResult.account_name}
                {importResult.skipped_count > 0 && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {' '}({importResult.skipped_count} already imported)
                  </span>
                )}
              </p>
            </div>
            <div className="ml-7 space-y-1">
              {importResult.calls.map((c, i) => (
                <p key={i} className={`text-sm ${c.status === 'skipped' ? 'text-muted-foreground line-through' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {c.date}: {c.title}
                  {c.status === 'imported' && c.token_count != null && ` (${c.token_count.toLocaleString()} tokens)`}
                  {c.status === 'skipped' && ' (skipped)'}
                </p>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Manual Text Upload (preserved)
// ---------------------------------------------------------------------------

function ManualUploadTab() {
  const { data: accountsData, isLoading: accountsLoading } = useAccounts();
  const accounts = (accountsData ?? []) as Account[];
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
    <Card>
      <CardHeader>
        <CardTitle>Transcript Details</CardTitle>
        <CardDescription>
          Paste the full call transcript and fill in the metadata.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Account selector */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="account-select">
              Account
            </label>
            <Select
              value={accountId}
              onValueChange={(v) => {
                setAccountId(v);
                handleReset();
              }}
              disabled={accountsLoading}
            >
              <SelectTrigger id="account-select" className="w-full">
                <SelectValue
                  placeholder={
                    accountsLoading ? 'Loading accounts...' : 'Select an account'
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.account_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Call date */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="call-date">
              Call Date
            </label>
            <Input
              id="call-date"
              type="date"
              value={callDate}
              onChange={(e) => setCallDate(e.target.value)}
              required
            />
          </div>

          {/* Duration */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="duration">
              Duration (mins)
            </label>
            <Input
              id="duration"
              type="number"
              min={1}
              placeholder="Optional"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
            />
          </div>

          {/* Transcript text */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="transcript-text">
              Transcript Text
            </label>
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

          {/* Submit button */}
          <Button
            type="submit"
            disabled={!isValid || uploadMutation.isPending}
            className="w-full sm:w-auto"
          >
            {uploadMutation.isPending ? (
              <>
                <Upload className="size-4 animate-pulse" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="size-4" />
                Upload Transcript
              </>
            )}
          </Button>

          {/* Error message */}
          {uploadMutation.isError && (
            <div className="rounded-md border border-destructive bg-destructive/5 p-3">
              <p className="text-sm text-destructive">
                {uploadMutation.error instanceof Error
                  ? uploadMutation.error.message
                  : 'Upload failed. Please try again.'}
              </p>
            </div>
          )}

          {/* Success message */}
          {uploadResult && (
            <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-start gap-2">
              <CheckCircle2 className="size-4 text-emerald-400 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-emerald-300">
                  Transcript uploaded successfully!
                </p>
                {uploadResult.token_count != null && (
                  <p className="text-emerald-600 dark:text-emerald-400">
                    Token count: {uploadResult.token_count.toLocaleString()}
                  </p>
                )}
              </div>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Past Uploads Table
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
                  <TableCell className="text-sm">
                    {acct.stage_name ?? '--'}
                  </TableCell>
                  <TableCell className="text-sm">
                    {acct.ai_forecast_category ?? '--'}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {acct.last_assessed
                      ? new Date(acct.last_assessed).toLocaleDateString()
                      : 'Not analyzed'}
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
