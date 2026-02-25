'use client';

import { useState } from 'react';
import { usePromptVersions } from '@/lib/hooks/use-admin';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
// Note: Collapsible removed – Radix renders a <div> wrapper that is invalid
// inside <tbody>. We use plain state + conditional rendering instead.
import { ChevronDown, ChevronRight } from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const AGENT_IDS = [
  'agent_0e', 'agent_1', 'agent_2', 'agent_3', 'agent_4', 'agent_5',
  'agent_6', 'agent_7', 'agent_8', 'agent_9', 'agent_10',
  'chat',
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Expandable prompt row
// ---------------------------------------------------------------------------

function PromptRow({ version }: { version: any }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TableRow className="cursor-pointer hover:bg-muted/50" onClick={() => setOpen(!open)}>
        <TableCell className="w-8">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </TableCell>
        <TableCell className="font-mono text-sm">{version.version}</TableCell>
        <TableCell>
          {version.is_active ? (
            <Badge>Active</Badge>
          ) : (
            <Badge variant="outline">Inactive</Badge>
          )}
        </TableCell>
        <TableCell className="max-w-xs text-sm text-muted-foreground">
          {version.change_notes ?? '--'}
        </TableCell>
        <TableCell className="text-sm text-muted-foreground">{formatDate(version.created_at)}</TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={5} className="bg-muted/30 p-0">
            <div className="px-6 py-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Prompt Template
              </p>
              <pre className="overflow-x-auto rounded-md border bg-background p-4 text-xs font-mono whitespace-pre-wrap leading-relaxed max-h-80">
                {version.prompt_template}
              </pre>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PromptsPage() {
  const [agentId, setAgentId] = useState<string | undefined>(undefined);
  const { data: versions, isLoading, isError, error } = usePromptVersions(agentId);

  const items: any[] = versions ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Prompt Versions</h1>
          <p className="text-sm text-muted-foreground">View prompt templates by agent</p>
        </div>
        <Select
          value={agentId ?? 'all'}
          onValueChange={(v) => setAgentId(v === 'all' ? undefined : v)}
        >
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="All Agents" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Agents</SelectItem>
            {AGENT_IDS.map((id) => (
              <SelectItem key={id} value={id}>
                {id.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load prompt versions</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {!isError && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8" />
                    <TableHead>Version</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Change Notes</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading && (
                    Array.from({ length: 4 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 5 }).map((_, j) => (
                          <TableCell key={j}>
                            <div className="h-4 w-24 animate-pulse rounded bg-muted" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                  {!isLoading && items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <div className="flex items-center justify-center py-10 text-muted-foreground">
                          No prompt versions found
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  {!isLoading && items.map((v: any, i: number) => (
                    <PromptRow key={v.id ?? i} version={v} />
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
