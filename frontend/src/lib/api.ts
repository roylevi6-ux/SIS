import { getStoredToken } from './auth';

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
      apiFetch<any[]>(`/api/accounts/?${new URLSearchParams(params as any)}`),
    get: (id: string) => apiFetch<any>(`/api/accounts/${id}`),
    create: (data: any) =>
      apiFetch<any>('/api/accounts/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: any) =>
      apiFetch<any>(`/api/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    setForecast: (id: string, category: string) =>
      apiFetch<any>(`/api/accounts/${id}/ic-forecast`, {
        method: 'POST',
        body: JSON.stringify({ category }),
      }),
  },
  transcripts: {
    list: (accountId: string, activeOnly?: boolean) =>
      apiFetch<any[]>(`/api/transcripts/${accountId}?active_only=${activeOnly ?? true}`),
    upload: (data: any) =>
      apiFetch<any>('/api/transcripts/', { method: 'POST', body: JSON.stringify(data) }),
  },
  analyses: {
    run: (accountId: string) =>
      apiFetch<any>('/api/analyses/', {
        method: 'POST',
        body: JSON.stringify({ account_id: accountId }),
      }),
    history: (accountId: string) => apiFetch<any[]>(`/api/analyses/history/${accountId}`),
    agents: (runId: string) => apiFetch<any[]>(`/api/analyses/${runId}/agents`),
    rerun: (runId: string, agentId: string) =>
      apiFetch<any>(`/api/analyses/${runId}/rerun/${agentId}`, { method: 'POST' }),
    resynthesize: (runId: string) =>
      apiFetch<any>(`/api/analyses/${runId}/resynthesize`, { method: 'POST' }),
    delta: (accountId: string) =>
      apiFetch<any>(`/api/analyses/delta/${accountId}`),
    timeline: (accountId: string) =>
      apiFetch<any[]>(`/api/analyses/timeline/${accountId}`),
  },
  dashboard: {
    pipeline: (team?: string) =>
      apiFetch<any>(`/api/dashboard/pipeline${team ? `?team=${team}` : ''}`),
    divergence: (team?: string) =>
      apiFetch<any[]>(`/api/dashboard/divergence${team ? `?team=${team}` : ''}`),
    teamRollup: (team?: string) =>
      apiFetch<any[]>(`/api/dashboard/team-rollup${team ? `?team=${team}` : ''}`),
    insights: () => apiFetch<any>('/api/dashboard/insights'),
    dealTrends: (params?: { account_id?: string; weeks?: number }) =>
      apiFetch<any[]>(`/api/dashboard/trends/deals?${new URLSearchParams(params as any)}`),
    teamTrends: (weeks?: number) =>
      apiFetch<any[]>(`/api/dashboard/trends/teams?weeks=${weeks ?? 4}`),
    portfolioSummary: (weeks?: number) =>
      apiFetch<any>(`/api/dashboard/trends/portfolio?weeks=${weeks ?? 4}`),
  },
  feedback: {
    submit: (data: any) =>
      apiFetch<any>('/api/feedback/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params?: { account_id?: string; author?: string; status?: string }) =>
      apiFetch<any[]>(`/api/feedback/?${new URLSearchParams(params as any)}`),
    resolve: (id: string, data: any) =>
      apiFetch<any>(`/api/feedback/${id}/resolve`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    summary: () => apiFetch<any>('/api/feedback/summary'),
  },
  chat: {
    query: (message: string, history?: any[]) =>
      apiFetch<{ response: string }>('/api/chat/query', {
        method: 'POST',
        body: JSON.stringify({ message, history }),
      }),
  },
  calibration: {
    current: () => apiFetch<any>('/api/calibration/current'),
    patterns: () => apiFetch<any>('/api/calibration/patterns'),
    create: (data: any) =>
      apiFetch<any>('/api/calibration/', { method: 'POST', body: JSON.stringify(data) }),
    history: () => apiFetch<any[]>('/api/calibration/history'),
  },
  tracking: {
    summary: (days?: number) => apiFetch<any>(`/api/tracking/summary?days=${days ?? 30}`),
    croMetrics: () => apiFetch<any[]>('/api/tracking/cro-metrics'),
  },
  coaching: {
    submit: (data: any) =>
      apiFetch<any>('/api/coaching/', { method: 'POST', body: JSON.stringify(data) }),
    list: (params?: any) =>
      apiFetch<any[]>(`/api/coaching/?${new URLSearchParams(params)}`),
    summary: (repName?: string) =>
      apiFetch<any>(`/api/coaching/summary${repName ? `?rep_name=${repName}` : ''}`),
  },
  prompts: {
    list: (agentId?: string) =>
      apiFetch<any[]>(`/api/prompts/versions${agentId ? `?agent_id=${agentId}` : ''}`),
    create: (data: any) =>
      apiFetch<any>('/api/prompts/versions', { method: 'POST', body: JSON.stringify(data) }),
  },
  scorecard: {
    reps: (aeOwner?: string) =>
      apiFetch<any[]>(`/api/scorecard/reps${aeOwner ? `?ae_owner=${aeOwner}` : ''}`),
  },
  forecast: {
    data: (team?: string) =>
      apiFetch<any[]>(`/api/forecast/data${team ? `?team=${team}` : ''}`),
    teams: () => apiFetch<string[]>('/api/forecast/teams'),
  },
  export: {
    brief: (accountId: string, format?: string) =>
      apiFetch<{ content: string }>(
        `/api/export/brief/${accountId}${format ? `?format=${format}` : ''}`,
      ),
    forecast: (params?: { team?: string; format?: string }) =>
      apiFetch<{ content: string }>(`/api/export/forecast?${new URLSearchParams(params as any)}`),
  },
  logs: {
    actions: (params?: any) =>
      apiFetch<any[]>(`/api/logs/actions?${new URLSearchParams(params)}`),
    summary: (days?: number) =>
      apiFetch<any>(`/api/logs/actions/summary?days=${days ?? 30}`),
  },
  gdrive: {
    config: () => apiFetch<{ path: string }>('/api/gdrive/config'),
    validate: (path: string) =>
      apiFetch<{ is_valid: boolean; message: string }>('/api/gdrive/validate', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    listAccounts: (path: string) =>
      apiFetch<any[]>('/api/gdrive/accounts', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),
    listCalls: (accountName: string, accountPath: string, maxCalls?: number) =>
      apiFetch<any[]>('/api/gdrive/calls', {
        method: 'POST',
        body: JSON.stringify({ account_name: accountName, account_path: accountPath, max_calls: maxCalls ?? 5 }),
      }),
    import: (accountName: string, accountPath: string, maxCalls?: number, dealArgs?: any) =>
      apiFetch<any>('/api/gdrive/import', {
        method: 'POST',
        body: JSON.stringify({ account_name: accountName, account_path: accountPath, max_calls: maxCalls ?? 5, ...dealArgs }),
      }),
  },
};
