'use client';

import { useState } from 'react';
import { useFeedback, useFeedbackSummary, useResolveFeedback } from '@/lib/hooks/use-feedback';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'accepted') return 'default';
  if (status === 'rejected') return 'destructive';
  return 'outline';
}

function directionLabel(dir: string): string {
  if (dir === 'too_high') return 'Too High';
  if (dir === 'too_low') return 'Too Low';
  return dir;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ---------------------------------------------------------------------------
// Resolve dialog
// ---------------------------------------------------------------------------

interface ResolveDialogProps {
  feedbackId: string;
  open: boolean;
  onClose: () => void;
}

function ResolveDialog({ feedbackId, open, onClose }: ResolveDialogProps) {
  const [resolution, setResolution] = useState('accepted');
  const [notes, setNotes] = useState('');
  const [resolvedBy, setResolvedBy] = useState('');
  const { mutate, isPending } = useResolveFeedback();

  const handleSubmit = () => {
    mutate(
      { id: feedbackId, data: { resolution, notes, resolved_by: resolvedBy } },
      { onSuccess: onClose },
    );
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Resolve Feedback</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <label className="text-sm font-medium">Resolution</label>
            <Select value={resolution} onValueChange={setResolution}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="accepted">Accepted</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Resolved by</label>
            <Input
              placeholder="Your name"
              value={resolvedBy}
              onChange={(e) => setResolvedBy(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Notes</label>
            <Textarea
              placeholder="Explain the resolution..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isPending || !resolvedBy}>
            {isPending ? 'Saving...' : 'Resolve'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------

function SummaryCards({ summary }: { summary: any }) {
  const cards = [
    { label: 'Total', value: summary?.total ?? '--' },
    { label: 'Pending', value: summary?.by_status?.pending ?? 0 },
    { label: 'Too High', value: summary?.by_direction?.too_high ?? 0 },
    { label: 'Too Low', value: summary?.by_direction?.too_low ?? 0 },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardHeader className="pb-1 pt-4 px-4">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {c.label}
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-4 px-4">
            <span className="text-2xl font-bold tabular-nums">{c.value}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function FeedbackPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [authorFilter, setAuthorFilter] = useState('');
  const [resolveId, setResolveId] = useState<string | null>(null);

  const { data: summary, isLoading: summaryLoading } = useFeedbackSummary();
  const { data: rawItems, isLoading, isError, error } = useFeedback({
    status: statusFilter,
    author: authorFilter || undefined,
  });

  const items: any[] = rawItems ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Feedback</h1>
          <p className="text-sm text-muted-foreground">Score feedback submitted by the IC team</p>
        </div>
      </div>

      {/* Summary */}
      {!summaryLoading && summary && <SummaryCards summary={summary} />}

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Select
          value={statusFilter ?? 'all'}
          onValueChange={(v) => setStatusFilter(v === 'all' ? undefined : v)}
        >
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="accepted">Accepted</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
        <Input
          placeholder="Filter by author..."
          value={authorFilter}
          onChange={(e) => setAuthorFilter(e.target.value)}
          className="sm:w-[200px]"
        />
      </div>

      {/* Error */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load feedback</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      {!isError && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Account</TableHead>
                    <TableHead>Author</TableHead>
                    <TableHead>Direction</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead className="text-right">Score</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading && (
                    Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 8 }).map((_, j) => (
                          <TableCell key={j}>
                            <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                  {!isLoading && items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8}>
                        <div className="flex items-center justify-center py-10 text-muted-foreground">
                          No feedback found
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  {!isLoading && items.map((item: any) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.account_name ?? item.account_id}</TableCell>
                      <TableCell>{item.author}</TableCell>
                      <TableCell>
                        <Badge variant={item.direction === 'too_high' ? 'destructive' : 'secondary'}>
                          {directionLabel(item.direction)}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[160px] truncate text-sm">{item.reason}</TableCell>
                      <TableCell className="text-right tabular-nums">{item.health_score ?? '--'}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(item.created_at)}
                      </TableCell>
                      <TableCell>
                        {item.status === 'pending' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8"
                            onClick={() => setResolveId(item.id)}
                          >
                            Resolve
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {resolveId && (
        <ResolveDialog
          feedbackId={resolveId}
          open={!!resolveId}
          onClose={() => setResolveId(null)}
        />
      )}
    </div>
  );
}
