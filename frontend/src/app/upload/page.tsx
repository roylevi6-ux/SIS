'use client';

import { useState, useEffect } from 'react';
import { Upload, CheckCircle2, FolderOpen, FileText, Loader2, HardDrive, Play } from 'lucide-react';
import { useAccounts, useUploadTranscript } from '@/lib/hooks';
import { api } from '@/lib/api';
import { AnalysisProgressDetail } from '@/components/analysis-progress-detail';
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
  return (
    <div className="p-6 max-w-3xl">
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
          <DriveImportTab />
        </TabsContent>

        <TabsContent value="local" className="mt-4">
          <LocalFolderTab />
        </TabsContent>

        <TabsContent value="manual" className="mt-4">
          <ManualUploadTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 1: Google Drive Import
// ---------------------------------------------------------------------------

function DriveImportTab() {
  const [drivePath, setDrivePath] = useState('');
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
  const [mrrEstimate, setMrrEstimate] = useState<string>('');
  const [aeOwner, setAeOwner] = useState<string>('');
  const [teamLead, setTeamLead] = useState<string>('');
  const [teamName, setTeamName] = useState<string>('');

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
    setSelectedAccount(null);
    setRecentCalls([]);
    setImportResult(null);

    try {
      const result = await api.gdrive.validate(drivePath.trim());
      setPathValidated(result.is_valid);
      setPathMessage(result.message);

      if (result.is_valid) {
        setIsLoadingAccounts(true);
        const accounts = await api.gdrive.listAccounts(drivePath.trim());
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
      setRecentCalls(calls);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Failed to load calls');
    } finally {
      setIsLoadingCalls(false);
    }
  }

  async function handleRescan() {
    if (!drivePath.trim()) return;
    setIsLoadingAccounts(true);
    setSelectedAccount(null);
    setRecentCalls([]);
    setImportResult(null);
    try {
      const result = await api.gdrive.validate(drivePath.trim());
      setPathValidated(result.is_valid);
      setPathMessage(result.message);
      if (result.is_valid) {
        const accounts = await api.gdrive.listAccounts(drivePath.trim());
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

    setIsImporting(true);
    setImportError('');
    setImportResult(null);
    setAnalysisRunId(null);
    setAnalysisAccountId(null);

    try {
      const dealArgs = {
        deal_type: dealType || undefined,
        mrr_estimate: mrrEstimate ? parseFloat(mrrEstimate) : undefined,
        ae_owner: aeOwner || undefined,
        team_lead: teamLead || undefined,
        team_name: teamName || undefined,
      };
      const result = await api.gdrive.import(selectedAccount.name, selectedAccount.path, maxCalls, dealArgs);
      setImportResult(result);

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
          <div className="rounded-md border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
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
                setSelectedAccount(null);
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

        {/* Step 2: Account selector */}
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
                      {a.name} ({a.call_count} calls)
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

        {/* Step 3: Recent calls table */}
        {isLoadingCalls && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading recent calls...
          </div>
        )}

        {recentCalls.length > 0 && selectedAccount && (
          <div className="space-y-3">
            <p className="text-sm font-medium">
              {recentCalls.length} most recent calls for{' '}
              <strong>{selectedAccount.name}</strong>:
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
                        <Badge variant="default" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                          ✓
                        </Badge>
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
                  <label className="text-xs font-medium">MRR Estimate ($)</label>
                  <Input type="number" min="0" step="1000" placeholder="Optional" value={mrrEstimate} onChange={e => setMrrEstimate(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">AE Owner</label>
                  <Input placeholder="Optional" value={aeOwner} onChange={e => setAeOwner(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Team Lead</label>
                  <Input placeholder="Optional" value={teamLead} onChange={e => setTeamLead(e.target.value)} />
                </div>
              </div>
            </div>

            <Button
              onClick={handleImport}
              disabled={isImporting}
              className="w-full"
            >
              {isImporting ? (
                <>
                  <Loader2 className="size-4 animate-spin mr-2" />
                  Importing & Analyzing...
                </>
              ) : (
                <>
                  <Play className="size-4 mr-2" />
                  Import & Run Analysis
                </>
              )}
            </Button>
          </div>
        )}

        {/* Import error */}
        {importError && (
          <div className="rounded-md border border-destructive bg-destructive/5 p-3">
            <p className="text-sm text-destructive">{importError}</p>
          </div>
        )}

        {/* Import success */}
        {importResult && (
          <div className="rounded-md border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-4 space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-emerald-700 dark:text-emerald-300">
                  Imported {importResult.imported_count} new call{importResult.imported_count !== 1 ? 's' : ''} for {importResult.account_name}
                  {importResult.skipped_count > 0 && (
                    <span className="text-amber-600 dark:text-amber-400">
                      {' '}({importResult.skipped_count} already imported)
                    </span>
                  )}
                </p>
              </div>
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
// Tab 2: Local Folder Import
// ---------------------------------------------------------------------------

function LocalFolderTab() {
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
  const [mrrEstimate, setMrrEstimate] = useState<string>('');
  const [aeOwner, setAeOwner] = useState<string>('');
  const [teamLead, setTeamLead] = useState<string>('');
  const [teamName, setTeamName] = useState<string>('');

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
      setRecentCalls(calls);
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
    setIsImporting(true);
    setImportError('');
    setImportResult(null);
    setAnalysisRunId(null);
    setAnalysisAccountId(null);

    try {
      const dealArgs = {
        deal_type: dealType || undefined,
        mrr_estimate: mrrEstimate ? parseFloat(mrrEstimate) : undefined,
        ae_owner: aeOwner || undefined,
        team_lead: teamLead || undefined,
        team_name: teamName || undefined,
      };
      const result = await api.gdrive.import(selectedAccount.name, selectedAccount.path, maxCalls, dealArgs);
      setImportResult(result);

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
          <div className="rounded-md border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
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
                      {a.name} ({a.call_count} calls)
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
              {recentCalls.length} most recent calls for <strong>{selectedAccount.name}</strong>:
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
                  <label className="text-xs font-medium">MRR Estimate ($)</label>
                  <Input type="number" min="0" step="1000" placeholder="Optional" value={mrrEstimate} onChange={e => setMrrEstimate(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">AE Owner</label>
                  <Input placeholder="Optional" value={aeOwner} onChange={e => setAeOwner(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium">Team Lead</label>
                  <Input placeholder="Optional" value={teamLead} onChange={e => setTeamLead(e.target.value)} />
                </div>
              </div>
            </div>

            <Button onClick={handleImport} disabled={isImporting} className="w-full">
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
          <div className="rounded-md border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-4 space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
              <p className="font-medium text-emerald-700 dark:text-emerald-300">
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
          setUploadResult(data as UploadResult);
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
            <div className="rounded-md border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-3 flex items-start gap-2">
              <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-emerald-700 dark:text-emerald-300">
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
