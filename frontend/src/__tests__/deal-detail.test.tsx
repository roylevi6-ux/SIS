import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HealthBadge } from '@/components/health-badge';
import { DealMemo } from '@/components/deal-memo';
import { AgentCard } from '@/components/agent-card';
import { ActionsList } from '@/components/actions-list';

// ---------------------------------------------------------------------------
// Mock recharts ResponsiveContainer (it needs a real DOM size measurement)
// ---------------------------------------------------------------------------

vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

// ---------------------------------------------------------------------------
// Mock data (mirrors what the deal detail page would receive)
// ---------------------------------------------------------------------------

const mockAssessment = {
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
  top_risks: [
    'Competitor mentioned in last call',
    'Decision timeline may slip to next quarter',
  ],
  top_positive_signals: [
    'Economic buyer actively participating in calls',
    'Technical POC completed successfully',
  ],
  recommended_actions: [
    'Schedule executive alignment meeting',
    'Send ROI analysis to CFO',
  ],
};

const mockAgentAnalyses = [
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
// HealthBadge Tests
// ---------------------------------------------------------------------------

describe('HealthBadge', () => {
  it('renders a healthy score (>=70) with the score value', () => {
    render(<HealthBadge score={82} />);
    expect(screen.getByText('82')).toBeInTheDocument();
  });

  it('renders an at-risk score (45-69) with the score value', () => {
    render(<HealthBadge score={55} />);
    expect(screen.getByText('55')).toBeInTheDocument();
  });

  it('renders a critical score (<45) with the score value', () => {
    render(<HealthBadge score={32} />);
    expect(screen.getByText('32')).toBeInTheDocument();
  });

  it('renders N/A for null score', () => {
    render(<HealthBadge score={null} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// DealMemo Tests
// ---------------------------------------------------------------------------

describe('DealMemo', () => {
  it('renders deal memo text', () => {
    render(<DealMemo memo={mockAssessment.deal_memo} />);
    expect(screen.getByText('Deal Memo')).toBeInTheDocument();
    expect(
      screen.getByText('Strong deal with clear path to close. Economic buyer engaged.'),
    ).toBeInTheDocument();
  });

  it('renders empty state when memo is null', () => {
    render(<DealMemo memo={null} />);
    expect(screen.getByText('Deal Memo')).toBeInTheDocument();
    expect(
      screen.getByText('No deal memo available. Run an analysis to generate one.'),
    ).toBeInTheDocument();
  });

  it('renders tab triggers for brief and summary', () => {
    render(<DealMemo memo={mockAssessment.deal_memo} />);
    expect(screen.getByRole('tab', { name: /TL Insider Brief/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Leadership Summary/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// AgentCard Tests
// ---------------------------------------------------------------------------

describe('AgentCard', () => {
  it('renders agent name and confidence', () => {
    render(<AgentCard analysis={mockAgentAnalyses[0]} />);
    expect(screen.getByText('Economic Buyer Analyst')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
  });

  it('renders sparse data indicator when flagged', () => {
    render(<AgentCard analysis={mockAgentAnalyses[1]} />);
    expect(screen.getByText('Competitive Position Analyst')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('renders multiple agent cards', () => {
    render(
      <div>
        {mockAgentAnalyses.map((agent) => (
          <AgentCard key={agent.id} analysis={agent} />
        ))}
      </div>,
    );
    expect(screen.getByText('Economic Buyer Analyst')).toBeInTheDocument();
    expect(screen.getByText('Competitive Position Analyst')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ActionsList Tests
// ---------------------------------------------------------------------------

describe('ActionsList', () => {
  it('renders recommended actions', () => {
    render(<ActionsList actions={mockAssessment.recommended_actions} />);
    expect(screen.getByText('Recommended Actions')).toBeInTheDocument();
    expect(screen.getByText('Schedule executive alignment meeting')).toBeInTheDocument();
    expect(screen.getByText('Send ROI analysis to CFO')).toBeInTheDocument();
  });

  it('renders empty state when no actions', () => {
    render(<ActionsList actions={null} />);
    expect(screen.getByText('Recommended Actions')).toBeInTheDocument();
    expect(screen.getByText('No actions recommended.')).toBeInTheDocument();
  });
});
