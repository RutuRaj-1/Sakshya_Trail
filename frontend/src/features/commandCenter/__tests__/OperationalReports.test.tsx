import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { OperationalReportsWorkspace } from '../components/OperationalReportsWorkspace';
import { commandCenterApi } from '@/api/commandCenter';
import type {
  PendingVerificationReportResponse,
  UpcomingMaturitiesReportResponse,
  MissingDocumentsReportResponse,
  InterventionsReportResponse,
  AuditEvidencePackResponse,
} from '@/types/commandCenter';

// Mock Auth Context
let mockUserRole = 'SCRUTINY_OFFICER';

vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'usr-officer-1',
      email: 'officer@sentinel.gov.in',
      role: mockUserRole,
      full_name: 'Scrutiny Officer Sharma',
    },
    isAuthenticated: true,
  }),
}));

const mockPendingVerificationData: PendingVerificationReportResponse = {
  report_type: 'PENDING_VERIFICATION',
  generated_at: '2026-10-25T12:00:00Z',
  total_records: 2,
  filters_applied: {
    institution_id: null,
    bank_name: null,
    assigned_office: null,
    trust_level: null,
  },
  rows: [
    {
      instrument_id: 'inst-rep-001',
      reference_number: 'FDR-REP-01',
      institution_id: 'inst-a',
      institution_name: 'IIT Rep A',
      bank_name: 'State Bank of India',
      branch: 'Main Branch',
      verification_status: 'PENDING',
      source_status: 'SIMULATED_PENDING',
      trust_level: 'L1_DOCUMENT_CONSISTENT',
      channel: 'SIMULATED',
      is_simulated: true,
      request_date: '2026-10-01',
      pending_age_days: 24,
      assigned_office: 'Western Regional Office',
      assigned_officer: null,
      discrepancy_count: 1,
      drill_down_path: '/instruments/inst-rep-001',
    },
    {
      instrument_id: 'inst-rep-002',
      reference_number: 'FDR-REP-02',
      institution_id: 'inst-b',
      institution_name: 'NIT Rep B',
      bank_name: 'Punjab National Bank',
      branch: 'Connaught Place',
      verification_status: 'PENDING',
      source_status: 'LIVE_PENDING',
      trust_level: 'L2_OFFICER_VERIFIED',
      channel: 'SFMS_GATEWAY',
      is_simulated: false,
      request_date: '2026-10-15',
      pending_age_days: 10,
      assigned_office: 'Northern Regional Office',
      assigned_officer: null,
      discrepancy_count: 0,
      drill_down_path: '/instruments/inst-rep-002',
    },
  ],
};

const mockUpcomingMaturitiesData: UpcomingMaturitiesReportResponse = {
  report_type: 'UPCOMING_MATURITIES',
  date_basis: 'Asia/Kolkata Calendar Date',
  window_days: 90,
  date_from: '2026-10-25',
  date_to: '2027-01-23',
  generated_at: '2026-10-25T12:00:00Z',
  total_records: 1,
  total_deposit_value: '2500000.00',
  filters_applied: {
    institution_id: null,
    bank_name: null,
  },
  rows: [
    {
      instrument_id: 'inst-rep-003',
      reference_number: 'FDR-MAT-01',
      institution_id: 'inst-a',
      institution_name: 'IIT Rep A',
      bank_name: 'HDFC Bank',
      branch: 'Powai',
      amount: '2500000.00',
      currency: 'INR',
      issue_date: '2025-11-01',
      maturity_date: '2026-11-15',
      days_to_maturity: 21,
      administrative_status: 'ACTIVE',
      trust_level: 'L3_BANK_CONFIRMED',
      renewal_status: 'RENEWAL_LINKED',
      successor_instrument_id: 'inst-rep-004',
      assigned_office: 'Western Regional Office',
      assigned_officer: null,
      drill_down_path: '/instruments/inst-rep-003',
    },
  ],
};

const mockMissingDocumentsData: MissingDocumentsReportResponse = {
  report_type: 'MISSING_DOCUMENTS',
  generated_at: '2026-10-25T12:00:00Z',
  total_records: 1,
  filters_applied: {},
  rows: [
    {
      finding_id: 'find-doc-01',
      instrument_id: 'inst-rep-001',
      reference_number: 'FDR-REP-01',
      institution_id: 'inst-a',
      institution_name: 'IIT Rep A',
      bank_name: 'State Bank of India',
      rule_id: 'RULE-DOC-001',
      document_category: 'FDR_CERTIFICATE',
      policy_version: '1.0',
      checklist_outcome: 'MISSING',
      severity: 'HIGH',
      finding_title: 'Original physical FDR scan is missing',
      last_updated: '2026-10-20',
      drill_down_path: '/instruments/inst-rep-001',
    },
  ],
};

