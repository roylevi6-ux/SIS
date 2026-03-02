import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/auth';
import PipelinePage from '@/app/pipeline/page';

// ---------------------------------------------------------------------------
// Mock Next.js navigation
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/pipeline',
  useSearchParams: () => new URLSearchParams(),
}));

// ---------------------------------------------------------------------------
// Mock API — vi.hoisted() so the data is available when vi.mock is hoisted
// ---------------------------------------------------------------------------

const { MOCK_COMMAND_CENTER } = vi.hoisted(() => ({
  MOCK_COMMAND_CENTER: {
    quota: { amount: 500000, period: '2026' },
    pipeline: { total_value: 320000, total_deals: 3, coverage: 1.2, weighted_value: 250000, gap: -20000 },
    forecast_breakdown: {
      commit: { count: 1, value: 120000 },
      realistic: { count: 1, value: 100000 },
      upside: { count: 1, value: 80000 },
      risk: { count: 0, value: 0 },
    },
    attention_items: [],
    changes_this_week: { added: 1, dropped: 0, net: 1, stage_advances: 0, forecast_flips: 0, new_risks: 0 },
    deals: [
      {
        account_id: 'a1', account_name: 'Acme Corp', cp_estimate: 120000, team_lead: 'Alice',
        ae_owner: 'Bob', team_name: 'Team Alpha', sf_forecast_category: 'Commit',
        last_call_date: '2026-02-20', health_score: 82, momentum_direction: 'Improving',
        ai_forecast_category: 'Commit', inferred_stage: 4, stage_name: 'Proposal',
        overall_confidence: 0.85, divergence_flag: false, deal_memo_preview: null, deal_type: 'New',
      },
      {
        account_id: 'a2', account_name: 'Beta Industries', cp_estimate: 100000, team_lead: 'Alice',
        ae_owner: 'Carol', team_name: 'Team Alpha', sf_forecast_category: 'Realistic',
        last_call_date: '2026-02-18', health_score: 55, momentum_direction: 'Stable',
        ai_forecast_category: 'Realistic', inferred_stage: 3, stage_name: 'Evaluation',
        overall_confidence: 0.60, divergence_flag: false, deal_memo_preview: null, deal_type: 'Expansion',
      },
      {
        account_id: 'a3', account_name: 'Gamma Solutions', cp_estimate: 80000, team_lead: 'Dave',
        ae_owner: 'Eve', team_name: 'Team Beta', sf_forecast_category: 'Upside',
        last_call_date: '2026-02-01', health_score: 32, momentum_direction: 'Declining',
        ai_forecast_category: 'Upside', inferred_stage: 2, stage_name: 'Discovery',
        overall_confidence: 0.40, divergence_flag: true, deal_memo_preview: 'Low engagement', deal_type: 'New',
      },
    ],
  },
}));

vi.mock('@/lib/api', () => ({
  api: {
    dashboard: {
      commandCenter: vi.fn().mockResolvedValue(MOCK_COMMAND_CENTER),
    },
    teams: {
      list: vi.fn().mockResolvedValue([]),
    },
  },
}));

// ---------------------------------------------------------------------------
// Test wrapper
// ---------------------------------------------------------------------------

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PipelineCommandCenter', () => {
  it('renders page title and loading state', () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    expect(screen.getByText('Pipeline Command Center')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders deal count after data loads', async () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText('3 deals across your pipeline')).toBeInTheDocument();
    });
  });

  it('renders deal names in the table', async () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    expect(screen.getByText('Beta Industries')).toBeInTheDocument();
    expect(screen.getByText('Gamma Solutions')).toBeInTheDocument();
  });

  it('renders quarter selector with current quarter', () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    // Quarter selector should be present
    expect(screen.getByText(/Q[1-4] 2026|Full Year 2026/)).toBeInTheDocument();
  });
});
