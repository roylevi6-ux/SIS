import { getStoredToken } from './auth';
import type {
  Account,
  AccountCreate,
  AgentAnalysisResponse,
  AnalysisHistoryItem,
  AnalysisRunResponse,
  CalibrationSnapshot,
  CarryForwardAction,
  ChatMessage,
  ChatResponse,
  CoachingNote,
  CoachingSummary,
  CROMetric,
  DealTrend,
  DeltaResponse,
  DivergenceItem,
  ExportResponse,
  FeedbackItem,
  FeedbackSubmit,
  FeedbackSummary,
  ForecastData,
  GDriveAccount,
  GDriveCall,
  GDriveConfig,
  GDriveImportResult,
  GDriveValidation,
  InsightsResponse,
  ActionLog,
  ActionLogSummary,
  PipelineOverview,
  PortfolioSummary,
  PromptVersion,
  RepScorecard,
  TeamRollup,
  TeamTrend,
  TimelineEntry,
  Transcript,
  TranscriptUpload,
  UsageSummary,
} from './api-types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  // Automatically include JWT if a token is stored
  const token = getStoredToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// Auth + Account endpoints
export const api = {
  auth: {
    login: (username: string, role: string) =>
      apiFetch<{ token: string; username: string; role: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, role }),
      }),
    me: () => apiFetch<{ username: string; role: string }>('/api/auth/me'),
  },
  accounts: {
    list: (params?: { sort_by?: string; team?: string }) =>
      apiFetch<Account[]>(`/api/accounts/?${new URLSearchParams(params as Record<string, string>)}`),
    get: (id: string) => apiFetch<Account>(`/api/accounts/${id}`),
    create: (data: AccountCreate) =>
      apiFetch<Account>('/api/accounts/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: Partial<AccountCreate>) =>
      apiFetch<Account>(`/api/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/api/accounts/${id}`, { method: 'DELETE' }),
    setForecast: (id: string, category: string) =>
      apiFetch<Account>(`/api/accounts/${id}/ic-forecast`, {
        method: 'POST',
        body: JSON.stringify({ category }),
      }),
  },
  transcripts: {
    list: (accountId: string, activeOnly?: boolean) =>
      apiFetch<Transcript[]>(`/api/transcripts/${accountId}?active_only=${activeOnly ?? true}`),
    upload: (data: TranscriptUpload) =>
      apiFetch<Transcript>('/api/transcripts/', { method: 'POST', body: JSON.stringify(data) }),
  },
  analyses: {
    run: (accountId: string) =>
      apiFetch<AnalysisRunResponse>('/api/analyses/', {
        method: 'POST',
        body: JSON.stringify({ account_id: accountId }),
      }),
    history: (accountId: string) => apiFetch<AnalysisHistoryItem[]>(`/api/analyses/history/${accountId}`),
    agents: (runId: string) => apiFetch<AgentAnalysisResponse[]>(`/api/analyses/${runId}/agents`),
    rerun: (runId: string, agentId: string) =>
      apiFetch<AnalysisRunResponse>(`/api/analyses/${runId}/rerun/${agentId}`, { method: 'POST' }),
    resynthesize: (runId: string) =>
      apiFetch<AnalysisRunResponse>(`/api/analyses/${runId}/resynthesize`, { method: 'POST' }),
    cancel: (runId: string) =>
      apiFetch<{ ok: boolean }>(`/api/analyses/${runId}/cancel`, { method: 'POST' }),
    delta: (accountId: string) =>
      apiFetch<DeltaResponse>(`/api/analyses/delta/${accountId}`),
    timeline: (accountId: string) =>
      apiFetch<TimelineEntry[]>(`/api/analyses/timeline/${accountId}`),
    carryForwardActions: (accountId: string) =>
      apiFetch<CarryForwardAction[]>(`/api/analyses/carry-forward/${accountId}`),
  },
  dashboard: {
    pipeline: (team?: string) =>
      apiFetch<PipelineOverview>(`/api/dashboard/pipeline${team ? `?team=${team}` : ''}`),
    divergence: (team?: string) =>
      apiFetch<DivergenceItem[]>(`/api/dashboard/divergence${team ? `?team=${team}` : ''}`),
    teamRollup: (team?: string) =>
      apiFetch<TeamRollup[]>(`/api/dashboard/team-rollup${team ? `?team=${team}` : ''}`),
    insights: () => apiFetch<InsightsResponse>('/api/dashboard/insights'),
    dealTrends: (params?: { account_id?: string; weeks?: number }) =>
      apiFetch<DealTrend[]>(`/api/dashboard/trends/deals?${new URLSearchParams(params as Record<string, string>)}`),
    teamTrends: (weeks?: number) =>
      apiFetch<TeamTrend[]>(`/api/dashboard/trends/teams?weeks=${weeks ?? 4}`),
    portfolioSummary: (weeks?: number) =>
      apiFetch<PortfolioSummary>(`/api/dashboard/trends/portfolio?weeks=${weeks ?? 4}`),
  },
  feedback: {
    submit: (data: FeedbackSubmit) =>
      apiFetch<FeedbackItem>('/api/feedback/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params?: { account_id?: string; author?: string; status?: string }) =>
      apiFetch<FeedbackItem[]>(`/api/feedback/?${new URLSearchParams(params as Record<string, string>)}`),
    resolve: (id: string, data: { resolution_note: string }) =>
      apiFetch<FeedbackItem>(`/api/feedback/${id}/resolve`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    summary: () => apiFetch<FeedbackSummary>('/api/feedback/summary'),
  },
  chat: {
    query: (message: string, history?: ChatMessage[]) =>
      apiFetch<ChatResponse>('/api/chat/query', {
        method: 'POST',
        body: JSON.stringify({ message, history }),
      }),
  },
  calibration: {
    current: () => apiFetch<CalibrationSnapshot>('/api/calibration/current'),
    patterns: () => apiFetch<Record<string, unknown>>('/api/calibration/patterns'),
    create: (data: Record<string, unknown>) =>
      apiFetch<CalibrationSnapshot>('/api/calibration/', { method: 'POST', body: JSON.stringify(data) }),
    history: () => apiFetch<CalibrationSnapshot[]>('/api/calibration/history'),
  },
  tracking: {
    summary: (days?: number) => apiFetch<UsageSummary>(`/api/tracking/summary?days=${days ?? 30}`),
    croMetrics: () => apiFetch<CROMetric[]>('/api/tracking/cro-metrics'),
  },
  coaching: {
    submit: (data: { rep_name: string; note_text: string; author?: string }) =>
      apiFetch<CoachingNote>('/api/coaching/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params?: Record<string, string>) =>
      apiFetch<CoachingNote[]>(`/api/coaching/?${new URLSearchParams(params)}`),
    summary: (repName?: string) =>
      apiFetch<CoachingSummary>(`/api/coaching/summary${repName ? `?rep_name=${repName}` : ''}`),
  },
  prompts: {
    list: (agentId?: string) =>
      apiFetch<PromptVersion[]>(`/api/prompts/versions${agentId ? `?agent_id=${agentId}` : ''}`),
    create: (data: { agent_id: string; system_prompt: string }) =>
      apiFetch<PromptVersion>('/api/prompts/versions', { method: 'POST', body: JSON.stringify(data) }),
  },
  scorecard: {
    reps: (aeOwner?: string) =>
      apiFetch<RepScorecard[]>(`/api/scorecard/reps${aeOwner ? `?ae_owner=${aeOwner}` : ''}`),
  },
  forecast: {
    data: (team?: string) =>
      apiFetch<ForecastData[]>(`/api/forecast/data${team ? `?team=${team}` : ''}`),
    teams: () => apiFetch<string[]>('/api/forecast/teams'),
  },
  export: {
    brief: (accountId: string, format?: string) =>
      apiFetch<ExportResponse>(
        `/api/export/brief/${accountId}${format ? `?format=${format}` : ''}`,
      ),
    forecast: (params?: { team?: string; format?: string }) =>
      apiFetch<ExportResponse>(`/api/export/forecast?${new URLSearchParams(params as Record<string, string>)}`),
  },
  logs: {
    actions: (params?: Record<string, string>) =>
      apiFetch<ActionLog[]>(`/api/logs/actions?${new URLSearchParams(params)}`),
    summary: (days?: number) =>
      apiFetch<ActionLogSummary>(`/api/logs/actions/summary?days=${days ?? 30}`),
  },
  gdrive: {
    config: () => apiFetch<GDriveConfig>('/api/gdrive/config'),
    validate: (path: string) =>
      apiFetch<GDriveValidation>('/api/gdrive/validate', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    listAccounts: (path: string) =>
      apiFetch<GDriveAccount[]>('/api/gdrive/accounts', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    listCalls: (accountName: string, accountPath: string, maxCalls?: number) =>
      apiFetch<GDriveCall[]>('/api/gdrive/calls', {
        method: 'POST',
        body: JSON.stringify({ account_name: accountName, account_path: accountPath, max_calls: maxCalls ?? 5 }),
      }),
    import: (accountName: string, accountPath: string, maxCalls?: number, dealArgs?: Record<string, unknown>) =>
      apiFetch<GDriveImportResult>('/api/gdrive/import', {
        method: 'POST',
        body: JSON.stringify({ account_name: accountName, account_path: accountPath, max_calls: maxCalls ?? 5, ...dealArgs }),
      }),
  },
};

// Re-export types for consumers
export type * from './api-types';
