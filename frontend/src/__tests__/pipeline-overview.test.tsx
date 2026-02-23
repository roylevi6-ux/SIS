import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/auth';
import PipelinePage from '@/app/pipeline/page';

// ---------------------------------------------------------------------------
// Mock Next.js navigation (required by DealTable's useRouter)
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
// Test wrapper with providers
// ---------------------------------------------------------------------------

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
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

describe('PipelinePage', () => {
  it('renders loading skeleton initially', () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    // The page title should be visible
    expect(screen.getByText('Pipeline Overview')).toBeInTheDocument();
    // Loading subtitle should appear
    expect(screen.getByText('Loading pipeline data...')).toBeInTheDocument();
  });

  it('renders deal data after loading', async () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    // Wait for the mock data to load via MSW
    await waitFor(() => {
      expect(screen.getByText('4 total deals across all tiers')).toBeInTheDocument();
    });

    // Summary cards should show counts
    expect(screen.getByText('Healthy')).toBeInTheDocument();
    expect(screen.getByText('At Risk')).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.getByText('Unscored')).toBeInTheDocument();

    // Deal names from mock data should appear in the table
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Beta Industries')).toBeInTheDocument();
    expect(screen.getByText('Gamma Solutions')).toBeInTheDocument();
    expect(screen.getByText('Delta Tech')).toBeInTheDocument();
  });

  it('renders tab triggers with counts', async () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText('4 total deals across all tiers')).toBeInTheDocument();
    });

    // Tab triggers should include counts
    expect(screen.getByRole('tab', { name: /All \(4\)/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Healthy \(1\)/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /At Risk \(1\)/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Critical \(1\)/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Unscored \(1\)/ })).toBeInTheDocument();
  });

  it('renders health badges with correct scores', async () => {
    render(
      <TestWrapper>
        <PipelinePage />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    // Health scores from mock data: 82 (healthy), 55 (at_risk), 32 (critical), null (N/A)
    expect(screen.getByText('82')).toBeInTheDocument();
    expect(screen.getByText('55')).toBeInTheDocument();
    expect(screen.getByText('32')).toBeInTheDocument();
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});
