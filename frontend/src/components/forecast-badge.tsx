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
    <span
      className={cn(
        'inline-flex items-center rounded-[5px] px-2.5 py-0.5 text-[11.5px] font-semibold',
        colorClass,
        className,
      )}
    >
      {category}
    </span>
  );
}
