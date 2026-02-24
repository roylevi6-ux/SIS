import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export function useAnalysisHistory(accountId: string) {
  return useQuery({
    queryKey: ['analyses', 'history', accountId],
    queryFn: () => api.analyses.history(accountId),
    enabled: !!accountId,
  });
}

export function useAgentAnalyses(runId: string) {
  return useQuery({
    queryKey: ['analyses', 'agents', runId],
    queryFn: () => api.analyses.agents(runId),
    enabled: !!runId,
  });
}

export function useRunAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (accountId: string) => api.analyses.run(accountId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analyses'] }),
  });
}

export function useRerunAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, agentId }: { runId: string; agentId: string }) =>
      api.analyses.rerun(runId, agentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analyses'] }),
  });
}

export function useResynthesize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.analyses.resynthesize(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analyses'] }),
  });
}

export function useAssessmentDelta(accountId: string) {
  return useQuery({
    queryKey: ['analyses', 'delta', accountId],
    queryFn: () => api.analyses.delta(accountId),
    enabled: !!accountId,
  });
}

export function useAssessmentTimeline(accountId: string) {
  return useQuery({
    queryKey: ['analyses', 'timeline', accountId],
    queryFn: () => api.analyses.timeline(accountId),
    enabled: !!accountId,
  });
}

export function useCarryForwardActions(accountId: string) {
  return useQuery({
    queryKey: ['analyses', 'carry-forward', accountId],
    queryFn: () => api.analyses.carryForwardActions(accountId),
    enabled: !!accountId,
  });
}
