import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
import { DashboardPage } from '@/app/routes/DashboardPage';
import { NineStageLifecycleTracker } from '@/features/lifecycle/components/NineStageLifecycleTracker';
import type { ApplicationRole, Instrument } from '@/types';

// Mock AuthContext
let mockUser: { id: string; name: string; email: string; role: ApplicationRole; institution_id?: string } | null = null;
let mockIsLoading = false;

vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: mockIsLoading,
    isAuthenticated: !!mockUser,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

// Mock APIs called by workspaces to avoid network calls
vi.mock('@/api/endpoints', () => ({
  instrumentsApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getSummary: vi.fn().mockResolvedValue({ total_instruments: 0 }),
  },
  dashboardApi: {
    getSummary: vi.fn().mockResolvedValue({
      total_instruments: 10,
      active_instruments: 8,
      matured_instruments: 2,
      total_deposit_amount: 5000000,
      documents_count: 15,
      pending_verifications_count: 1,
      total_users: 5,
    }),
  },
  lifecycleApi: {
    getUserInbox: vi.fn().mockResolvedValue({ notifications: [] }),
    listFailedNotifications: vi.fn().mockResolvedValue([]),
  },
  findingsApi: {
    getQueue: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
  usersApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
  institutionsApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
  healthApi: {
    getLiveness: vi.fn().mockResolvedValue({ status: 'HEALTHY' }),
    getReadiness: vi.fn().mockResolvedValue({ status: 'READY', components: { database: { status: 'CONNECTED' } } }),
  },
  auditApi: {
    verifyChain: vi.fn().mockResolvedValue({ is_valid: true, total_events_checked: 100 }),
    listEvents: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

vi.mock('@/api/commandCenter', () => ({
  commandCenterApi: {
    getPriorityQueue: vi.fn().mockResolvedValue({ items: [], total_count: 0 }),
    getDocumentCompleteness: vi.fn().mockResolvedValue({ missing_count: 0 }),
    getVerificationQueue: vi.fn().mockResolvedValue({ total_outstanding: 0 }),
    getOverdueEscalations: vi.fn().mockResolvedValue({ records: [], total_overdue: 0 }),
    getMaturityWindow: vi.fn().mockResolvedValue({ total_deposit_value: 0, buckets: [] }),
    getReleaseBlockers: vi.fn().mockResolvedValue({ blocked_requests_count: 0 }),
  },
}));

vi.mock('@/api/release', () => ({
  releaseApi: {
    list: vi.fn().mockResolvedValue([]),
    getReleaseBlockers: vi.fn().mockResolvedValue({ blockers: [] }),
  },
}));

describe('Prompt 2 — Role-Specific Navigation, Direct Route Guards & Workspaces', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Direct Route Access Protection', () => {
    it('blocks direct navigation to /users for unauthorized INSTITUTION_USER', () => {
      mockUser = {
        id: 'user-inst-1',
        name: 'College Principal',
        email: 'principal@college.edu',
        role: 'INSTITUTION_USER',
      };

      render(
        <MemoryRouter initialEntries={['/users']}>
          <Routes>
            <Route
              path="/users"
              element={
                <ProtectedRoute allowedRoles={['SYSTEM_ADMIN']}>
                  <div>Protected Users Management Page</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.queryByText('Protected Users Management Page')).not.toBeInTheDocument();
      expect(screen.getByText('Access Restricted')).toBeInTheDocument();
      expect(screen.getByText(/is not authorized to access this module/i)).toBeInTheDocument();
    });

    it('blocks direct navigation to /audit for unauthorized FINANCE_OFFICER', () => {
      mockUser = {
        id: 'user-fin-1',
        name: 'Finance Desk',
        email: 'finance@aicte.gov.in',
        role: 'FINANCE_OFFICER',
      };

      render(
        <MemoryRouter initialEntries={['/audit']}>
          <Routes>
            <Route
              path="/audit"
              element={
                <ProtectedRoute allowedRoles={['SYSTEM_ADMIN', 'AUDITOR', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY']}>
                  <div>Protected Audit Ledger Page</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.queryByText('Protected Audit Ledger Page')).not.toBeInTheDocument();
      expect(screen.getByText('Access Restricted')).toBeInTheDocument();
      expect(screen.getByText(/is not authorized to access this module/i)).toBeInTheDocument();
    });

    it('allows direct navigation to /audit for authorized AUDITOR', () => {
      mockUser = {
        id: 'user-aud-1',
        name: 'External Auditor',
        email: 'auditor@cag.gov.in',
        role: 'AUDITOR',
      };

      render(
        <MemoryRouter initialEntries={['/audit']}>
          <Routes>
            <Route
              path="/audit"
              element={
                <ProtectedRoute allowedRoles={['SYSTEM_ADMIN', 'AUDITOR', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY']}>
                  <div>Protected Audit Ledger Page</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Protected Audit Ledger Page')).toBeInTheDocument();
      expect(screen.queryByText('Access Restricted')).not.toBeInTheDocument();
    });
  });

  describe('Role-Specific Dashboard Workspaces', () => {
    it('renders Institution Workspace for INSTITUTION_USER', async () => {
      mockUser = {
        id: 'inst-1',
        name: 'Delhi Tech College',
        email: 'admin@dtc.edu.in',
        role: 'INSTITUTION_USER',
        institution_id: 'INST-001',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Institutional FDR Portfolio Vault/i)).toBeInTheDocument();
      expect(screen.getByText(/Manage your institution's security deposit receipts/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Register FDR/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Upload Evidence/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Release Petition/i })).toBeInTheDocument();
      // Should NOT have administrative or bureau-wide management controls
      expect(screen.queryByText('System Health Operations')).not.toBeInTheDocument();
      expect(screen.queryByText('Regional Workload & Reassignment')).not.toBeInTheDocument();
    });

    it('renders Scrutiny Officer Workspace for SCRUTINY_OFFICER', async () => {
      mockUser = {
        id: 'scrutiny-1',
        name: 'Officer Rajesh',
        email: 'rajesh@aicte.gov.in',
        role: 'SCRUTINY_OFFICER',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Scrutiny & Regulatory Examination Desk/i)).toBeInTheDocument();
      expect(screen.getByText(/Priority Validation Findings Queue/i)).toBeInTheDocument();
      expect(screen.getByText(/Release Case Reviews/i)).toBeInTheDocument();
      expect(screen.getByText('Open Review Queue')).toBeInTheDocument();
      // Scrutiny officer must NOT see final sanction buttons
      expect(screen.queryByText('Sanction / Reject Release Petitions')).not.toBeInTheDocument();
    });

    it('renders Branch Head Workspace for BRANCH_HEAD', async () => {
      mockUser = {
        id: 'head-1',
        name: 'Regional Director',
        email: 'director.nr@aicte.gov.in',
        role: 'BRANCH_HEAD',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Branch Executive Portfolio & Escalation Center/i)).toBeInTheDocument();
      expect(screen.getByText(/Overdue Reviews & Escalations/i)).toBeInTheDocument();
      expect(screen.getByText(/Command Center/i)).toBeInTheDocument();
    });

    it('renders Competent Authority Workspace for COMPETENT_AUTHORITY', async () => {
      mockUser = {
        id: 'auth-1',
        name: 'Member Secretary',
        email: 'member.sec@aicte.gov.in',
        role: 'COMPETENT_AUTHORITY',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Competent Authority Release & Discharge Sanction Desk/i)).toBeInTheDocument();
      expect(screen.getByText(/Maker-Checker Statutory Protocol/i)).toBeInTheDocument();
      expect(screen.getByText(/Petitions Awaiting Sanction Decision/i)).toBeInTheDocument();
      // Must NOT allow AI to become final decision or show user provisioning
      expect(screen.queryByText('User and Role Administration')).not.toBeInTheDocument();
    });

    it('renders Finance Officer Workspace for FINANCE_OFFICER', async () => {
      mockUser = {
        id: 'fin-1',
        name: 'Finance Desk Officer',
        email: 'finance.officer@aicte.gov.in',
        role: 'FINANCE_OFFICER',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Financial Operations & Release Order Execution Desk/i)).toBeInTheDocument();
      expect(screen.getByText(/Awaiting Order Letter/i)).toBeInTheDocument();
      expect(screen.getByText(/Pending Bank Action/i)).toBeInTheDocument();
      expect(screen.getByText(/Financial Actions Queue/i)).toBeInTheDocument();
      // Must NOT show regulatory approval controls
      expect(screen.queryByText('Sanction / Reject Release Petitions')).not.toBeInTheDocument();
    });

    it('renders Auditor Workspace for AUDITOR', async () => {
      mockUser = {
        id: 'aud-1',
        name: 'Chief Audit Officer',
        email: 'audit.lead@cag.gov.in',
        role: 'AUDITOR',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Cryptographic Audit & Compliance Verification Cockpit/i)).toBeInTheDocument();
      expect(screen.getByText(/Auditor Read-Only Invariant/i)).toBeInTheDocument();
      expect(screen.getByText('Verify Audit Chain')).toBeInTheDocument();
      expect(screen.getByText(/Chain Integrity/i)).toBeInTheDocument();
      // Must have zero business mutation controls
      expect(screen.queryByText('Submit New FDR')).not.toBeInTheDocument();
      expect(screen.queryByText('Initiate Release Petition')).not.toBeInTheDocument();
    });

    it('renders System Admin Workspace for SYSTEM_ADMIN', async () => {
      mockUser = {
        id: 'admin-1',
        name: 'Root Administrator',
        email: 'sysadmin@aicte.gov.in',
        role: 'SYSTEM_ADMIN',
      };

      render(
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      );

      expect(await screen.findByText(/Platform Governance & Security Administration/i)).toBeInTheDocument();
      expect(screen.getByText('Provisioned Users')).toBeInTheDocument();
      expect(screen.getByText('Registered Institutions')).toBeInTheDocument();
      expect(screen.getByText(/Active User Accounts/i)).toBeInTheDocument();
    });
  });

  describe('Nine-Stage Lifecycle Tracker Role Awareness', () => {
    const mockInstrument: Instrument = {
      id: 'inst-test-12345678',
      instrument_type: 'FDR',
      reference_number: 'FDR-2026-999',
      institution_id: 'INST-001',
      bank_name: 'State Bank of India',
      branch: 'New Delhi Main',
      amount: 1000000,
      currency: 'INR',
      issue_date: '2025-01-01',
      maturity_date: '2028-01-01',
      maturity_indicator: 'ACTIVE',
      status: 'SUBMITTED',
      trust_level: 'L1_DOCUMENT_CONSISTENT',
      verification_level: 'L1_DOCUMENT_CONSISTENT',
      joint_with_aicte: true,
      lien_marked: true,
      is_synthetic: false,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    };

    it('renders role-tailored next action for SCRUTINY_OFFICER on submitted instrument', () => {
      render(
        <MemoryRouter>
          <NineStageLifecycleTracker
            mode="instrument"
            instrument={mockInstrument}
            role="SCRUTINY_OFFICER"
          />
        </MemoryRouter>
      );

      expect(screen.getByText(/Examine findings in queue & record observation/i)).toBeInTheDocument();
      expect(screen.getByText(/Statutory Guardrails:/i)).toBeInTheDocument();
    });

    it('renders role-tailored next action for INSTITUTION_USER on submitted instrument', () => {
      render(
        <MemoryRouter>
          <NineStageLifecycleTracker
            mode="instrument"
            instrument={mockInstrument}
            role="INSTITUTION_USER"
          />
        </MemoryRouter>
      );

      expect(screen.getByText(/Awaiting scrutiny officer validation outcome/i)).toBeInTheDocument();
    });

    it('renders read-only statutory oversight message for AUDITOR', () => {
      render(
        <MemoryRouter>
          <NineStageLifecycleTracker
            mode="instrument"
            instrument={mockInstrument}
            role="AUDITOR"
          />
        </MemoryRouter>
      );

      expect(screen.getByText(/Inspect scrutiny validation findings \(read-only\)/i)).toBeInTheDocument();
    });
  });
});
