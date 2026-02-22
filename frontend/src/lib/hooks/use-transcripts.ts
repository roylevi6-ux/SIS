import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export function useTranscripts(accountId: string, activeOnly?: boolean) {
  return useQuery({
    queryKey: ['transcripts', accountId, activeOnly],
    queryFn: () => api.transcripts.list(accountId, activeOnly),
    enabled: !!accountId,
  });
}

export function useUploadTranscript() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.transcripts.upload,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transcripts'] }),
  });
}
