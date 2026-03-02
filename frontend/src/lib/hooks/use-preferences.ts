import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export interface WidgetConfig {
  id: string;
  label: string;
  description: string;
  visible: boolean;
  order: number;
}

export function useDealPageWidgets() {
  return useQuery({
    queryKey: ['preferences', 'deal_page_widgets'],
    queryFn: async () => {
      const data = await api.preferences.get('deal_page_widgets');
      return (data.widgets ?? []) as WidgetConfig[];
    },
    staleTime: 5 * 60 * 1000, // 5 min — prefs don't change often
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
