import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ForecastBadgeProps {
  category: string | null;
  className?: string;
}

const categoryColors: Record<string, string> = {
  'Commit': 'bg-forecast-commit-bg text-forecast-commit',
  'Realistic': 'bg-forecast-realistic-bg text-forecast-realistic',
  'Upside': 'bg-forecast-upside-bg text-forecast-upside',
  'At Risk': 'bg-forecast-risk-bg text-forecast-risk',
};

export function ForecastBadge({ category, className }: ForecastBadgeProps) {
  if (!category) {
    return <span className="text-muted-foreground text-sm">--</span>;
  }

  const colorClass = categoryColors[category] ?? 'bg-muted text-muted-foreground';

  return (
    <Badge
      variant="outline"
      className={cn('border-transparent font-medium', colorClass, className)}
    >
      {category}
    </Badge>
  );
}
