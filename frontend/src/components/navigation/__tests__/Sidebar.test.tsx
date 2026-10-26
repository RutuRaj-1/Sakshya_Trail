import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';

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

describe('Sidebar Component Navigation & IA', () => {
  beforeEach(() => {
    localStorage.clear();
    mockRole = 'SCRUTINY_OFFICER';
  });

  it('renders all 4 major navigation groups', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByText('FDR Lifecycle')).toBeInTheDocument();
    expect(screen.getByText('Intelligence & Oversight')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('renders Core Workspace items Overview and Command Center', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Command Center')).toBeInTheDocument();
  });

  it('renders FDR Lifecycle module links with active badge counts', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Institutions & Instruments')).toBeInTheDocument();
    expect(screen.getByText('Documents & Evidence')).toBeInTheDocument();
    expect(screen.getByText('Validation & Review Queue')).toBeInTheDocument();
    expect(screen.getByText('Trust & Verification')).toBeInTheDocument();
    expect(screen.getByText('Monitoring & Renewals')).toBeInTheDocument();
    expect(screen.getByText('Release / Refund Cases')).toBeInTheDocument();

    // Verify badges
    expect(screen.getByText('7')).toBeInTheDocument(); // review queue badge
    expect(screen.getByText('3')).toBeInTheDocument(); // verification queue badge
    expect(screen.getByText('2')).toBeInTheDocument(); // release cases badge
  });

  it('collapses and expands a navigation group when toggle header is clicked', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Initial state: 'Overview' is visible
    expect(screen.getByText('Overview')).toBeInTheDocument();

    // Click on 'Workspace' header button to collapse
    const workspaceHeader = screen.getByText('Workspace').closest('button');
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

    // Allowed for institution:
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Institutions & Instruments')).toBeInTheDocument();
    expect(screen.getByText('Documents & Evidence')).toBeInTheDocument();
    expect(screen.getByText('Monitoring & Renewals')).toBeInTheDocument();
    expect(screen.getByText('Release / Refund Cases')).toBeInTheDocument();

    // Restricted regulatory items must NOT be rendered for INSTITUTION_USER:
    expect(screen.queryByText('Command Center')).not.toBeInTheDocument();
    expect(screen.queryByText('Validation & Review Queue')).not.toBeInTheDocument();
    expect(screen.queryByText('Trust & Verification')).not.toBeInTheDocument();
    expect(screen.queryByText('Operational Reports')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit & Integrity')).not.toBeInTheDocument();
    expect(screen.queryByText('System Users')).not.toBeInTheDocument();
  });

  it('renders Command Center and supervisory groups for BRANCH_HEAD', () => {
    mockRole = 'BRANCH_HEAD';

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Command Center')).toBeInTheDocument();
    expect(screen.getByText('Validation & Review Queue')).toBeInTheDocument();
    expect(screen.getByText('Trust & Verification')).toBeInTheDocument();
    expect(screen.getByText('Operational Reports')).toBeInTheDocument();
    // System Users is strictly SYSTEM_ADMIN only
    expect(screen.queryByText('System Users')).not.toBeInTheDocument();
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
