import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { StatusOverviewCards } from '../components/StatusOverviewCards';
import { MaturityWindowSection } from '../components/MaturityWindowSection';
import { OverdueEscalatedQueue } from '../components/OverdueEscalatedQueue';
import { VerificationQueueWidget } from '../components/VerificationQueueWidget';
import { CompletenessBlockersWidget } from '../components/CompletenessBlockersWidget';
import { MaturityLoadChart } from '../components/MaturityLoadChart';
import { PriorityQueueDesk } from '../components/PriorityQueueDesk';
import { CommandCenterPage } from '@/app/routes/CommandCenterPage';
import { commandCenterApi } from '@/api/commandCenter';
import type {
  StatusCountsResponse,
  MaturityWindowResponse,
  OverdueEscalatedResponse,
  VerificationQueueResponse,
  DocumentCompletenessResponse,
  ReleaseBlockersResponse,
  MonthWiseMaturityLoadResponse,
  PriorityQueueResponse,
} from '@/types/commandCenter';

// Mock auth context
vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-officer-1',
      email: 'officer@aicte.gov.in',
      role: 'SCRUTINY_OFFICER',
      full_name: 'Scrutiny Officer',
    },
    isAuthenticated: true,
  }),
}));

const mockStatusCounts: StatusCountsResponse = {
  metric_id: 'MTR-STAT-ALL',
  active_count: 15,
  expiring_soon_count: 4,
  matured_count: 3,
  renewed_count: 5,
  released_count: 8,
  pending_count: 2,
  total_instruments: 37,
  total_deposit_value: '37500000.00',
  window_days: 90,
  date_basis: 'Asia/Kolkata calendar date',
  metadata: {},
};

const mockMaturityWindow: MaturityWindowResponse = {
  metric_id: 'MTR-MAT-WINDOW',
  start_date: '2026-10-25',
  end_date: '2027-01-23',
  total_instruments: 4,
  total_deposit_value: '5000000.00',
  by_bank: { 'State Bank of India': 3, 'Canara Bank': 1 },
  by_office: { WRO_MUMBAI: 4 },
  page: 1,
  page_size: 50,
  total_records: 4,
  records: [
    {
      id: 'inst-1',
      reference_number: 'FDR-SBI-2026-001',
      institution_id: 'inst-alpha',
      institution_name: 'Alpha Engineering College',
      bank_name: 'State Bank of India',
      branch: 'Nariman Point',
      amount: '1000000.00',
      issue_date: '2025-10-25',
      maturity_date: '2026-11-20',
      days_to_maturity: 26,
      status: 'REGISTERED',
      trust_level: 'L2_OFFICER_VERIFIED',
      assigned_office: 'WRO_MUMBAI',
    },
  ],
};

const mockOverdueEscalated: OverdueEscalatedResponse = {
  metric_id: 'MTR-OVERDUE-ESCALATED',
  total_overdue: 2,
  total_escalated: 1,
  by_office: { WRO_MUMBAI: 2 },
  by_assignee: { 'user-officer-1': 2 },
  records: [
    {
      record_id: 'inst-matured-1',
      record_type: 'INSTRUMENT',
      reference_number: 'FDR-OVERDUE-01',
      institution_id: 'inst-alpha',
      institution_name: 'Alpha Engineering College',
      assigned_office: 'WRO_MUMBAI',
      assignee_name: 'Scrutiny Officer',
      due_date: '2026-10-10',
      days_overdue: 15,
      is_escalated: true,
      escalation_role: 'BRANCH_HEAD',
      due_condition: 'ESCALATED',
    },
  ],
};

const mockVerificationQueue: VerificationQueueResponse = {
  metric_id: 'MTR-VERIF-QUEUE',
  total_outstanding: 3,
  average_age_days: 12.5,
  age_distribution: { '<7d': 1, '7-14d': 1, '15-30d': 1, '>30d': 0 },
  source_unavailable_count: 1,
  failed_count: 0,
  records: [
    {
      request_id: 'vr-1',
      reference_code: 'VR-2026-001',
      instrument_id: 'inst-1',
      instrument_reference: 'FDR-SBI-2026-001',
      institution_id: 'inst-alpha',
      bank_name: 'State Bank of India',
      channel: 'SIMULATED',
      status: 'PENDING',
      created_at: '2026-10-15T10:00:00Z',
      age_days: 10,
      attempt_count: 1,
      is_source_unavailable: false,
    },
    {
      request_id: 'vr-2',
      reference_code: 'VR-2026-002',
      instrument_id: 'inst-2',
      instrument_reference: 'FDR-PNB-2026-002',
      institution_id: 'inst-alpha',
      bank_name: 'Punjab National Bank',
      channel: 'LIVE_BANK_API',
      status: 'SOURCE_UNAVAILABLE',
      created_at: '2026-10-05T10:00:00Z',
      age_days: 20,
      attempt_count: 3,
      is_source_unavailable: true,
    },
  ],
};

