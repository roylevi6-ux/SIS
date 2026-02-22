'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Copy, Check } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BriefFormat = 'structured' | 'narrative' | 'inspection';

const FORMAT_OPTIONS: { value: BriefFormat; label: string }[] = [
  { value: 'structured', label: 'Structured' },
  { value: 'narrative', label: 'Narrative' },
  { value: 'inspection', label: 'Inspection' },
];

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function BriefSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-muted"
          style={{ width: `${60 + (i % 4) * 10}%` }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DealBriefPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [format, setFormat] = useState<BriefFormat>('structured');
  const [copied, setCopied] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['export', 'brief', id, format],
    queryFn: () => api.export.brief(id, format),
    enabled: !!id,
  });

  const briefContent = data?.content ?? '';

  async function handleCopy() {
    if (!briefContent) return;
    try {
      await navigator.clipboard.writeText(briefContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API unavailable
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Back link */}
      <Link
        href={`/deals/${id}`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to Deal
      </Link>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Deal Brief</h1>

        <Button
          variant="outline"
          size="sm"
          onClick={handleCopy}
          disabled={!briefContent || isLoading}
          className="self-start sm:self-auto"
        >
          {copied ? (
            <>
              <Check className="size-4" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-4" />
              Copy to Clipboard
            </>
          )}
        </Button>
      </div>

      {/* Format selector */}
      <div className="flex gap-2">
        {FORMAT_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFormat(opt.value)}
            className={[
              'min-h-[44px] px-4 py-2 rounded-md text-sm font-medium transition-colors',
              format === opt.value
                ? 'bg-primary text-primary-foreground'
                : 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
            ].join(' ')}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Error state */}
      {isError && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive font-medium">Failed to load deal brief</p>
            <p className="text-sm text-muted-foreground mt-1">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Brief content */}
      {!isError && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base capitalize">{format} Brief</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <BriefSkeleton />
            ) : !briefContent ? (
              <p className="text-sm text-muted-foreground">
                No brief content available. Run an analysis first.
              </p>
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground">
                {briefContent}
              </pre>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
