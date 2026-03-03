'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

interface DealMemoSection {
  section_id: string;
  title: string;
  content: string;
  health_signal: string;
  related_components: string[];
}

interface DealNarrativeProps {
  memo: string | null;
  sections: DealMemoSection[];
}

const SIGNAL_STYLES: Record<string, string> = {
  green: 'border-l-emerald-500',
  amber: 'border-l-amber-400',
  red: 'border-l-red-500',
};

function parseFallbackSections(memo: string): DealMemoSection[] {
  const paragraphs = memo.split(/\n\n+/).filter((p) => p.trim());
  const sectionIds = [
    'bottom_line', 'deal_situation', 'people_power', 'commercial_competitive',
    'why_now', 'momentum', 'technical', 'red_flags', 'expansion_dynamics',
  ];
  const titles = [
    'The Bottom Line', 'Deal Situation & Stage', 'People & Power',
    'Commercial & Competitive', 'Why Now?', 'Momentum & Advancement',
    'Technical & Integration', 'Red Flags & Silence Signals', 'Expansion Dynamics',
  ];
  return paragraphs.slice(0, sectionIds.length).map((content, i) => ({
    section_id: sectionIds[i] ?? `section_${i}`,
    title: titles[i] ?? `Section ${i + 1}`,
    content: content.trim(),
    health_signal: 'amber',
    related_components: [],
  }));
}

export function DealNarrative({ memo, sections }: DealNarrativeProps) {
  const [expandedAll, setExpandedAll] = useState(true);

  const displaySections = sections.length > 0
    ? sections
    : memo
      ? parseFallbackSections(memo)
      : [];

  if (displaySections.length === 0) return null;

  const bottomLine = displaySections.find((s) => s.section_id === 'bottom_line');
  const rest = displaySections.filter((s) => s.section_id !== 'bottom_line');

  return (
    <Card>
      <CardContent className="pt-4 pb-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Deal Narrative
          </h3>
          <button
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setExpandedAll(!expandedAll)}
          >
            {expandedAll ? 'Collapse all' : 'Expand all'}
          </button>
        </div>

        {bottomLine && (
          <div className="border-l-4 border-l-foreground/20 pl-4 py-1">
            <p className="text-sm font-medium leading-relaxed">{bottomLine.content}</p>
          </div>
        )}

        <div className="space-y-1">
          {rest.map((section) => (
            <NarrativeSection key={section.section_id} section={section} defaultOpen={expandedAll} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function NarrativeSection({ section, defaultOpen }: { section: DealMemoSection; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="w-full text-left">
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors border-l-3',
            SIGNAL_STYLES[section.health_signal] ?? 'border-l-muted',
          )}
        >
          <ChevronRight
            className={cn(
              'size-3.5 shrink-0 text-muted-foreground transition-transform duration-200',
              open && 'rotate-90',
            )}
          />
          <span className="text-sm font-medium">{section.title}</span>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className={cn('pl-9 pr-3 pb-3 border-l-3', SIGNAL_STYLES[section.health_signal] ?? 'border-l-muted')}>
          {section.content.split(/\n+/).filter(Boolean).map((para, i) => (
            <p key={i} className="text-sm leading-relaxed text-muted-foreground mt-1.5">
              {para}
            </p>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
