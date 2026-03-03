import { cn } from '@/lib/utils';

interface HealthBadgeProps {
  score: number | null;
  className?: string;
}

function getHealthTier(score: number | null) {
  if (score === null || score === undefined) {
    return { dotColor: 'bg-muted-foreground', textColor: 'text-muted-foreground', bgColor: 'bg-muted' };
  }
  if (score >= 70) {
    return { dotColor: 'bg-healthy', textColor: 'text-healthy', bgColor: 'bg-healthy-bg' };
  }
  if (score >= 40) {
    return { dotColor: 'bg-neutral', textColor: 'text-neutral', bgColor: 'bg-neutral-bg' };
  }
  return { dotColor: 'bg-needs-attention', textColor: 'text-needs-attention', bgColor: 'bg-needs-attention-bg' };
}

export function HealthBadge({ score, className }: HealthBadgeProps) {
  const { dotColor, textColor, bgColor } = getHealthTier(score);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold font-mono tabular-nums',
        bgColor,
        textColor,
        className,
      )}
    >
      <span className={cn('inline-block size-2 rounded-full', dotColor)} />
      {score !== null ? score : 'N/A'}
    </span>
  );
}
