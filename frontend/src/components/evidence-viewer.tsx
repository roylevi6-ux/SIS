interface EvidenceItem {
  quote?: string;
  source?: string;
  [key: string]: unknown;
}

interface EvidenceViewerProps {
  evidence: EvidenceItem[];
}

export function EvidenceViewer({ evidence }: EvidenceViewerProps) {
  if (!evidence || evidence.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No evidence available.</p>
    );
  }

  return (
    <div className="space-y-2">
      {evidence.map((item, i) => (
        <div
          key={i}
          className="rounded-md border bg-muted/30 px-3 py-2 text-sm"
        >
          {item.quote && (
            <p className="italic text-foreground/80">
              &ldquo;{item.quote}&rdquo;
            </p>
          )}
          {item.source && (
            <p className="mt-1 text-xs text-muted-foreground">
              Source: {item.source}
            </p>
          )}
          {/* Fallback: if no quote/source, render whatever we have */}
          {!item.quote && !item.source && (
            <p className="text-foreground/80">
              {JSON.stringify(item)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
