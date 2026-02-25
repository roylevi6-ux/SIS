import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import type { CommandCenterResponse } from '../pipeline-types';

interface CommandCenterParams {
  team?: string;
  ae?: string;
  period?: string;
  quarter?: string;
}

export function useCommandCenter(params?: CommandCenterParams) {
  return useQuery<CommandCenterResponse>({
    queryKey: ['dashboard', 'command-center', params],
    queryFn: () => api.dashboard.commandCenter(params),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
