import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface HealthBadgeProps {
  score: number | null;
  className?: string;
}

function getHealthTier(score: number | null) {
  if (score === null || score === undefined) {
    return { label: 'N/A', colorClass: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' };
  }
  if (score >= 70) {
    return { label: String(score), colorClass: 'bg-healthy-light text-healthy dark:bg-emerald-950 dark:text-emerald-400' };
  }
  if (score >= 40) {
    return { label: String(score), colorClass: 'bg-neutral-light text-neutral dark:bg-amber-950 dark:text-amber-400' };
  }
  return { label: String(score), colorClass: 'bg-needs-attention-light text-needs-attention dark:bg-red-950 dark:text-red-400' };
}

export function HealthBadge({ score, className }: HealthBadgeProps) {
  const { label, colorClass } = getHealthTier(score);

  return (
    <Badge
      variant="outline"
      className={cn(
        'border-transparent font-semibold tabular-nums',
        colorClass,
        className,
      )}
    >
      {label}
    </Badge>
  );
}
