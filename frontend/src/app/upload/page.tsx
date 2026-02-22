'use client';

import { useState } from 'react';
import { Upload, CheckCircle2 } from 'lucide-react';
import { useAccounts, useUploadTranscript } from '@/lib/hooks';
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function UploadPage() {
  const { data: accountsData, isLoading: accountsLoading } = useAccounts();
  const accounts = (accountsData ?? []) as Account[];
  const uploadMutation = useUploadTranscript();

  // Form state
  const [accountId, setAccountId] = useState('');
  const [callDate, setCallDate] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('');
  const [rawText, setRawText] = useState('');

  // Result state
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  // Validation
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
          // Reset form fields on success (keep account selected)
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
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight mb-1">
        Upload Transcript
      </h1>
      <p className="text-sm text-muted-foreground mb-6">
        Upload a call transcript for analysis.
      </p>

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
    </div>
  );
}