const mockInterventionsData: InterventionsReportResponse = {
  report_type: 'INTERVENTIONS',
  generated_at: '2026-10-25T12:00:00Z',
  total_records: 1,
  filters_applied: {},
  rows: [
    {
      intervention_type: 'OVERDUE_ESCALATION',
      entity_id: 'inst-rep-005',
      reference_number: 'FDR-OVERDUE-01',
      institution_id: 'inst-b',
      institution_name: 'NIT Rep B',
      reason_description: 'Statutory renewal overdue by 15 days (Condition: OVERDUE_15D)',
      severity: 'CRITICAL',
      age_days: 15,
      deadline_date: '2026-10-10',
      assigned_office: 'Northern Regional Office',
      assigned_officer: null,
      next_appropriate_action: 'Issue formal regulatory renewal demand and notify nodal officer',
      drill_down_path: '/instruments/inst-rep-005',
    },
  ],
};

const mockEvidencePackData: AuditEvidencePackResponse = {
  instrument_id: 'inst-rep-001',
  reference_number: 'FDR-REP-01',
  institution_id: 'inst-a',
  institution_name: 'IIT Rep A',
  bank_name: 'State Bank of India',
  amount: '1500000.00',
  trust_level: 'L1_DOCUMENT_CONSISTENT',
  status: 'ACTIVE',
  maturity_date: '2026-12-09',
  documents: [
    {
      version_number: 1,
      category: 'FDR_CERTIFICATE',
      file_name: 'scan_copy.pdf',
      sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      uploaded_at: '2026-10-01T10:00:00Z',
      uploader_name: 'Admin Test',
    },
  ],
  field_provenance_count: 5,
  verification_summary: {
    channel: 'SIMULATED',
    status: 'PENDING',
    is_simulated: true,
  },
  scrutiny_observations_count: 2,
  audit_events_count: 8,
  audit_chain_verified: true,
  chain_verification_status: 'VERIFIED_VALID',
  chain_verification_detail: 'Continuous cryptographic hash chain verified (8 blocks checked)',
  regulatory_disclaimer:
    'This operational evidence pack is an administrative compilation and does not constitute an independently certified forensic guarantee.',
  generated_at: '2026-10-25T12:00:00Z',
};

