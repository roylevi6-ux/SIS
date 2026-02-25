import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

// Tracking
export function useUsageSummary(days?: number) {
  return useQuery({
    queryKey: ['tracking', 'summary', days],
    queryFn: () => api.tracking.summary(days),
  });
}

export function useCROMetrics() {
  return useQuery({
    queryKey: ['tracking', 'cro-metrics'],
    queryFn: () => api.tracking.croMetrics(),
  });
}

// Coaching
export function useCoaching(params?: any) {
  return useQuery({
    queryKey: ['coaching', params],
    queryFn: () => api.coaching.list(params),
  });
}

export function useCoachingSummary(repName?: string) {
  return useQuery({
    queryKey: ['coaching', 'summary', repName],
    queryFn: () => api.coaching.summary(repName),
  });
}

export function useSubmitCoaching() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.coaching.submit,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['coaching'] }),
  });
}

// Prompt versions
export function usePromptVersions(agentId?: string) {
  return useQuery({
    queryKey: ['prompts', 'versions', agentId],
    queryFn: () => api.prompts.list(agentId),
  });
}

export function useCreatePromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.prompts.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  });
}

// IC Users (non-admin)
export function useICUsers() {
  return useQuery({
    queryKey: ['users', 'ics'],
    queryFn: () => api.users.listICs(),
  });
}

// Scorecard
export function useRepScorecard(aeOwner?: string) {
  return useQuery({
    queryKey: ['scorecard', 'reps', aeOwner],
    queryFn: () => api.scorecard.reps(aeOwner),
  });
}

// Forecast
export function useForecastData(team?: string) {
  return useQuery({
    queryKey: ['forecast', 'data', team],
    queryFn: () => api.forecast.data(team),
  });
}

export function useForecastTeams() {
  return useQuery({
    queryKey: ['forecast', 'teams'],
    queryFn: () => api.forecast.teams(),
  });
}

// Action logs
export function useActionLogs(params?: any) {
  return useQuery({
    queryKey: ['logs', 'actions', params],
    queryFn: () => api.logs.actions(params),
  });
}

export function useActionSummary(days?: number) {
  return useQuery({
    queryKey: ['logs', 'summary', days],
    queryFn: () => api.logs.summary(days),
  });
}

// Calibration
export function useCalibrationCurrent() {
  return useQuery({
    queryKey: ['calibration', 'current'],
    queryFn: () => api.calibration.current(),
  });
}

export function useCalibrationHistory() {
  return useQuery({
    queryKey: ['calibration', 'history'],
    queryFn: () => api.calibration.history(),
  });
}

export function useCalibrationPatterns() {
  return useQuery({
    queryKey: ['calibration', 'patterns'],
    queryFn: () => api.calibration.patterns(),
  });
}

export function useCreateCalibration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.calibration.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['calibration'] }),
  });
}
