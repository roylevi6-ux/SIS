import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function usePipelineFlow(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'pipeline-flow', weeks],
    queryFn: () => api.dashboard.trendsPipelineFlow(weeks),
  });
}

export function useForecastMovement(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'forecast-movement', weeks],
    queryFn: () => api.dashboard.trendsForecastMovement(weeks),
  });
}

export function useDealHealth(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'deal-health', weeks],
    queryFn: () => api.dashboard.trendsDealHealth(weeks),
  });
}

export function useVelocity(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'velocity', weeks],
    queryFn: () => api.dashboard.trendsVelocity(weeks),
  });
}

export function useTeamComparison(weeks: number) {
  return useQuery({
    queryKey: ['trends', 'team-comparison', weeks],
    queryFn: () => api.dashboard.trendsTeamComparison(weeks),
  });
}
