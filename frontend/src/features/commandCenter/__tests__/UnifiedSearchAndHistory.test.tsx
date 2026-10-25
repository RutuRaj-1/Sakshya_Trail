import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { UnifiedSearchPage } from '@/app/routes/UnifiedSearchPage';
import { InstrumentDetailPage } from '@/app/routes/InstrumentDetailPage';
import { commandCenterApi } from '@/api/commandCenter';
import { instrumentsApi } from '@/api/endpoints';
import type {
  InstrumentSearchResponse,
  ReleaseCaseSearchResponse,
  InstrumentDetailSnapshotResponse,
} from '@/types/commandCenter';

// Mock auth context
const mockUser = {
  id: 'usr-officer-1',
  email: 'officer@aicte.gov.in',
  role: 'SCRUTINY_OFFICER',
  full_name: 'Scrutiny Officer Sharma',
};

vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
  }),
}));

const mockInstrumentSearchData: InstrumentSearchResponse = {
  total_count: 2,
  skip: 0,
  limit: 15,
  sort_by: 'created_at',
  sort_order: 'desc',
  records: [
    {
      id: 'inst-test-001',
      reference_number: 'FDR-2026-SEARCH-01',
      institution_id: 'inst-pune-tech',
      institution_name: 'Pune College of Engineering',
      bank_name: 'State Bank of India',
      branch: 'Shivajinagar',
      amount: '500000.00',
      currency: 'INR',
      issue_date: '2025-01-01',
      maturity_date: '2026-12-31',
      status: 'ACTIVE',
      trust_level: 'L3_BANK_CONFIRMED',
      assigned_office: 'Western Regional Office',
      has_active_discrepancies: false,
      priority_category: null,
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: 'inst-test-002',
      reference_number: 'FDR-2026-SEARCH-02',
      institution_id: 'inst-mumbai-poly',
      institution_name: 'Mumbai Polytechnic Institute',
      bank_name: 'Punjab National Bank',
      branch: 'Bandra',
      amount: '1000000.00',
      currency: 'INR',
      issue_date: '2024-06-01',
      maturity_date: '2026-06-01',
      status: 'MATURED',
      trust_level: 'L1_DOCUMENT_CONSISTENT',
      assigned_office: 'Western Regional Office',
      has_active_discrepancies: true,
      priority_category: 'DISCREPANCY_FLAGGED',
      created_at: '2024-06-01T00:00:00Z',
    },
  ],
};

const mockReleaseCaseSearchData: ReleaseCaseSearchResponse = {
  total_count: 1,
  skip: 0,
  limit: 15,
  sort_by: 'created_at',
  sort_order: 'desc',
  records: [
    {
      id: 'case-rel-001',
      case_number: 'REL-2026-00042',
      case_reference: 'REL-2026-00042',
      instrument_id: 'inst-test-001',
      instrument_reference: 'FDR-2026-SEARCH-01',
      institution_id: 'inst-pune-tech',
      institution_name: 'Pune College of Engineering',
      request_type: 'SURRENDER_REFUND',
      case_type: 'INSTITUTION_CLOSURE',
      workflow_status: 'UNDER_SCRUTINY',
      readiness_outcome: 'READY',
      blockers_count: 0,
      created_at: '2026-02-15T10:30:00Z',
    },
  ],
};

