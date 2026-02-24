/**
 * TypeScript types for the SIS API responses.
 * Derived from the FastAPI/Pydantic backend schemas.
 */

// ── Auth ──
export interface LoginResponse {
  token: string;
  username: string;
  role: string;
}

export interface UserInfo {
  username: string;
  role: string;
}

// ── Accounts ──
export interface Account {
  id: string;
  account_name: string;
  mrr_estimate: number | null;
  team_lead: string | null;
  ae_owner: string | null;
  ic_forecast_category: string | null;
  health_score: number | null;
  momentum_direction: string | null;
  ai_forecast_category: string | null;
  inferred_stage: number | null;
  stage_name: string | null;
  divergence_flag: boolean;
  created_at: string;
  updated_at: string;
  // Backend may include additional fields (assessment data, etc.)
  [key: string]: unknown;
}

export interface AccountCreate {
  account_name: string;
  mrr_estimate?: number;
  team_lead?: string;
  ae_owner?: string;
}

// ── Transcripts ──
export interface Transcript {
  id: string;
  account_id: string;
  gong_call_id: string | null;
  call_title: string | null;
  call_date: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TranscriptUpload {
  account_id: string;
  raw_text: string;
  gong_call_id?: string;
  call_title?: string;
  call_date?: string;
  duration_minutes?: number | null;
}

// ── Analyses ──
export interface AnalysisRunResponse {
  run_id: string;
  status: string;
}

export interface AnalysisHistoryItem {
  run_id: string;
  account_id: string;
  status: string;
  health_score: number | null;
  deal_type: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  cost_summary: CostSummary | null;
  total_cost_usd?: number;
  total_input_tokens?: number;
  total_output_tokens?: number;
  [key: string]: unknown;
}

export interface AgentAnalysisResponse {
  id?: string;
  agent_id: string;
  agent_name: string;
  findings: Record<string, unknown>;
  evidence: Array<{ quote: string; interpretation: string }>;
  narrative: string;
  confidence: { overall: number; rationale: string; data_gaps: string[] };
  sparse_data_flag: boolean;
  transcript_count_analyzed: number;
  [key: string]: unknown;
}

export interface DeltaResponse {
  account_id: string;
  current_run_id: string;
  previous_run_id: string | null;
  deltas: Record<string, AgentDelta>;
  fields?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AgentDelta {
  agent_id: string;
  changed: boolean;
  summary: string | null;
}

export interface TimelineEntry {
  run_id: string;
  created_at: string;
  health_score: number | null;
  momentum_direction: string | null;
  stage_name: string | null;
}

// ── Dashboard ──
export interface PipelineOverview {
  total_deals: number;
  summary: {
    healthy_count: number;
    at_risk_count: number;
    critical_count: number;
    total_mrr_healthy: number;
    total_mrr_at_risk: number;
    total_mrr_critical: number;
  };
  deals: Account[];
}

export interface DivergenceItem {
  account_id: string;
  account_name: string;
  ai_forecast_category: string;
  ic_forecast_category: string;
  mrr_estimate: number;
  health_score: number | null;
}

export interface TeamRollup {
  team_name: string;
  total_deals: number;
  avg_health_score: number | null;
  total_mrr: number;
  divergent_count: number;
}

export interface PipelineInsight {
  account_id: string;
  account_name: string;
  health_score: number | null;
  description: string;
  mrr_estimate?: number | null;
  team_name?: string | null;
  ae_owner?: string | null;
  momentum_direction?: string | null;
  ai_forecast_category?: string | null;
  inferred_stage?: number | null;
  stage_name?: string | null;
  previous_health_score?: number | null;
  delta?: number | null;
  previous_forecast?: string | null;
  current_forecast?: string | null;
  last_call_date?: string | null;
  days_since_call?: number | null;
}

export interface InsightsResponse {
  stuck: PipelineInsight[];
  improving: PipelineInsight[];
  declining: PipelineInsight[];
  new_risks: PipelineInsight[];
  stale: PipelineInsight[];
  forecast_flips: PipelineInsight[];
}

export interface CarryForwardAction {
  action: string;
  priority: string;
  owner?: string;
  rationale?: string;
  status: 'unfollowed';
}

export interface DealTrend {
  account_id: string;
  account_name: string;
  week: string;
  health_score: number | null;
  momentum_direction: string | null;
}

export interface TeamTrend {
  team_name: string;
  week: string;
  avg_health_score: number;
  deal_count: number;
}

export interface PortfolioSummary {
  weeks: Array<{
    week: string;
    avg_health_score: number;
    total_deals: number;
    healthy_pct: number;
  }>;
}

// ── Feedback ──
export interface FeedbackItem {
  id: string;
  account_id: string;
  agent_id: string;
  author: string;
  feedback_text: string;
  status: string;
  resolution_note: string | null;
  created_at: string;
  [key: string]: unknown;
}

export interface FeedbackSubmit {
  account_id: string;
  agent_id: string;
  feedback_text: string;
  author?: string;
}

export interface FeedbackSummary {
  total: number;
  pending: number;
  resolved: number;
  by_agent: Record<string, number>;
  by_status?: Record<string, number>;
  by_direction?: Record<string, number>;
  [key: string]: unknown;
}

// ── Chat ──
export interface ChatResponse {
  response: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

// ── Calibration ──
export interface CalibrationSnapshot {
  id: string;
  snapshot_data: Record<string, unknown>;
  created_at: string;
  [key: string]: unknown;
}

// ── Tracking / Admin ──
export interface UsageSummary {
  total_events: number;
  days: number;
  by_type: Record<string, number>;
  by_day: Record<string, number>;
  by_user: Record<string, number>;
  by_page: Record<string, number>;
}

export interface CROMetric {
  metric_name: string;
  value: number;
  trend: string;
}

export interface CoachingNote {
  id: string;
  rep_name: string;
  note_text: string;
  author: string;
  created_at: string;
}

export interface CoachingSummary {
  rep_name: string;
  total_notes: number;
  recent_notes: CoachingNote[];
}

export interface PromptVersion {
  id: string;
  agent_id: string;
  version: number;
  system_prompt: string;
  created_at: string;
}

export interface RepScorecard {
  rep_name: string;
  dimensions: Record<string, number>;
  overall_score: number;
}

export interface ForecastData {
  account_id: string;
  account_name: string;
  ai_forecast_category: string;
  ic_forecast_category: string | null;
  mrr_estimate: number;
  health_score: number | null;
  [key: string]: unknown;
}

// ── Export ──
export interface ExportResponse {
  content: string;
}

// ── Action Logs ──
export interface ActionLog {
  id: string;
  action_type: string;
  actor: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface ActionLogSummary {
  total_actions: number;
  by_type: Record<string, number>;
  by_actor: Record<string, number>;
}

// ── Google Drive ──
export interface GDriveConfig {
  path: string;
}

export interface GDriveValidation {
  is_valid: boolean;
  message: string;
}

export interface GDriveAccount {
  name: string;
  path: string;
  call_count: number;
}

export interface GDriveCall {
  filename: string;
  call_date: string | null;
  participants: string[];
}

export interface GDriveImportResult {
  account_id: string;
  transcripts_imported: number;
  skipped: number;
}

// ── Cost ──
export interface CostSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  agents: Array<{
    agent_id: string;
    model: string;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    elapsed_seconds: number;
    retries: number;
  }>;
}
