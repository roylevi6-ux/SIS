'use client';

import { useState } from 'react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Separator } from '@/components/ui/separator';
import { ChevronDown, ChevronRight } from 'lucide-react';

export function Section({
  id,
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: {
  id: string;
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section id={id} className="scroll-mt-6">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-3 py-2 group">
          <Icon className="size-5 text-primary shrink-0" />
          <h2 className="text-lg font-semibold tracking-tight text-left">{title}</h2>
          <div className="flex-1" />
          {open ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="pl-8 pb-6 space-y-4">{children}</div>
        </CollapsibleContent>
      </Collapsible>
      <Separator />
    </section>
  );
}