const mockCompleteness: DocumentCompletenessResponse = {
  metric_id: 'MTR-DOC-COMPLETENESS',
  policy_configured: false,
  policy_version: null,
  policy_status_message: 'POLICY_UNCONFIGURED: No active policy in effect.',
  present_count: 30,
  missing_count: 2,
  unreadable_count: 1,
  wrong_category_count: 0,
  awaiting_confirmation_count: 1,
  missing_categories_breakdown: { FDR_COPY: 2 },
  metadata: {},
};

const mockReleaseBlockers: ReleaseBlockersResponse = {
  metric_id: 'MTR-REL-BLOCKERS',
  policy_configured: true,
  policy_version: 1,
  total_active_release_requests: 3,
  blocked_requests_count: 1,
  ready_requests_count: 2,
  unmet_mandatory_items_count: 1,
  blockers_by_requirement_type: { DOCUMENT_COMPLETENESS: 1 },
  cases: [
    {
      case_id: 'rel-case-1',
      case_number: 'REL-2026-0001',
      instrument_id: 'inst-1',
      instrument_reference: 'FDR-SBI-2026-001',
      institution_id: 'inst-alpha',
      case_type: 'STANDARD_MATURITY_RELEASE',
      workflow_status: 'UNDER_REVIEW',
      blockers_count: 1,
      unsatisfied_item_codes: ['CHK-DOC-FDR'],
      latest_assessment_outcome: 'BLOCKED',
    },
  ],
};

const mockMaturityLoad: MonthWiseMaturityLoadResponse = {
  metric_id: 'MTR-MAT-LOAD',
  calendar_year: 2026,
  points: [
    { year: 2026, month: 10, month_label: '2026-10', instrument_count: 2, total_amount: '2000000.00' },
    { year: 2026, month: 11, month_label: '2026-11', instrument_count: 4, total_amount: '5000000.00' },
    { year: 2026, month: 12, month_label: '2026-12', instrument_count: 1, total_amount: '1000000.00' },
  ],
  grand_total_instruments: 7,
  grand_total_amount: '8000000.00',
  disclaimer: 'Deterministic calendar aggregation based strictly on recorded instrument maturity dates. Not a forecast or projection.',
};

const mockPriorityQueue: PriorityQueueResponse = {
  metric_id: 'MTR-PRIORITY-QUEUE',
  total_count: 1,
  page: 1,
  page_size: 50,
  weights_applied: { urgency: 0.35, discrepancy: 0.25, trust: 0.20, overdue: 0.20 },
  items: [
    {
      instrument_id: 'inst-1',
      reference_number: 'FDR-SBI-2026-001',
      institution_id: 'inst-alpha',
      institution_name: 'Alpha Engineering College',
      bank_name: 'State Bank of India',
      amount: '1000000.00',
      maturity_date: '2026-11-20',
      days_to_maturity: 26,
      status: 'REGISTERED',
      trust_level: 'L2_OFFICER_VERIFIED',
      priority_score: 82.5,
      urgency_factor: 75.0,
      discrepancy_factor: 50.0,
      trust_factor: 25.0,
      overdue_factor: 100.0,
    },
  ],
};

