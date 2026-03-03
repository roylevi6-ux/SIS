import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export interface WidgetConfig {
  id: string;
  label: string;
  description: string;
  visible: boolean;
  order: number;
}

export const DEFAULT_DEAL_WIDGETS: WidgetConfig[] = [
  // Active widgets — default visible, ordered for clean first impression
  { id: 'status_strip', label: 'Status Strip', description: 'Health, stage, forecast, and confidence badges', visible: true, order: 0 },
  { id: 'call_timeline', label: 'Call Timeline', description: 'Chronological view of all calls', visible: true, order: 1 },
  { id: 'vp_brief', label: 'VP Brief', description: 'Blunt advisor brief for VP/leadership', visible: true, order: 2 },
  { id: 'what_changed', label: 'What Changed', description: 'Metric deltas between latest and previous run', visible: true, order: 3 },
  { id: 'rep_action_plan', label: 'Rep Action Plan', description: 'Actions grouped by owner (AE/SE/Manager)', visible: true, order: 4 },
  { id: 'deal_narrative', label: 'Deal Narrative', description: 'Structured deal memo with health-coded sections', visible: true, order: 5 },
  { id: 'health_breakdown', label: 'Health Breakdown', description: 'Radar chart and score table for health components', visible: true, order: 6 },
  { id: 'sf_gap', label: 'SF Gap Analysis', description: 'SIS vs Salesforce stage and forecast comparison (includes forecast rationale + divergence)', visible: true, order: 7 },
  { id: 'agent_analyses', label: 'Per-Agent Analysis', description: 'Collapsible cards for each agent\'s findings (includes key findings inline)', visible: true, order: 8 },
  { id: 'deal_timeline', label: 'Deal Timeline', description: 'Assessment history trend chart', visible: true, order: 9 },
  { id: 'analysis_history', label: 'Analysis History', description: 'List of past analysis runs', visible: true, order: 10 },
  { id: 'transcript_list', label: 'Transcripts', description: 'All uploaded transcripts for this account', visible: true, order: 11 },
  // Deprecated widgets — hidden by default, re-enable in Display Settings
  { id: 'key_metrics', label: 'Key Metrics', description: 'Top risk, top action, key unknown at a glance — covered by VP Brief', visible: false, order: 80 },
  { id: 'actions_risks', label: 'Actions & Risks', description: 'Recommended actions and risk signals — replaced by Rep Action Plan', visible: false, order: 81 },
  { id: 'positive_contradictions', label: 'Signals & Contradictions', description: 'Positive signals and contradiction map — covered by Deal Narrative', visible: false, order: 82 },
  { id: 'key_unknowns', label: 'Key Unknowns', description: 'Outstanding questions and unknowns — in Deal Narrative + VP Brief', visible: false, order: 83 },
  { id: 'forecast_divergence', label: 'Forecast Divergence', description: 'AI vs IC forecast divergence — folded into SF Gap card', visible: false, order: 84 },
  { id: 'forecast_rationale', label: 'Forecast Rationale', description: 'Reasoning behind the AI forecast — folded into SF Gap card', visible: false, order: 85 },
  { id: 'key_findings', label: 'Key Findings', description: 'Per-agent insights — folded into Per-Agent Analysis cards', visible: false, order: 86 },
  { id: 'deal_memo', label: 'Deal Memo (Legacy)', description: 'Old flat deal memo — replaced by Deal Narrative', visible: false, order: 90 },
  { id: 'manager_actions', label: 'Manager Actions (Legacy)', description: 'Old manager actions — replaced by Key Findings + Rep Action Plan', visible: false, order: 91 },
];

/** Widgets replaced by newer versions — hide in saved prefs. */
const DEPRECATED_WIDGETS = new Set([
  'deal_memo', 'manager_actions',
  'key_metrics', 'actions_risks', 'positive_contradictions',
  'key_unknowns', 'forecast_divergence', 'forecast_rationale', 'key_findings',
]);

/** Merge new widgets into saved prefs and hide deprecated ones. */
function mergeNewDefaults(saved: WidgetConfig[], defaults: WidgetConfig[]): WidgetConfig[] {
  const savedIds = new Set(saved.map((w) => w.id));
  const maxOrder = Math.max(...saved.map((w) => w.order), 0);
  const newWidgets = defaults
    .filter((d) => !savedIds.has(d.id))
    .map((d, i) => ({ ...d, order: maxOrder + 1 + i }));
  const merged = newWidgets.length > 0 ? [...saved, ...newWidgets] : saved;
  return merged.map((w) =>
    DEPRECATED_WIDGETS.has(w.id) ? { ...w, visible: false } : w,
  );
}

export function useDealPageWidgets() {
  return useQuery({
    queryKey: ['preferences', 'deal_page_widgets'],
    queryFn: async () => {
      try {
        const data = await api.preferences.get('deal_page_widgets');
        const widgets = (data.widgets ?? []) as WidgetConfig[];
        return widgets.length > 0
          ? mergeNewDefaults(widgets, DEFAULT_DEAL_WIDGETS)
          : DEFAULT_DEAL_WIDGETS;
      } catch {
        return DEFAULT_DEAL_WIDGETS;
      }
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useSaveDealPageWidgets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (widgets: WidgetConfig[]) =>
      api.preferences.save('deal_page_widgets', { widgets }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['preferences', 'deal_page_widgets'] }),
  });
}

export const DEFAULT_PIPELINE_WIDGETS: WidgetConfig[] = [
  { id: 'number_line', label: 'Number Line', description: 'Pipeline stage funnel visualization', visible: true, order: 0 },
  { id: 'attention_strip', label: 'Attention Strip', description: 'Deals needing immediate attention', visible: true, order: 1 },
  { id: 'pipeline_changes', label: 'Pipeline Changes', description: 'Recent deal movements and updates', visible: true, order: 2 },
  { id: 'filter_chips', label: 'Filter Chips', description: 'Quick filters for deal table', visible: true, order: 3 },
  { id: 'team_forecast_grid', label: 'Team Forecast Grid', description: 'Team-level forecast summary (VP+ only)', visible: true, order: 4 },
  { id: 'deal_table', label: 'Deal Table', description: 'Main pipeline data table', visible: true, order: 5 },
];

export function usePipelineWidgets() {
  return useQuery({
    queryKey: ['preferences', 'pipeline_page_widgets'],
    queryFn: async () => {
      try {
        const data = await api.preferences.get('pipeline_page_widgets');
        const widgets = (data.widgets ?? []) as WidgetConfig[];
        return widgets.length > 0 ? widgets : DEFAULT_PIPELINE_WIDGETS;
      } catch {
        return DEFAULT_PIPELINE_WIDGETS;
      }
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useSavePipelineWidgets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (widgets: WidgetConfig[]) =>
      api.preferences.save('pipeline_page_widgets', { widgets }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['preferences', 'pipeline_page_widgets'] }),
  });
}
