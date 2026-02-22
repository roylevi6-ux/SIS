import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface DivergenceBadgeProps {
  divergence: boolean;
  explanation?: string | null;
  className?: string;
}

export function DivergenceBadge({ divergence, explanation, className }: DivergenceBadgeProps) {
  if (!divergence) {
    return (
      <span className={cn('inline-flex items-center gap-1 text-sm text-healthy', className)}>
        <CheckCircle2 className="size-4" />
        <span className="sr-only">Aligned</span>
      </span>
    );
  }

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              'inline-flex items-center gap-1 text-sm font-medium text-at-risk cursor-default',
              className,
            )}
          >
            <AlertTriangle className="size-4 shrink-0" />
            <span>Divergent</span>
          </span>
        </TooltipTrigger>
        {explanation && (
          <TooltipContent className="max-w-xs text-balance">
            {explanation}
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}
