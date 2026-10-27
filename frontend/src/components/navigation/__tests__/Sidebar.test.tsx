import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar, NAV_GROUPS } from '../Sidebar';
import { CANONICAL_FDR_STAGES } from '@/features/lifecycle/stageMapping';

// Variable to control mock user role
let mockRole = 'SCRUTINY_OFFICER';

vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'test@aicte.gov.in',
      role: mockRole,
      full_name: 'Test Officer',
    },
    isAuthenticated: true,
  }),
}));

vi.mock('@/hooks/useNavBadges', () => ({
  useNavBadges: () => ({
    reviewQueueCount: 7,
    verificationQueueCount: 3,
    releaseCasesCount: 2,
  }),
}));

describe('Sidebar Component Navigation & IA (Prompt 3)', () => {
  beforeEach(() => {
    localStorage.clear();
    mockRole = 'SCRUTINY_OFFICER';
  });

  it('renders all three primary experiences and supporting navigation in correct order', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Verify groups exist
    expect(screen.getByText('FDR Workflow')).toBeInTheDocument();
    expect(screen.getByText('Lifecycle & Monitoring')).toBeInTheDocument();
    expect(screen.getByText('My Workspace')).toBeInTheDocument();
    expect(screen.getByText('Supporting Capabilities')).toBeInTheDocument();

    // Verify exact order of the navigation groups
    expect(NAV_GROUPS[0].id).toBe('fdr-workflow');
    expect(NAV_GROUPS[0].title).toBe('FDR Workflow');

    expect(NAV_GROUPS[1].id).toBe('lifecycle-monitoring');
    expect(NAV_GROUPS[1].title).toBe('Lifecycle & Monitoring');

    expect(NAV_GROUPS[2].id).toBe('workspace');
    expect(NAV_GROUPS[2].title).toBe('My Workspace');

    expect(NAV_GROUPS[3].id).toBe('supporting-capabilities');
    expect(NAV_GROUPS[3].title).toBe('Supporting Capabilities');
  });

  it('renders all nine canonical FDR workflow stages in exact order', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    const workflowGroup = NAV_GROUPS.find((g) => g.id === 'fdr-workflow');
    expect(workflowGroup).toBeDefined();
    expect(workflowGroup?.items).toHaveLength(9);

    const expectedCanonicalStages = [
      'FDR Submission & Registration',
      'Document Upload & Evidence',
      'Validation & Discrepancy Detection',
      'Scrutiny & Review',
      'Bank Verification & Trust',
      'Lifecycle Monitoring',
      'Renewal & Successor Lineage',
      'Release Readiness',
      'Maker-Checker Decision & Closure',
    ];

    expectedCanonicalStages.forEach((stageName, idx) => {
      expect(workflowGroup?.items[idx].name).toBe(stageName);
      expect(screen.getByText(stageName)).toBeInTheDocument();
    });

    // Also verify centralized CANONICAL_FDR_STAGES mapping exact match
    CANONICAL_FDR_STAGES.forEach((stage, idx) => {
      expect(stage.label).toBe(expectedCanonicalStages[idx]);
    });
  });

  it('resolves every stage link to an implemented route or valid view', () => {
    const workflowGroup = NAV_GROUPS.find((g) => g.id === 'fdr-workflow');
    expect(workflowGroup).toBeDefined();

    const expectedRoutes = [
      '/instruments',
      '/documents',
      '/findings/queue?status=OPEN',
      '/findings/queue?status=IN_REVIEW',
      '/verification',
      '/monitoring',
      '/monitoring?tab=renewals',
      '/release?status=UNDER_REVIEW',
      '/release?status=READY_FOR_AUTHORITY',
    ];

    expectedRoutes.forEach((route, idx) => {
      expect(workflowGroup?.items[idx].to).toBe(route);
    });
  });

  it('renders all 7 Lifecycle & Monitoring destinations', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Portfolio Overview')).toBeInTheDocument();
    expect(screen.getByText('Maturity Calendar')).toBeInTheDocument();
    expect(screen.getByText('Approaching & Overdue')).toBeInTheDocument();
    expect(screen.getByText('Renewal Queue')).toBeInTheDocument();
    expect(screen.getByText('Predecessor–Successor Lineage')).toBeInTheDocument();
    expect(screen.getByText('Lifecycle Exceptions & Alerts')).toBeInTheDocument();
    expect(screen.getByText('Policies & Scheduler')).toBeInTheDocument();
  });

  it('renders My Workspace items Overview and Command Center', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Command Center')).toBeInTheDocument();
  });

  it('renders Supporting Capabilities destinations', () => {
    mockRole = 'SYSTEM_ADMIN';
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Unified Search')).toBeInTheDocument();
    expect(screen.getByText('Operational Reports')).toBeInTheDocument();
    expect(screen.getByText('Audit & Integrity')).toBeInTheDocument();
    expect(screen.getByText('Institution Directory')).toBeInTheDocument();
    expect(screen.getByText('Password Security')).toBeInTheDocument();
    expect(screen.getByText('System Diagnostics')).toBeInTheDocument();
  });

  it('renders live count badges for review queue, verification desk, and release cases', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('7')).toBeInTheDocument(); // reviewQueueCount on Stage 3
    expect(screen.getByText('3')).toBeInTheDocument(); // verificationQueueCount on Stage 5
    expect(screen.getByText('2')).toBeInTheDocument(); // releaseCasesCount on Stage 8
  });

  it('collapses and expands a navigation group when toggle header is clicked', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Initial state: 'Overview' is visible
    expect(screen.getByText('Overview')).toBeInTheDocument();

    // Click on 'My Workspace' header button to collapse
    const workspaceHeader = screen.getByText('My Workspace').closest('button');
    expect(workspaceHeader).toBeTruthy();
    fireEvent.click(workspaceHeader!);

    // Overview should now be hidden
    expect(screen.queryByText('Overview')).not.toBeInTheDocument();

    // Click again to expand
    fireEvent.click(workspaceHeader!);
    expect(screen.getByText('Overview')).toBeInTheDocument();
  });

  it('enforces RBAC item isolation for INSTITUTION_USER', () => {
    mockRole = 'INSTITUTION_USER';

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Permitted workflow stages for institution:
    expect(screen.getByText('FDR Submission & Registration')).toBeInTheDocument();
    expect(screen.getByText('Document Upload & Evidence')).toBeInTheDocument();
    expect(screen.getByText('Lifecycle Monitoring')).toBeInTheDocument();
    expect(screen.getByText('Renewal & Successor Lineage')).toBeInTheDocument();
    expect(screen.getByText('Release Readiness')).toBeInTheDocument();
    expect(screen.getByText('Maker-Checker Decision & Closure')).toBeInTheDocument();

    // Permitted lifecycle monitoring destinations:
    expect(screen.getByText('Portfolio Overview')).toBeInTheDocument();
    expect(screen.getByText('Maturity Calendar')).toBeInTheDocument();
    expect(screen.getByText('Approaching & Overdue')).toBeInTheDocument();
    expect(screen.getByText('Renewal Queue')).toBeInTheDocument();
    expect(screen.getByText('Predecessor–Successor Lineage')).toBeInTheDocument();
    expect(screen.getByText('Lifecycle Exceptions & Alerts')).toBeInTheDocument();

    // Permitted workspace and supporting:
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Unified Search')).toBeInTheDocument();
    expect(screen.getByText('Password Security')).toBeInTheDocument();

    // STRICTLY HIDDEN for INSTITUTION_USER:
    expect(screen.queryByText('Validation & Discrepancy Detection')).not.toBeInTheDocument();
    expect(screen.queryByText('Scrutiny & Review')).not.toBeInTheDocument();
    expect(screen.queryByText('Bank Verification & Trust')).not.toBeInTheDocument();
    expect(screen.queryByText('Command Center')).not.toBeInTheDocument();
    expect(screen.queryByText('Operational Reports')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit & Integrity')).not.toBeInTheDocument();
    expect(screen.queryByText('Institution Directory')).not.toBeInTheDocument();
    expect(screen.queryByText('Users & Access')).not.toBeInTheDocument();
    expect(screen.queryByText('System Diagnostics')).not.toBeInTheDocument();
    expect(screen.queryByText('Policies & Scheduler')).not.toBeInTheDocument();
  });

  it('enforces RBAC item visibility for SYSTEM_ADMIN', () => {
    mockRole = 'SYSTEM_ADMIN';

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Admin has access to all groups and items including Users & Access
    expect(screen.getByText('Users & Access')).toBeInTheDocument();
    expect(screen.getByText('Policies & Scheduler')).toBeInTheDocument();
    expect(screen.getByText('Command Center')).toBeInTheDocument();
    expect(screen.getByText('Audit & Integrity')).toBeInTheDocument();
  });

  it('enforces read-only oversight navigation for AUDITOR', () => {
    mockRole = 'AUDITOR';

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Auditor can view audit, reports, diagnostics, and workflow verification queues
    expect(screen.getByText('Audit & Integrity')).toBeInTheDocument();
    expect(screen.getByText('Operational Reports')).toBeInTheDocument();
    expect(screen.getByText('System Diagnostics')).toBeInTheDocument();
    expect(screen.getByText('Bank Verification & Trust')).toBeInTheDocument();

    // But Auditor does NOT have administrative user management or policies scheduler
    expect(screen.queryByText('Users & Access')).not.toBeInTheDocument();
    expect(screen.queryByText('Policies & Scheduler')).not.toBeInTheDocument();
    expect(screen.queryByText('Command Center')).not.toBeInTheDocument();
  });

  it('renders mobile close button when onCloseMobile is provided', () => {
    const handleCloseMobile = vi.fn();

    render(
      <MemoryRouter>
        <Sidebar onCloseMobile={handleCloseMobile} />
      </MemoryRouter>
    );

    const closeBtn = screen.getByLabelText(/close sidebar/i);
    expect(closeBtn).toBeInTheDocument();

    fireEvent.click(closeBtn);
    expect(handleCloseMobile).toHaveBeenCalledTimes(1);
  });
});
