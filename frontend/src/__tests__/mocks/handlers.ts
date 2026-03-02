import { http, HttpResponse } from 'msw';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

export const mockPipelineData = {
  total_deals: 4,
  healthy: [
    {
      account_id: 'acc-001',
      account_name: 'Acme Corp',
      cp_estimate: 12000,
      team_lead: 'Sarah Chen',
      ae_owner: 'Mike Johnson',
      team_name: 'Enterprise',
      sf_forecast_category: 'Commit',
      last_call_date: '2026-02-20',
      health_score: 82,
      momentum_direction: 'Improving',
      ai_forecast_category: 'Commit',
      inferred_stage: 4,
      stage_name: 'Proposal',
      overall_confidence: 78,
      divergence_flag: false,
      deal_memo_preview: 'Strong engagement with economic buyer.',
    },
  ],
  at_risk: [
    {
      account_id: 'acc-002',
      account_name: 'Beta Industries',
      cp_estimate: 8500,
      team_lead: 'Sarah Chen',
      ae_owner: 'Lisa Park',
      team_name: 'Enterprise',
      sf_forecast_category: 'Realistic',
      last_call_date: '2026-02-15',
      health_score: 55,
      momentum_direction: 'Stable',
      ai_forecast_category: 'Realistic',
      inferred_stage: 3,
      stage_name: 'Scope',
      overall_confidence: 62,
      divergence_flag: false,
      deal_memo_preview: 'Technical evaluation in progress.',
    },
  ],
  critical: [
    {
      account_id: 'acc-003',
      account_name: 'Gamma Solutions',
      cp_estimate: 5000,
      team_lead: 'David Kim',
      ae_owner: 'Anna Lee',
      team_name: 'Mid-Market',
      sf_forecast_category: 'Commit',
      last_call_date: '2026-01-28',
      health_score: 32,
      momentum_direction: 'Declining',
      ai_forecast_category: 'Realistic',
      inferred_stage: 2,
      stage_name: 'Establish Business Case',
      overall_confidence: 45,
      divergence_flag: true,
      deal_memo_preview: 'Champion went silent after pricing discussion.',
    },
  ],
  unscored: [
    {
      account_id: 'acc-004',
      account_name: 'Delta Tech',
      cp_estimate: null,
      team_lead: null,
      ae_owner: 'Mike Johnson',
      team_name: 'Enterprise',
      sf_forecast_category: null,
      last_call_date: null,
      health_score: null,
      momentum_direction: null,
      ai_forecast_category: null,
      inferred_stage: null,
      stage_name: null,
      overall_confidence: null,
      divergence_flag: false,
      deal_memo_preview: null,
    },
  ],
  summary: {
    healthy_count: 1,
    at_risk_count: 1,
    critical_count: 1,
    unscored_count: 1,
    total_mrr_healthy: 12000,
    total_mrr_at_risk: 8500,
    total_mrr_critical: 5000,
  },
};

export const mockAccountDetail = {
  id: 'acc-001',
  account_name: 'Acme Corp',
  cp_estimate: 12000,
  team_lead: 'Sarah Chen',
  ae_owner: 'Mike Johnson',
  team_name: 'Enterprise',
  sf_forecast_category: 'Commit',
  transcripts: [
    {
      id: 'tr-001',
      call_date: '2026-02-20',
      duration_minutes: 45,
      token_count: 3200,
      is_active: true,
      created_at: '2026-02-20T10:00:00Z',
    },
  ],
  assessment: {
    id: 'assess-001',
    deal_memo: 'Strong deal with clear path to close. Economic buyer engaged.',
    health_score: 82,
    health_breakdown: {
      buyer_validated_pain_commercial_clarity: 78,
      momentum_quality: 75,
      champion_strength: 85,
      commitment_quality: 88,
      economic_buyer_engagement: 90,
      urgency_compelling_event: 72,
      stage_appropriateness: 80,
      multithreading_stakeholder_coverage: 70,
      competitive_position: 65,
      technical_path_clarity: 82,
    },
    momentum_direction: 'Improving',
    momentum_trend: 'up',
    ai_forecast_category: 'Commit',
    forecast_rationale: 'Multiple buying signals detected across recent calls.',
    inferred_stage: 4,
    stage_name: 'Proposal',
    stage_confidence: 85,
    overall_confidence: 78,
    key_unknowns: ['Budget approval timeline', 'Legal review status'],
    top_positive_signals: [
      'Economic buyer actively participating in calls',
      'Technical POC completed successfully',
    ],
    top_risks: [
      'Competitor mentioned in last call',
      'Decision timeline may slip to next quarter',
    ],
    recommended_actions: [
      'Schedule executive alignment meeting',
      'Send ROI analysis to CFO',
    ],
    contradiction_map: [],
    divergence_flag: false,
    divergence_explanation: null,
    created_at: '2026-02-20T12:00:00Z',
  },
};

export const mockAnalysisHistory = [
  {
    id: 'run-001',
    account_id: 'acc-001',
    status: 'completed',
    created_at: '2026-02-20T12:00:00Z',
    completed_at: '2026-02-20T12:05:00Z',
  },
];

export const mockAgentAnalyses = [
  {
    id: 'agent-001',
    agent_name: 'Economic Buyer Analyst',
    agent_id: 'economic_buyer',
    confidence_overall: 88,
    sparse_data_flag: false,
    narrative: 'Clear engagement from VP of Engineering who controls budget.',
    evidence: [
      { quote: 'We have budget allocated for Q1', source: 'Call 2026-02-20' },
    ],
    data_gaps: [],
    findings_summary: 'Strong economic buyer engagement detected.',
  },
  {
    id: 'agent-002',
    agent_name: 'Competitive Position Analyst',
    agent_id: 'competitive_position',
    confidence_overall: 65,
    sparse_data_flag: true,
    narrative: 'Limited competitive intelligence available.',
    evidence: [],
    data_gaps: ['No direct competitor comparison data'],
    findings_summary: 'Competitor mentioned but details sparse.',
  },
];

// ---------------------------------------------------------------------------
// MSW handlers
// ---------------------------------------------------------------------------

const API_BASE = 'http://localhost:8000';

export const handlers = [
  // Pipeline overview
  http.get(`${API_BASE}/api/dashboard/pipeline`, () => {
    return HttpResponse.json(mockPipelineData);
  }),

  // Account detail
  http.get(`${API_BASE}/api/accounts/:id`, ({ params }) => {
    const { id } = params;
    if (id === 'acc-001') {
      return HttpResponse.json(mockAccountDetail);
    }
    return HttpResponse.json(
      { detail: 'Account not found' },
      { status: 404 },
    );
  }),

  // Analysis history
  http.get(`${API_BASE}/api/analyses/history/:accountId`, () => {
    return HttpResponse.json(mockAnalysisHistory);
  }),

  // Agent analyses for a run
  http.get(`${API_BASE}/api/analyses/:runId/agents`, () => {
    return HttpResponse.json(mockAgentAnalyses);
  }),

  // Health check
  http.get(`${API_BASE}/api/health`, () => {
    return HttpResponse.json({ status: 'ok', version: '1.0.0' });
  }),

  // Login
  http.post(`${API_BASE}/api/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { username: string; role: string };
    return HttpResponse.json({
      token: 'mock-jwt-token-12345',
      username: body.username,
      role: body.role,
    });
  }),
];
