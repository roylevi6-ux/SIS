import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ForecastBadgeProps {
  category: string | null;
  className?: string;
}

const categoryColors: Record<string, string> = {
  'Commit': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400',
  'Realistic': 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400',
  'Upside': 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400',
  'At Risk': 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400',
};

export function ForecastBadge({ category, className }: ForecastBadgeProps) {
  if (!category) {
    return <span className="text-muted-foreground text-sm">--</span>;
  }

  const colorClass = categoryColors[category] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';

  return (
    <Badge
      variant="outline"
      className={cn('border-transparent font-medium', colorClass, className)}
    >
      {category}
    </Badge>
  );
}
