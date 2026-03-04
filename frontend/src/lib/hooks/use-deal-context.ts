import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import type { DealContextUpsert } from '../api-types';

export function useDealContext(accountId: string) {
  return useQuery({
    queryKey: ['deal_context', accountId],
    queryFn: () => api.dealContext.get(accountId),
    enabled: !!accountId,
  });
}

export function useDealContextQuestions() {
  return useQuery({
    queryKey: ['deal_context_questions'],
    queryFn: () => api.dealContext.questions(),
    staleTime: Infinity,
  });
}

export function useSubmitDealContext() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DealContextUpsert) => api.dealContext.upsert(data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['deal_context', variables.account_id] });
    },
  });
}