const mockInstrumentDetailSnapshot: InstrumentDetailSnapshotResponse = {
  instrument: {
    id: 'inst-test-001',
    reference_number: 'FDR-2026-SEARCH-01',
    institution_id: 'inst-pune-tech',
    institution_name: 'Pune College of Engineering',
    bank_name: 'State Bank of India',
    branch: 'Shivajinagar',
    amount: '500000.00',
    currency: 'INR',
    issue_date: '2025-01-01',
    maturity_date: '2026-12-31',
    status: 'ACTIVE',
    trust_level: 'L3_BANK_CONFIRMED',
    assigned_office: 'Western Regional Office',
    lien_holder: 'AICTE Member Secretary',
    joint_with_aicte: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    active_discrepancy_count: 0,
    pending_verification_count: 0,
    active_findings: [],
    lineage_predecessors: [],
    lineage_successors: [],
  },
  documents: [
    {
      id: 'doc-ver-1',
      document_id: 'doc-fdr-cert-1',
      version_number: 1,
      category: 'FDR_CERTIFICATE',
      uploader_user_id: 'usr-officer-1',
      uploader_name: 'Officer Sharma',
      uploaded_at: '2025-01-02T10:00:00Z',
      sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      file_name: 'fdr_certificate_scan.pdf',
      file_size_bytes: 204800,
      is_verified: true,
      download_url: '/api/v1/documents/doc-fdr-cert-1/versions/1/content',
    },
  ],
  field_history: [
    {
      id: 'prov-001',
      field_name: 'bank_name',
      recorded_value: 'State Bank of India',
      previous_value: 'SBI Branch',
      source_type: 'OCR_EXTRACTION',
      source_actor_id: 'usr-officer-1',
      actor_name: 'Officer Sharma',
      evidence_reference: 'doc-ver-1',
      reason: 'Standardized bank name against RBI IFSC master',
      created_at: '2025-01-02T11:00:00Z',
    },
  ],
  lifecycle_lineage: [
    {
      event_type: 'VERIFICATION_REQUEST',
      timestamp: '2025-01-03T12:00:00Z',
      actor_id: 'VERIFICATION_ROUTER',
      summary: 'Electronic verification executed via SIMULATED adapter (CONFIRMED)',
      details: {
        channel: 'SIMULATED',
        status: 'CONFIRMED',
      },
      is_simulated: true,
    },
    {
      event_type: 'LIFECYCLE_EVALUATION',
      timestamp: '2026-01-01T00:00:00Z',
      actor_id: 'SYSTEM_CLOCK',
      summary: "Maturity stage evaluated as 'ACTIVE'",
      details: {
        days_to_maturity: 364,
        is_overdue: false,
      },
      is_simulated: false,
    },
  ],
  timeline: [
    {
      event_type: 'INSTRUMENT_REGISTERED',
      timestamp: '2025-01-01T09:00:00Z',
      actor_id: 'Registrar Staff',
      summary: 'Initial FDR statutory registration submitted',
      details: { status: 'REGISTERED' },
    },
  ],
  observations: [
    {
      id: 'obs-001',
      instrument_id: 'inst-test-001',
      observation_category: 'MANDATE',
      observation_text: 'Lien clausing explicitly marked in favor of AICTE as required.',
      author_user_id: 'usr-officer-1',
      author_name: 'Officer Sharma',
      author_role: 'SCRUTINY_OFFICER',
      status: 'RECORDED',
      supersedes_id: null,
      superseded_by_id: null,
      is_internal_only: false,
      created_at: '2025-01-02T14:00:00Z',
      updated_at: '2025-01-02T14:00:00Z',
    },
  ],
};

