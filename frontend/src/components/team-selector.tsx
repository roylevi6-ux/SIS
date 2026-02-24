'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface TeamSelectorProps {
  teams: { id: string; name: string }[];
  selected: string | null; // null = "All Teams"
  onSelect: (teamId: string | null) => void;
}

export function TeamSelector({ teams, selected, onSelect }: TeamSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        variant={selected === null ? 'default' : 'outline'}
        size="sm"
        onClick={() => onSelect(null)}
        className="text-xs"
      >
        All Teams
      </Button>
      {teams.map((team) => (
        <Button
          key={team.id}
          variant={selected === team.id ? 'default' : 'outline'}
          size="sm"
          onClick={() => onSelect(team.id)}
          className="text-xs"
        >
          {team.name}
        </Button>
      ))}
    </div>
  );
}