describe('Command Center Components & Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders StatusOverviewCards with real counts and definitions', () => {
    const handleDict = vi.fn();
    render(
      <BrowserRouter>
        <StatusOverviewCards
          data={mockStatusCounts}
          isLoading={false}
          onOpenDictionary={handleDict}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('Active Instruments')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('Expiring Soon')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Matured Instruments')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Renewed / Replaced')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Released Deposits')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('renders MaturityWindowSection with statutory warning and table items', () => {
    const handleWindowChange = vi.fn();
    render(
      <BrowserRouter>
        <MaturityWindowSection
          data={mockMaturityWindow}
          isLoading={false}
          selectedWindowDays={90}
          onWindowChange={handleWindowChange}
        />
      </BrowserRouter>
    );

    // Warning guard presence
    expect(screen.getByText(/Statutory Compliance Guard/i)).toBeInTheDocument();
    expect(screen.getByText(/Statutory Compliance Guard/i).closest('div')).toHaveTextContent(
      /does not constitute proof of release or refund eligibility/i
    );

    // Table data
    expect(screen.getByText('FDR-SBI-2026-001')).toBeInTheDocument();
    expect(screen.getByText('Alpha Engineering College')).toBeInTheDocument();
    expect(screen.getByText(/In 26 days/i)).toBeInTheDocument();
    expect(screen.getByText('L2 Verified')).toBeInTheDocument();
  });

  it('renders OverdueEscalatedQueue with escalation state and office', () => {
    render(
      <BrowserRouter>
        <OverdueEscalatedQueue
          data={mockOverdueEscalated}
          isLoading={false}
          isInstitutionUser={false}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('FDR-OVERDUE-01')).toBeInTheDocument();
    expect(screen.getByText('+15 days')).toBeInTheDocument();
    expect(screen.getByText(/Escalated \(BRANCH_HEAD\)/i)).toBeInTheDocument();
    expect(screen.getByText('Scrutiny Officer')).toBeInTheDocument();
  });

  it('renders VerificationQueueWidget and visibly labels SIMULATED adapter channel', () => {
    render(
      <BrowserRouter>
        <VerificationQueueWidget
          data={mockVerificationQueue}
          isLoading={false}
        />
      </BrowserRouter>
    );

    expect(screen.getByText('VR-2026-001')).toBeInTheDocument();
    // Check for prominent SIMULATED badge
    const simBadges = screen.getAllByText('SIMULATED');
    expect(simBadges.length).toBeGreaterThan(0);
    const highlightedBadge = simBadges.find((b) => b.classList.contains('bg-amber-100'));
    expect(highlightedBadge).toBeDefined();
    expect(highlightedBadge).toHaveClass('bg-amber-100');

    // Source unavailable item
    expect(screen.getByText('Source Unavailable')).toBeInTheDocument();
  });

  it('renders CompletenessBlockersWidget with unconfigured policy warning and release blockers', () => {
    render(
      <BrowserRouter>
        <CompletenessBlockersWidget
          completeness={mockCompleteness}
          blockers={mockReleaseBlockers}
          isLoading={false}
        />
      </BrowserRouter>
    );

    // Policy unconfigured alert
    expect(screen.getByText('POLICY UNCONFIGURED')).toBeInTheDocument();
    expect(screen.getByText(/Policy Configuration Notice/i)).toBeInTheDocument();

    // Release blockers
    expect(screen.getByText('REL-2026-0001')).toBeInTheDocument();
    expect(screen.getByText('1 Blocker')).toBeInTheDocument();
  });

  it('renders MaturityLoadChart with chart bars and switches to accessible table', () => {
    render(
      <MaturityLoadChart
        data={mockMaturityLoad}
        isLoading={false}
        selectedYear={2026}
      />
    );

    // Disclaimer
    expect(screen.getByText(/Accounting Transparency Notice/i)).toBeInTheDocument();
    expect(screen.getByText(/Not a forecast or projection/i)).toBeInTheDocument();

    // Switch to table
    const tableBtn = screen.getByRole('button', { name: /Accessible table view/i });
    fireEvent.click(tableBtn);

    expect(screen.getByRole('table', { name: /Month-wise maturity table/i })).toBeInTheDocument();
    expect(screen.getByText(/Nov 2026/i)).toBeInTheDocument();
  });

  it('renders PriorityQueueDesk with score, contributing factors and weight assumptions', () => {
    const handleScoreChange = vi.fn();
    render(
      <BrowserRouter>
        <PriorityQueueDesk
          data={mockPriorityQueue}
          isLoading={false}
          minScore={0}
          onMinScoreChange={handleScoreChange}
        />
      </BrowserRouter>
    );

    // Workflow score disclaimer
    expect(screen.getByText(/Methodological Clarification/i).closest('div')).toHaveTextContent(
      /operational workflow-priority score to guide scrutiny triage/i
    );
    expect(screen.getByText(/Methodological Clarification/i).closest('div')).toHaveTextContent(
      /NOT a fraud probability/i
    );

    // Item score & factors
    expect(screen.getByText('82.5 / 100')).toBeInTheDocument();
    expect(screen.getByText(/Urg:/i)).toBeInTheDocument();
    expect(screen.getByText(/Disc:/i)).toBeInTheDocument();

    // Toggle weights
    const weightsBtn = screen.getByRole('button', { name: /Weights & Assumptions/i });
    fireEvent.click(weightsBtn);

    expect(screen.getByText(/35% Weight/i)).toBeInTheDocument();
    expect(screen.getByText(/25% Weight/i)).toBeInTheDocument();
  });

  it('renders full CommandCenterPage and integrates real API calls', async () => {
    vi.spyOn(commandCenterApi, 'getStatusCounts').mockResolvedValue(mockStatusCounts);
    vi.spyOn(commandCenterApi, 'getMaturityWindow').mockResolvedValue(mockMaturityWindow);
    vi.spyOn(commandCenterApi, 'getOverdueEscalated').mockResolvedValue(mockOverdueEscalated);
    vi.spyOn(commandCenterApi, 'getVerificationQueue').mockResolvedValue(mockVerificationQueue);
    vi.spyOn(commandCenterApi, 'getDocumentCompleteness').mockResolvedValue(mockCompleteness);
    vi.spyOn(commandCenterApi, 'getReleaseBlockers').mockResolvedValue(mockReleaseBlockers);
    vi.spyOn(commandCenterApi, 'getMaturityLoad').mockResolvedValue(mockMaturityLoad);
    vi.spyOn(commandCenterApi, 'getPriorityQueue').mockResolvedValue(mockPriorityQueue);

    render(
      <MemoryRouter initialEntries={['/command-center?window_days=90']}>
        <CommandCenterPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Security Deposit & FDR Command Center/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Active Instruments')).toBeInTheDocument();
      expect(screen.getByText('15')).toBeInTheDocument();
      expect(screen.getAllByText('FDR-SBI-2026-001').length).toBeGreaterThan(0);
    });
  });
});