const mockBaseInstrument = {
  id: 'inst-test-001',
  reference_number: 'FDR-2026-SEARCH-01',
  institution_id: 'inst-pune-tech',
  institution_name: 'Pune College of Engineering',
  institution_code: 'AICTE-WRO-4001',
  bank_name: 'State Bank of India',
  branch: 'Shivajinagar',
  amount: '500000.00',
  currency: 'INR',
  issue_date: '2025-01-01',
  maturity_date: '2026-12-31',
  status: 'ACTIVE',
  trust_level: 'L3_BANK_CONFIRMED',
  maturity_indicator: 'ACTIVE',
  assigned_office: 'Western Regional Office',
  lien_holder: 'AICTE Member Secretary',
  joint_with_aicte: true,
  lien_details: 'Under AICTE statutory pledge regulations',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

describe('Unified Search and History Drill-Down (Module 7 Prompt 3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(commandCenterApi, 'searchInstruments').mockResolvedValue(mockInstrumentSearchData);
    vi.spyOn(commandCenterApi, 'searchReleaseCases').mockResolvedValue(mockReleaseCaseSearchData);
    vi.spyOn(instrumentsApi, 'get').mockResolvedValue(mockBaseInstrument as any);
    vi.spyOn(commandCenterApi, 'getInstrumentDetailSnapshot').mockResolvedValue(mockInstrumentDetailSnapshot);
  });

  describe('Unified Search Page', () => {
    it('renders search bar and default FDR Instruments results with status and trust badges', async () => {
      render(
        <MemoryRouter initialEntries={['/search']}>
          <UnifiedSearchPage />
        </MemoryRouter>
      );

      // Verify title & table header
      expect(screen.getByText('Unified Record Search & History Drill-Down')).toBeInTheDocument();
      expect(screen.getByText('FDR Instruments')).toBeInTheDocument();
      expect(screen.getByText('Release & Refund Cases')).toBeInTheDocument();

      // Wait for results
      await waitFor(() => {
        expect(screen.getByText('FDR-2026-SEARCH-01')).toBeInTheDocument();
        expect(screen.getByText('Pune College of Engineering')).toBeInTheDocument();
        expect(screen.getByText('FDR-2026-SEARCH-02')).toBeInTheDocument();
        expect(screen.getByText('Mumbai Polytechnic Institute')).toBeInTheDocument();
      });

      // Verify discrepancy flag
      expect(screen.getByText('Flagged')).toBeInTheDocument();
    });

    it('switches between FDR Instruments and Release Cases tabs', async () => {
      render(
        <MemoryRouter initialEntries={['/search']}>
          <UnifiedSearchPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('FDR-2026-SEARCH-01')).toBeInTheDocument();
      });

      // Click Release & Refund Cases tab
      const casesTab = screen.getByRole('button', { name: /Release & Refund Cases/i });
      fireEvent.click(casesTab);

      // Wait for release case records
      await waitFor(() => {
        expect(commandCenterApi.searchReleaseCases).toHaveBeenCalled();
        expect(screen.getByText('REL-2026-00042')).toBeInTheDocument();
        expect(screen.getByText('INSTITUTION_CLOSURE')).toBeInTheDocument();
      });
    });

    it('toggles advanced filters drawer and updates parameters', async () => {
      render(
        <MemoryRouter initialEntries={['/search']}>
          <UnifiedSearchPage />
        </MemoryRouter>
      );

      // Open filters drawer
      const filterBtn = screen.getByRole('button', { name: /Filters/i });
      fireEvent.click(filterBtn);

      // Verify advanced filter fields exist
      expect(screen.getByText('Administrative Status')).toBeInTheDocument();
      expect(screen.getByText('Trust Provenance Level')).toBeInTheDocument();
      expect(screen.getByText('Active Discrepancies Only')).toBeInTheDocument();
    });

    it('handles empty results display gracefully', async () => {
      vi.spyOn(commandCenterApi, 'searchInstruments').mockResolvedValueOnce({
        total_count: 0,
        skip: 0,
        limit: 15,
        sort_by: 'created_at',
        sort_order: 'desc',
        records: [],
      });

      render(
        <MemoryRouter initialEntries={['/search?q=NonExistent']}>
          <UnifiedSearchPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('No FDR instruments match criteria')).toBeInTheDocument();
      });
    });
  });

  describe('Instrument Detail & Historical Drill-Down View', () => {
    it('renders current snapshot, administrative state, trust level and maturity separation', async () => {
      render(
        <MemoryRouter initialEntries={['/instruments/inst-test-001']}>
          <Routes>
            <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('FDR-2026-SEARCH-01')).toBeInTheDocument();
        expect(screen.getByText('State Bank of India — Shivajinagar')).toBeInTheDocument();
      });

      // Verify explicit concept separation notices
      expect(screen.getByText('1. Administrative State')).toBeInTheDocument();
      expect(screen.getByText('2. Evidentiary Trust Level')).toBeInTheDocument();
      expect(screen.getByText('3. Maturity / Term Window')).toBeInTheDocument();
    });

    it('switches to Documents tab and displays versioned documents and SHA-256 hashes', async () => {
      render(
        <MemoryRouter initialEntries={['/instruments/inst-test-001']}>
          <Routes>
            <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Documents & Hashes/i)).toBeInTheDocument();
      });

      // Click Documents tab
      const docsTab = screen.getByRole('button', { name: /Documents & Hashes/i });
      fireEvent.click(docsTab);

      // Verify document version and hash
      expect(screen.getByText('v1')).toBeInTheDocument();
      expect(screen.getByText('fdr_certificate_scan.pdf')).toBeInTheDocument();
      expect(screen.getByText(/e3b0c44298fc1c14/i)).toBeInTheDocument();
      expect(screen.getByText('Download')).toBeInTheDocument();
    });

    it('switches to Field Provenance tab and displays audited previous and recorded values', async () => {
      render(
        <MemoryRouter initialEntries={['/instruments/inst-test-001']}>
          <Routes>
            <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Field Provenance/i })).toBeInTheDocument();
      });

      // Click Field Provenance tab
      fireEvent.click(screen.getByRole('button', { name: /Field Provenance/i }));

      // Verify field mutation
      expect(screen.getByText('bank_name')).toBeInTheDocument();
      expect(screen.getByText('SBI Branch')).toBeInTheDocument();
      expect(screen.getByText('Standardized bank name against RBI IFSC master')).toBeInTheDocument();
    });

    it('switches to Lifecycle & Lineage tab and highlights SIMULATED adapter responses', async () => {
      render(
        <MemoryRouter initialEntries={['/instruments/inst-test-001']}>
          <Routes>
            <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Lifecycle & Lineage/i })).toBeInTheDocument();
      });

      // Click Lifecycle & Lineage tab
      fireEvent.click(screen.getByRole('button', { name: /Lifecycle & Lineage/i }));

      // Verify simulated adapter badge
      expect(screen.getByText('SIMULATED ADAPTER')).toBeInTheDocument();
      expect(screen.getByText(/Electronic verification executed via SIMULATED adapter/i)).toBeInTheDocument();
    });

    it('switches to Scrutiny Observations tab and supports append-only creation and amending', async () => {
      const createObsSpy = vi.spyOn(commandCenterApi, 'createObservation').mockResolvedValue({
        id: 'obs-002',
        instrument_id: 'inst-test-001',
        observation_category: 'GENERAL',
        observation_text: 'Newly recorded observation test note',
        author_user_id: 'usr-officer-1',
        author_name: 'Officer Sharma',
        author_role: 'SCRUTINY_OFFICER',
        status: 'RECORDED',
        is_internal_only: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      render(
        <MemoryRouter initialEntries={['/instruments/inst-test-001']}>
          <Routes>
            <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Scrutiny Observations/i })).toBeInTheDocument();
      });

      // Click Observations tab
      fireEvent.click(screen.getByRole('button', { name: /Scrutiny Observations/i }));

      // Verify existing note
      expect(screen.getByText(/Lien clausing explicitly marked in favor of AICTE/i)).toBeInTheDocument();
      expect(screen.getByText('RECORDED')).toBeInTheDocument();

      // Open Record Note modal
      const recordBtn = screen.getByRole('button', { name: /Record Scrutiny Note/i });
      fireEvent.click(recordBtn);

      expect(screen.getByText('Record Scrutiny Observation')).toBeInTheDocument();

      // Fill in note
      const textarea = screen.getByPlaceholderText(/Enter detailed scrutiny observation findings/i);
      fireEvent.change(textarea, { target: { value: 'Newly recorded observation test note' } });

      // Submit
      const submitBtn = screen.getByRole('button', { name: 'Record Observation' });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(createObsSpy).toHaveBeenCalledWith(
          'inst-test-001',
          expect.objectContaining({
            observation_text: 'Newly recorded observation test note',
            observation_category: 'GENERAL',
          })
        );
      });
    });
  });
});
