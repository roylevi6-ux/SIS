import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function usePipeline(team?: string) {
  return useQuery({
    queryKey: ['dashboard', 'pipeline', team],
    queryFn: () => api.dashboard.pipeline(team),
  });
}

export function useDivergence(team?: string) {
  return useQuery({
    queryKey: ['dashboard', 'divergence', team],
    queryFn: () => api.dashboard.divergence(team),
  });
}

export function useTeamRollup(team?: string) {
  return useQuery({
    queryKey: ['dashboard', 'team-rollup', team],
    queryFn: () => api.dashboard.teamRollup(team),
  });
}

export function useInsights() {
  return useQuery({
    queryKey: ['dashboard', 'insights'],
    queryFn: () => api.dashboard.insights(),
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
