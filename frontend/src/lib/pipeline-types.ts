export interface PipelineDeal {
  account_id: string;
  account_name: string;
  mrr_estimate: number | null;
  team_lead: string | null;
  ae_owner: string | null;
  team_name: string | null;
  ic_forecast_category: string | null;
  last_call_date: string | null;
  health_score: number | null;
  momentum_direction: string | null;
  ai_forecast_category: string | null;
  inferred_stage: number | null;
  stage_name: string | null;
  overall_confidence: number | null;
  divergence_flag: boolean;
  deal_memo_preview: string | null;
}

export interface PipelineSummary {
  healthy_count: number;
  at_risk_count: number;
  critical_count: number;
  unscored_count: number;
  total_mrr_healthy: number;
  total_mrr_at_risk: number;
  total_mrr_critical: number;
}

export interface PipelineOverviewResponse {
  total_deals: number;
  healthy: PipelineDeal[];
  at_risk: PipelineDeal[];
  critical: PipelineDeal[];
  unscored: PipelineDeal[];
  summary: PipelineSummary;
}
