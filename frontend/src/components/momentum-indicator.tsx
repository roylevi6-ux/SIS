import { ArrowUpRight, ArrowRight, ArrowDownRight } from 'lucide-react';
import { cn } from '@/lib/utils';

type MomentumDirection = 'Improving' | 'Stable' | 'Declining' | null;

interface MomentumIndicatorProps {
  direction: MomentumDirection;
  className?: string;
}

const config: Record<string, { Icon: typeof ArrowRight; label: string; colorClass: string }> = {
  Improving: {
    Icon: ArrowUpRight,
    label: 'Improving',
    colorClass: 'text-improving',
  },
  Stable: {
    Icon: ArrowRight,
    label: 'Stable',
    colorClass: 'text-stable',
  },
  Declining: {
    Icon: ArrowDownRight,
    label: 'Declining',
    colorClass: 'text-declining',
  },
};

export function MomentumIndicator({ direction, className }: MomentumIndicatorProps) {
  if (!direction || !config[direction]) {
    return <span className="text-muted-foreground text-sm">--</span>;
  }

  const { Icon, label, colorClass } = config[direction];

  return (
    <span className={cn('inline-flex items-center gap-1 text-sm font-medium', colorClass, className)}>
      <Icon className="size-4" />
      <span>{label}</span>
    </span>
  );
}
