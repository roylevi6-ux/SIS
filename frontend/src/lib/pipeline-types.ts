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
  deal_type?: string | null;
}

// ---------------------------------------------------------------------------
// Command Center types
// ---------------------------------------------------------------------------

export interface CommandCenterQuota {
  amount: number;
  period: string;
}

export interface CommandCenterPipeline {
  total_value: number;
  total_deals: number;
  coverage: number;
  weighted_value: number;
  gap: number;
}

export interface ForecastCategory {
  count: number;
  value: number;
}

export interface ForecastBreakdown {
  commit: ForecastCategory;
  realistic: ForecastCategory;
  upside: ForecastCategory;
  risk: ForecastCategory;
}

export interface AttentionItem {
  account_id: string;
  account_name: string;
  mrr_estimate: number;
  reason: string;
  type: 'declining' | 'divergent' | 'stale';
}

export interface WeeklyChanges {
  added: number;
  dropped: number;
  net: number;
  stage_advances: number;
  forecast_flips: number;
  new_risks: number;
}

export interface CommandCenterResponse {
  quota: CommandCenterQuota;
  pipeline: CommandCenterPipeline;
  forecast_breakdown: ForecastBreakdown;
  attention_items: AttentionItem[];
  changes_this_week: WeeklyChanges;
  deals: PipelineDeal[];
}
