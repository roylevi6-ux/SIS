import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export function useFeedback(params?: { account_id?: string; author?: string; status?: string }) {
  return useQuery({
    queryKey: ['feedback', params],
    queryFn: () => api.feedback.list(params),
  });
}

export function useFeedbackSummary() {
  return useQuery({
    queryKey: ['feedback', 'summary'],
    queryFn: () => api.feedback.summary(),
  });
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.feedback.submit,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['feedback'] }),
  });
}

export function useResolveFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.feedback.resolve(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['feedback'] }),
  });
}
