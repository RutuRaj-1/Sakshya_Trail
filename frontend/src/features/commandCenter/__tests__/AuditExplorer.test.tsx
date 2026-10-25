import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { AuditPage } from '@/app/routes/AuditPage';
import { auditApi } from '@/api/endpoints';

// Mock auth context
vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'usr-auditor-1',
      email: 'auditor@audit.gov.in',
      role: 'AUDITOR',
      full_name: 'Lead Compliance Auditor',
    },
    isAuthenticated: true,
  }),
}));

const mockEventsList = {
  items: [
    {
      id: 'ev-1111-aaaa',
      sequence_number: 1,
      created_at: '2026-10-25T10:00:00Z',
      action: 'SYSTEM_BOOTSTRAP_CHAIN_INIT',
      entity_type: 'SYSTEM',
      entity_id: 'sentinel_bootstrap',
      actor_user_id: 'usr-admin-1',
      actor_email: 'admin@sentinel.gov.in',
      actor_role: 'SYSTEM_ADMIN',
      outcome: 'SUCCESS',
      request_id: 'req-001',
      policy_version: 'v1.0.0',
      metadata: { status: 'CHAIN_ACTIVE' },
      previous_hash: '0000000000000000000000000000000000000000000000000000000000000000',
      current_hash: '86cd8157c91e8c5c79f969b0eaeac74d5e9a084836adb2e598107caff065c233',
    },
    {
      id: 'ev-2222-bbbb',
      sequence_number: 2,
      created_at: '2026-10-25T11:00:00Z',
      action: 'INSTRUMENT_CREATED',
      entity_type: 'INSTRUMENT',
      entity_id: 'inst-9999-uuid',
      actor_user_id: 'usr-officer-1',
      actor_email: 'officer@aicte.gov.in',
      actor_role: 'SCRUTINY_OFFICER',
      outcome: 'SUCCESS',
      request_id: 'req-002',
      policy_version: 'v1.0.0',
      metadata: { deposit_amount: '500000.00', bank_name: 'State Bank of India' },
      previous_hash: '86cd8157c91e8c5c79f969b0eaeac74d5e9a084836adb2e598107caff065c233',
      current_hash: '9d7b53a42ed7c51efc662359d16c2eb18807b6e92707757aaba1f42712b17cf0',
    },
    {
      id: 'ev-3333-cccc',
      sequence_number: 3,
      created_at: '2026-10-25T12:00:00Z',
      action: 'UNAUTHORIZED_CROSS_TENANT_DASHBOARD_ACCESS',
      entity_type: 'INSTITUTION',
      entity_id: 'inst-other-tenant',
      actor_user_id: 'usr-inst-1',
      actor_email: 'nodal@diet-delhi.ac.in',
      actor_role: 'INSTITUTION_USER',
      outcome: 'DENIED',
      request_id: 'req-003',
      policy_version: 'v1.0.0',
      metadata: { attempted_tenant: 'inst-b' },
      previous_hash: '9d7b53a42ed7c51efc662359d16c2eb18807b6e92707757aaba1f42712b17cf0',
      current_hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
    },
  ],
  total: 3,
  skip: 0,
  limit: 20,
  has_more: false,
};

describe('AuditExplorer Component (Module 7 — Prompt 5)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(auditApi, 'list').mockResolvedValue(mockEventsList);
  });

  it('renders the Audit Explorer with header and cryptographic explanation', async () => {
    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Tamper-Evident Audit Explorer/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Cryptographically chained SHA-256 regulatory ledger/i)
    ).toBeInTheDocument();
  });

  it('displays sequence numbers, outcome badges, and truncated hashes', async () => {
    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument();
      expect(screen.getByText('#2')).toBeInTheDocument();
      expect(screen.getByText('#3')).toBeInTheDocument();
      expect(screen.getByText('DENIED')).toBeInTheDocument();
      expect(screen.getAllByText('SUCCESS').length).toBeGreaterThanOrEqual(2);
    });
  });

  it('invokes verifyChain when "Verify Audit Chain" button is clicked and renders PASS banner', async () => {
    vi.spyOn(auditApi, 'verifyChain').mockResolvedValue({
      status: 'PASS',
      is_chain_intact: true,
      total_events_in_scope: 3,
      verified_count: 3,
      latest_sequence_number: 3,
      chain_head_hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
      first_inconsistency: null,
      verification_timestamp: '2026-10-25T12:05:00Z',
      verification_scope_description: 'Full audit sequence (Blocks #1 to #3) verified intact.',
    });

    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    );

    const verifyButton = screen.getByRole('button', { name: /Verify Audit Chain/i });
    expect(verifyButton).toBeInTheDocument();

    fireEvent.click(verifyButton);

    await waitFor(() => {
      expect(auditApi.verifyChain).toHaveBeenCalledTimes(1);
      expect(
        screen.getByText(/Audit Ledger Integrity Verified \(PASS\)/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Full audit sequence \(Blocks #1 to #3\) verified intact/i)
      ).toBeInTheDocument();
    });
  });

  it('displays tamper detection diagnosis and forensic details when chain verification fails', async () => {
    vi.spyOn(auditApi, 'verifyChain').mockResolvedValue({
      status: 'TAMPER_DETECTED',
      is_chain_intact: false,
      total_events_in_scope: 3,
      verified_count: 1,
      latest_sequence_number: 1,
      chain_head_hash: '86cd8157c91e8c5c79f969b0eaeac74d5e9a084836adb2e598107caff065c233',
      first_inconsistency: {
        sequence_number: 2,
        event_id: 'ev-2222-bbbb',
        failure_type: 'PAYLOAD_TAMPERED',
        expected_hash: 'expected-canonical-digest',
        actual_hash: 'tampered-actual-digest',
        safe_explanation:
          'Payload modification detected at sequence #2: recorded current_hash does not match canonical payload digest.',
      },
      verification_timestamp: '2026-10-25T12:05:00Z',
      verification_scope_description: 'Verification failed at sequence #2.',
    });

    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    );

    const verifyButton = screen.getByRole('button', { name: /Verify Audit Chain/i });
    fireEvent.click(verifyButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Cryptographic Chain Integrity Inconsistency Detected/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/PAYLOAD_TAMPERED/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Earliest Detected Inconsistency at Sequence #2/i)
      ).toBeInTheDocument();
    });
  });

  it('opens Inspect Modal with full cryptographic proof and metadata when "Inspect" is clicked', async () => {
    render(
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Inspect/i }).length).toBe(3);
    });

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[1]); // Inspect second event

    await waitFor(() => {
      expect(screen.getByText(/Audit Event Payload #2/i)).toBeInTheDocument();
      expect(screen.getByText(/Cryptographic Proof & SHA-256 Linkage/i)).toBeInTheDocument();
      expect(screen.getByText(/Current Canonical Payload Hash/i)).toBeInTheDocument();
      expect(screen.getByText(/deposit_amount/i)).toBeInTheDocument();
      expect(screen.getByText(/State Bank of India/i)).toBeInTheDocument();
    });

    // Close modal
    const closeButton = screen.getByRole('button', { name: /Close/i });
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText(/Audit Event Payload #2/i)).not.toBeInTheDocument();
    });
  });
});
