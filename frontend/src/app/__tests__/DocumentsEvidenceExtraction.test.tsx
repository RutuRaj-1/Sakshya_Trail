import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { DocumentsEvidencePage } from '@/app/routes/DocumentsEvidencePage';
import { documentsApi, instrumentsApi } from '@/api/endpoints';
import type { ApplicationRole } from '@/types';

// Mock AuthContext
let mockUser: { id: string; name: string; email: string; role: ApplicationRole; institution_id?: string } | null = {
  id: 'usr-1',
  name: 'Scrutiny Officer User',
  email: 'scrutiny@fdr.test',
  role: 'SCRUTINY_OFFICER',
  institution_id: 'inst-1',
};

vi.mock('@/features/auth/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    isAuthenticated: !!mockUser,
  }),
}));

vi.mock('@/api/endpoints', () => ({
  documentsApi: {
    listByInstrument: vi.fn(),
    getDetail: vi.fn(),
    upload: vi.fn(),
    uploadVersion: vi.fn(),
    triggerExtraction: vi.fn(),
    getDownloadUrl: vi.fn().mockReturnValue('http://localhost/download'),
  },
  instrumentsApi: {
    list: vi.fn(),
    getById: vi.fn(),
  },
}));

describe('Prompt 5 — Documents & Evidence Extraction UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders extracted candidate fields and provenance when version has extraction', async () => {
    vi.mocked(instrumentsApi.list).mockResolvedValue({
      items: [
        {
          id: 'ins-123',
          fdr_number: 'FDR-2026-TEST',
          bank_name: 'State Bank of India',
          branch: 'Main Branch',
          amount: 1000000,
          maturity_date: '2026-12-31',
          status: 'ACTIVE',
        } as any,
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    } as any);

    vi.mocked(documentsApi.listByInstrument).mockResolvedValue({
      items: [
        {
          id: 'doc-1',
          instrument_id: 'ins-123',
          document_type: 'FDR_CERTIFICATE',
          original_filename: 'sbi_fdr_copy.pdf',
          file_size_bytes: 204800,
          content_type: 'application/pdf',
          scan_status: 'CLEAN',
          is_active: true,
          current_version_number: 1,
          total_versions: 1,
          created_at: '2026-10-27T10:00:00Z',
          updated_at: '2026-10-27T10:00:00Z',
          uploaded_by_user_id: 'usr-1',
        } as any,
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    } as any);

    vi.mocked(documentsApi.getDetail).mockResolvedValue({
      id: 'doc-1',
      instrument_id: 'ins-123',
      document_type: 'FDR_CERTIFICATE',
      original_filename: 'sbi_fdr_copy.pdf',
      file_size_bytes: 204800,
      content_type: 'application/pdf',
      scan_status: 'CLEAN',
      is_active: true,
      current_version_number: 1,
      total_versions: 1,
      created_at: '2026-10-27T10:00:00Z',
      updated_at: '2026-10-27T10:00:00Z',
      uploaded_by_user_id: 'usr-1',
      versions: [
        {
          id: 'ver-1',
          document_id: 'doc-1',
          version_number: 1,
          original_filename: 'sbi_fdr_copy.pdf',
          file_size_bytes: 204800,
          content_type: 'application/pdf',
          content_sha256: 'abc123hash',
          scan_status: 'CLEAN',
          is_active: true,
          created_at: '2026-10-27T10:00:00Z',
          uploaded_by_user_id: 'usr-1',
          extracted_fields: {
            id: 'ext-1',
            document_id: 'doc-1',
            version_id: 'ver-1',
            status: 'SUCCESS',
            doc_reference_number: 'SBI-FDR-987654',
            doc_bank_name: 'State Bank of India',
            doc_amount_str: '10,00,000.00',
            doc_maturity_date_str: '31/12/2026',
            doc_account_holder: 'ABC Infrastructure Ltd',
            doc_lien_holder: 'High Court Registrar',
            confidence_scores: { overall: 0.95 },
            created_at: '2026-10-27T10:01:00Z',
          },
        },
      ],
    } as any);

    render(
      <MemoryRouter initialEntries={['/documents']}>
        <Routes>
          <Route path="/documents" element={<DocumentsEvidencePage />} />
        </Routes>
      </MemoryRouter>
    );

    // Document card header
    await waitFor(() => {
      expect(screen.getByText('sbi_fdr_copy.pdf')).toBeInTheDocument();
    });

    // Expand version history
    const historyBtn = screen.getByText(/Version History/i);
    fireEvent.click(historyBtn);

    // Extraction status badge in version table
    await waitFor(() => {
      expect(screen.getByText('Extracted Candidate Fields (Automated) — Version 1')).toBeInTheDocument();
    });

    // Extracted fields
    expect(screen.getByText('SBI-FDR-987654')).toBeInTheDocument();
    expect(screen.getByText('₹10,00,000.00')).toBeInTheDocument();
    expect(screen.getByText('ABC Infrastructure Ltd')).toBeInTheDocument();
    expect(screen.getByText('High Court Registrar')).toBeInTheDocument();

    // Verify statutory disclaimer is present
    expect(
      screen.getByText(/Candidate values extracted via deterministic text parser/i)
    ).toBeInTheDocument();
  });

  it('allows triggering re-extraction for a version', async () => {
    vi.mocked(instrumentsApi.list).mockResolvedValue({
      items: [
        {
          id: 'ins-123',
          fdr_number: 'FDR-2026-TEST',
          bank_name: 'State Bank of India',
          branch: 'Main Branch',
          amount: 1000000,
          maturity_date: '2026-12-31',
          status: 'ACTIVE',
        } as any,
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    } as any);

    vi.mocked(documentsApi.listByInstrument).mockResolvedValue({
      items: [
        {
          id: 'doc-1',
          instrument_id: 'ins-123',
          document_type: 'FDR_CERTIFICATE',
          original_filename: 'sbi_fdr_copy.pdf',
          file_size_bytes: 204800,
          content_type: 'application/pdf',
          scan_status: 'CLEAN',
          is_active: true,
          current_version_number: 1,
          total_versions: 1,
          created_at: '2026-10-27T10:00:00Z',
          updated_at: '2026-10-27T10:00:00Z',
          uploaded_by_user_id: 'usr-1',
        } as any,
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    } as any);

    vi.mocked(documentsApi.getDetail).mockResolvedValue({
      id: 'doc-1',
      instrument_id: 'ins-123',
      document_type: 'FDR_CERTIFICATE',
      original_filename: 'sbi_fdr_copy.pdf',
      file_size_bytes: 204800,
      content_type: 'application/pdf',
      scan_status: 'CLEAN',
      is_active: true,
      current_version_number: 1,
      total_versions: 1,
      created_at: '2026-10-27T10:00:00Z',
      updated_at: '2026-10-27T10:00:00Z',
      uploaded_by_user_id: 'usr-1',
      versions: [
        {
          id: 'ver-1',
          document_id: 'doc-1',
          version_number: 1,
          original_filename: 'sbi_fdr_copy.pdf',
          file_size_bytes: 204800,
          content_type: 'application/pdf',
          content_sha256: 'abc123hash',
          scan_status: 'CLEAN',
          is_active: true,
          created_at: '2026-10-27T10:00:00Z',
          uploaded_by_user_id: 'usr-1',
          extracted_fields: {
            id: 'ext-1',
            document_id: 'doc-1',
            version_id: 'ver-1',
            status: 'FAILED',
            raw_text_excerpt: 'Error reading PDF',
          },
        },
      ],
    } as any);

    vi.mocked(documentsApi.triggerExtraction).mockResolvedValue({
      status: 'SUCCESS',
      extracted_fields: {
        id: 'ext-2',
        document_id: 'doc-1',
        version_id: 'ver-1',
        status: 'SUCCESS',
      },
    } as any);

    render(
      <MemoryRouter initialEntries={['/documents']}>
        <Routes>
          <Route path="/documents" element={<DocumentsEvidencePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('sbi_fdr_copy.pdf')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Version History/i));

    await waitFor(() => {
      expect(screen.getByText('Re-extract')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Re-extract'));

    await waitFor(() => {
      expect(documentsApi.triggerExtraction).toHaveBeenCalledWith('doc-1', 'ver-1');
    });
  });
});