describe('Module 7 Prompt 4 — Operational Reports and Exports Frontend', () => {
  beforeEach(() => {
    mockUserRole = 'SCRUTINY_OFFICER';
    vi.restoreAllMocks();

    vi.spyOn(commandCenterApi, 'getPendingVerificationReport').mockResolvedValue(mockPendingVerificationData);
    vi.spyOn(commandCenterApi, 'getUpcomingMaturitiesReport').mockResolvedValue(mockUpcomingMaturitiesData);
    vi.spyOn(commandCenterApi, 'getMissingDocumentsReport').mockResolvedValue(mockMissingDocumentsData);
    vi.spyOn(commandCenterApi, 'getInterventionsReport').mockResolvedValue(mockInterventionsData);
    vi.spyOn(commandCenterApi, 'getAuditEvidencePack').mockResolvedValue(mockEvidencePackData);
    vi.spyOn(commandCenterApi, 'downloadReportCsv').mockResolvedValue(undefined);
    vi.spyOn(commandCenterApi, 'downloadReportPdf').mockResolvedValue(undefined);
  });

  it('renders operational reports workspace and displays pending verification data', async () => {
    render(
      <MemoryRouter>
        <OperationalReportsWorkspace />
      </MemoryRouter>
    );

    expect(screen.getByText('Operational Reports Workspace')).toBeInTheDocument();
    expect(screen.getByText('Pending Electronic Verification Report')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('FDR-REP-01')).toBeInTheDocument();
      expect(screen.getByText('FDR-REP-02')).toBeInTheDocument();
    });

    // Verify Simulated channel vs Live channel badges
    expect(screen.getByText('SIMULATED')).toBeInTheDocument();
    expect(screen.getByText('LIVE (SFMS_GATEWAY)')).toBeInTheDocument();

    // Verify Pending age
    expect(screen.getByText('24 days')).toBeInTheDocument();
  });

  it('switches tabs to Upcoming Maturities and displays deposit value and statutory notice', async () => {
    render(
      <MemoryRouter>
        <OperationalReportsWorkspace />
      </MemoryRouter>
    );

    const maturitiesTab = screen.getByRole('button', { name: /Upcoming Maturities/i });
    fireEvent.click(maturitiesTab);

    await waitFor(() => {
      expect(commandCenterApi.getUpcomingMaturitiesReport).toHaveBeenCalled();
    });

    expect(screen.getByText('Upcoming Deposit Maturities Report')).toBeInTheDocument();
    expect(screen.getByText(/Statutory Notice:/i)).toBeInTheDocument();
    expect(screen.getByText('FDR-MAT-01')).toBeInTheDocument();
    expect(screen.getByText('RENEWAL_LINKED')).toBeInTheDocument();
  });

  it('switches tabs to Missing Documents and displays policy versions and severity', async () => {
    render(
      <MemoryRouter>
        <OperationalReportsWorkspace />
      </MemoryRouter>
    );

    const missingDocsTab = screen.getByRole('button', { name: /Missing Documents/i });
    fireEvent.click(missingDocsTab);

    await waitFor(() => {
      expect(commandCenterApi.getMissingDocumentsReport).toHaveBeenCalled();
    });

    expect(screen.getByText('Missing & Non-Compliant Documents Report')).toBeInTheDocument();
    expect(screen.getByText('Original physical FDR scan is missing')).toBeInTheDocument();
    expect(screen.getByText('v1.0')).toBeInTheDocument();
    expect(screen.getByText('MISSING')).toBeInTheDocument();
  });

  it('switches tabs to Interventions Required and shows neutral reasons and next steps', async () => {
    render(
      <MemoryRouter>
        <OperationalReportsWorkspace />
      </MemoryRouter>
    );

    const interventionsTab = screen.getByRole('button', { name: /Interventions Required/i });
    fireEvent.click(interventionsTab);

    await waitFor(() => {
      expect(commandCenterApi.getInterventionsReport).toHaveBeenCalled();
    });

    expect(screen.getByText('Operational Interventions Report')).toBeInTheDocument();
    expect(screen.getByText('FDR-OVERDUE-01')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText(/Statutory renewal overdue by 15 days/i)).toBeInTheDocument();
    expect(screen.getByText(/Issue formal regulatory renewal demand/i)).toBeInTheDocument();
  });

  it('triggers CSV and PDF downloads when export buttons are clicked', async () => {
    render(
      <MemoryRouter>
        <OperationalReportsWorkspace />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('FDR-REP-01')).toBeInTheDocument();
    });

    const exportCsvBtn = screen.getByRole('button', { name: /Export CSV/i });
    fireEvent.click(exportCsvBtn);

    await waitFor(() => {
      expect(commandCenterApi.downloadReportCsv).toHaveBeenCalledWith(
        'PENDING_VERIFICATION',
        expect.any(Object)
      );
    });

    const exportPdfBtn = screen.getByRole('button', { name: /Export PDF/i });
    fireEvent.click(exportPdfBtn);

    await waitFor(() => {
      expect(commandCenterApi.downloadReportPdf).toHaveBeenCalledWith(
        'PENDING_VERIFICATION',
        expect.any(Object)
      );
    });
  });

  it('opens and displays the Audit Evidence Pack modal with SHA-256 digests and disclaimer', async () => {
    render(
      <MemoryRouter>
        <OperationalReportsWorkspace />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('FDR-REP-01')).toBeInTheDocument();
    });

    // Click the eye icon for the first instrument
    const inspectEvidenceBtn = screen.getAllByTitle('Audit Evidence Pack')[0];
    fireEvent.click(inspectEvidenceBtn);

    await waitFor(() => {
      expect(commandCenterApi.getAuditEvidencePack).toHaveBeenCalledWith('inst-rep-001');
    });

    expect(screen.getByText('Instrument Audit Evidence Pack')).toBeInTheDocument();
    expect(screen.getByText(/Audit Disclaimer:/i)).toBeInTheDocument();
    expect(screen.getByText('scan_copy.pdf')).toBeInTheDocument();
    expect(screen.getByText('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')).toBeInTheDocument();
    expect(screen.getByText('VERIFIED_VALID')).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole('button', { name: /Close Evidence Extract/i });
    fireEvent.click(closeBtn);
    expect(screen.queryByText('Instrument Audit Evidence Pack')).not.toBeInTheDocument();
  });
});
