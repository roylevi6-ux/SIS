import { getStoredToken, triggerLogout } from './auth';
import type {
  Account,
  AccountCreate,
  AgentAnalysisResponse,
  AnalysisHistoryItem,
  AnalysisRunResponse,
  BatchAnalysisResponse,
  BatchItemRequest,
  CalibrationSnapshot,
  CarryForwardAction,
  ChatMessage,
  ChatResponse,
  CoachingNote,
  CoachingSummary,
  CROMetric,
  DealContextEntryInput,
  DealContextQuestion,
  DealContextResponse,
  DealContextUpsert,
  DealHealthResponse,
  DealTrend,
  DeltaResponse,
  DivergenceItem,
  ExportResponse,
  ForecastData,
  ForecastMovementResponse,
  HierarchyTeam,
  EnrichedCall,
  EnrichedDriveAccount,
  GDriveAccount,
  GDriveCall,
  GDriveConfig,
  GDriveImportResult,
  GDriveValidation,
  InsightsResponse,
  ActionLog,
  ActionLogSummary,
  PipelineFlowResponse,
  PipelineOverview,
  PortfolioSummary,
  PromptVersion,
  ICUser,
  RepScorecard,
  TeamComparisonResponse,
  TeamRollup,
  TeamRollupHierarchyTeam,
  TeamTrend,
  TimelineEntry,
  Transcript,
  TranscriptUpload,
  UsageSummary,
  VelocityResponse,
} from './api-types';
import type { CommandCenterResponse } from './pipeline-types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

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
    // Auto-logout on expired/invalid token so the user sees the login page
    if (res.status === 401) {
      triggerLogout();
    }
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
      apiFetch<Account>(`/api/accounts/${id}/forecast`, {
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
    batch: (items: BatchItemRequest[]) =>
      apiFetch<BatchAnalysisResponse>('/api/analyses/batch', {
        method: 'POST',
        body: JSON.stringify({ items }),
      }),
    cancelBatch: (batchId: string) =>
      apiFetch<{ status: string }>(`/api/analyses/batch/${batchId}/cancel`, { method: 'POST' }),
  },
  dashboard: {
    pipeline: (team?: string) =>
      apiFetch<PipelineOverview>(`/api/dashboard/pipeline${team ? `?team=${team}` : ''}`),
    divergence: (teamId?: string) =>
      apiFetch<DivergenceItem[]>(`/api/dashboard/divergence${teamId ? `?team_id=${teamId}` : ''}`),
    teamRollup: (team?: string) =>
      apiFetch<TeamRollup[]>(`/api/dashboard/team-rollup${team ? `?team=${team}` : ''}`),
    teamRollupHierarchy: (teamId?: string) =>
      apiFetch<TeamRollupHierarchyTeam[]>(`/api/dashboard/team-rollup/hierarchy${teamId ? `?team_id=${teamId}` : ''}`),
    insights: () => apiFetch<InsightsResponse>('/api/dashboard/insights'),
    dealTrends: (params?: { account_id?: string; weeks?: number }) =>
      apiFetch<DealTrend[]>(`/api/dashboard/trends/deals?${new URLSearchParams(params as Record<string, string>)}`),
    teamTrends: (weeks?: number) =>
      apiFetch<TeamTrend[]>(`/api/dashboard/trends/teams?weeks=${weeks ?? 4}`),
    portfolioSummary: (weeks?: number) =>
      apiFetch<PortfolioSummary>(`/api/dashboard/trends/portfolio?weeks=${weeks ?? 4}`),
    commandCenter: (params?: { team?: string; ae?: string; period?: string; quarter?: string }) => {
      const sp = new URLSearchParams();
      if (params?.team) sp.set('team', params.team);
      if (params?.ae) sp.set('ae', params.ae);
      if (params?.period) sp.set('period', params.period);
      if (params?.quarter) sp.set('quarter', params.quarter);
      const qs = sp.toString();
      return apiFetch<CommandCenterResponse>(`/api/dashboard/command-center${qs ? `?${qs}` : ''}`);
    },
    trendsPipelineFlow: (weeks?: number) =>
      apiFetch<PipelineFlowResponse>(`/api/dashboard/trends/pipeline-flow?weeks=${weeks ?? 4}`),
    trendsForecastMovement: (weeks?: number) =>
      apiFetch<ForecastMovementResponse>(`/api/dashboard/trends/forecast-migration?weeks=${weeks ?? 4}`),
    trendsDealHealth: (weeks?: number) =>
      apiFetch<DealHealthResponse>(`/api/dashboard/trends/deal-health?weeks=${weeks ?? 4}`),
    trendsVelocity: (weeks?: number) =>
      apiFetch<VelocityResponse>(`/api/dashboard/trends/velocity?weeks=${weeks ?? 4}`),
    trendsTeamComparison: (weeks?: number) =>
      apiFetch<TeamComparisonResponse>(`/api/dashboard/trends/team-comparison?weeks=${weeks ?? 4}`),
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
    data: (teamId?: string) =>
      apiFetch<ForecastData[]>(`/api/forecast/data${teamId ? `?team_id=${teamId}` : ''}`),
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
      apiFetch<EnrichedDriveAccount[]>('/api/gdrive/accounts', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    callsStatus: (accountPath: string, accountName?: string, dbAccountId?: string) =>
      apiFetch<{ calls: EnrichedCall[] }>('/api/gdrive/calls-status', {
        method: 'POST',
        body: JSON.stringify({
          account_path: accountPath,
          account_name: accountName,
          db_account_id: dbAccountId,
        }),
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
  preferences: {
    get: (key: string) => apiFetch<any>(`/api/preferences/${key}`),
    save: (key: string, value: any) =>
      apiFetch<any>(`/api/preferences/${key}`, {
        method: 'PUT',
        body: JSON.stringify({ value }),
      }),
  },

  // Team & User management (admin)
  teams: {
    list: () => apiFetch<HierarchyTeam[]>('/api/teams/'),
    create: (data: { name: string; level: string; parent_id?: string; leader_id?: string }) =>
      apiFetch<any>('/api/teams/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name?: string; parent_id?: string; leader_id?: string }) =>
      apiFetch<any>(`/api/teams/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    members: (id: string) => apiFetch<any[]>(`/api/teams/${id}/members`),
  },
  users: {
    list: () => apiFetch<any[]>('/api/users/'),
    listICs: () => apiFetch<ICUser[]>('/api/users/ics'),
    create: (data: { name: string; email: string; role: string; team_id?: string }) =>
      apiFetch<any>('/api/users/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name?: string; role?: string; team_id?: string; is_active?: boolean }) =>
      apiFetch<any>(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  },
  dealContext: {
    upsert: (data: DealContextUpsert) =>
      apiFetch<{ account_id: string; entries: DealContextEntryInput[] }>('/api/deal-context/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (accountId: string) =>
      apiFetch<DealContextResponse>(`/api/deal-context/${accountId}`),
    questions: () =>
      apiFetch<Record<string, DealContextQuestion>>('/api/deal-context/questions'),
  },
};

// Re-export types for consumers
export type * from './api-types';
