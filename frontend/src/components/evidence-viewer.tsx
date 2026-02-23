interface EvidenceItem {
  claim_id?: string;
  transcript_index?: number;
  speaker?: string;
  quote?: string;
  interpretation?: string;
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
          className="rounded-md border bg-muted/30 px-3 py-2 text-sm space-y-1"
        >
          {item.quote && (
            <p className="italic text-foreground/80">
              &ldquo;{item.quote}&rdquo;
            </p>
          )}
          {item.interpretation && (
            <p className="text-foreground/90">{item.interpretation}</p>
          )}
          {(item.speaker || item.transcript_index != null) && (
            <p className="text-xs text-muted-foreground">
              {item.speaker && <span>{item.speaker}</span>}
              {item.speaker && item.transcript_index != null && ' · '}
              {item.transcript_index != null && (
                <span>Call {item.transcript_index}</span>
              )}
            </p>
          )}
          {item.source && (
            <p className="text-xs text-muted-foreground">
              Source: {item.source}
            </p>
          )}
          {/* Fallback for items with no recognized fields */}
          {!item.quote && !item.interpretation && !item.speaker && !item.source && (
            <p className="text-foreground/80">
              {typeof item === 'string' ? item : JSON.stringify(item)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
