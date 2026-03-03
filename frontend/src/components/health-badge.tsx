import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface HealthBadgeProps {
  score: number | null;
  className?: string;
}

function getHealthTier(score: number | null) {
  if (score === null || score === undefined) {
    return { label: 'N/A', colorClass: 'bg-muted text-muted-foreground' };
  }
  if (score >= 70) {
    return { label: String(score), colorClass: 'bg-healthy-bg text-healthy' };
  }
  if (score >= 40) {
    return { label: String(score), colorClass: 'bg-neutral-bg text-neutral' };
  }
  return { label: String(score), colorClass: 'bg-needs-attention-bg text-needs-attention' };
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
