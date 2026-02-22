'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DealMemoProps {
  memo: string | null | undefined;
}

function truncateToSummary(text: string): string {
  // First 3 sentences or first 500 chars, whichever is shorter
  const sentences = text.match(/[^.!?]+[.!?]+/g);
  if (sentences && sentences.length >= 3) {
    const first3 = sentences.slice(0, 3).join('').trim();
    if (first3.length <= 500) return first3;
  }
  if (text.length <= 500) return text;
  // Truncate at word boundary near 500 chars
  const truncated = text.slice(0, 500);
  const lastSpace = truncated.lastIndexOf(' ');
  return (lastSpace > 400 ? truncated.slice(0, lastSpace) : truncated) + '...';
}

function MemoText({ text }: { text: string }) {
  // Split on newlines and render as paragraphs
  const lines = text.split(/\n+/).filter((line) => line.trim().length > 0);

  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {lines.map((line, i) => (
        <p key={i}>{line}</p>
      ))}
    </div>
  );
}

export function DealMemo({ memo }: DealMemoProps) {
  if (!memo) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Deal Memo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No deal memo available. Run an analysis to generate one.
          </p>
        </CardContent>
      </Card>
    );
  }

  const summary = truncateToSummary(memo);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Deal Memo</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="brief">
          <TabsList>
            <TabsTrigger value="brief">TL Insider Brief</TabsTrigger>
            <TabsTrigger value="summary">Leadership Summary</TabsTrigger>
          </TabsList>
          <TabsContent value="brief" className="mt-3">
            <MemoText text={memo} />
          </TabsContent>
          <TabsContent value="summary" className="mt-3">
            <MemoText text={summary} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
