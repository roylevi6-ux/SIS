import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function useDivergence(team?: string) {
  return useQuery({
    queryKey: ['dashboard', 'divergence', team],
    queryFn: () => api.dashboard.divergence(team),
  });
}

export function useTeamRollupHierarchy(team?: string) {
  return useQuery({
    queryKey: ['dashboard', 'team-rollup-hierarchy', team],
    queryFn: () => api.dashboard.teamRollupHierarchy(team),
  });
}

export function useDealTrends(params?: { account_id?: string; weeks?: number }) {
  return useQuery({
    queryKey: ['dashboard', 'trends', 'deals', params],
    queryFn: () => api.dashboard.dealTrends(params),
  });
}

export function useTeamTrends(weeks?: number) {
  return useQuery({
    queryKey: ['dashboard', 'trends', 'teams', weeks],
    queryFn: () => api.dashboard.teamTrends(weeks),
  });
}

export function usePortfolioSummary(weeks?: number) {
  return useQuery({
    queryKey: ['dashboard', 'trends', 'portfolio', weeks],
    queryFn: () => api.dashboard.portfolioSummary(weeks),
  });
}
