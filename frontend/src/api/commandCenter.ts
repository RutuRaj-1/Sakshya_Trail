/**
 * Module 7 — Command Center API Client
 * Interfaces directly with the versioned backend endpoints on /api/v1/dashboard/*
 */
import { apiClient } from './client';
import type {
  StatusCountsResponse,
  MaturityWindowResponse,
  OverdueEscalatedResponse,
  VerificationQueueResponse,
  DocumentCompletenessResponse,
  ReleaseBlockersResponse,
  MonthWiseMaturityLoadResponse,
  PriorityQueueResponse,
  CommandCenterOverviewResponse,
  MetricDictionaryResponse,
  InstrumentSearchResponse,
  ReleaseCaseSearchResponse,
  InstrumentDetailSnapshotResponse,
  ScrutinyObservationItem,
  ScrutinyObservationCreateRequest,
  ScrutinyObservationAmendRequest,
  ScrutinyObservationResolveRequest,
  PendingVerificationReportResponse,
  UpcomingMaturitiesReportResponse,
  MissingDocumentsReportResponse,
  InterventionsReportResponse,
  AuditEvidencePackResponse,
} from '@/types/commandCenter';

export interface StatusCountsParams {
  window_days?: number;
  institution_id?: string;
  assigned_office?: string;
  bank_name?: string;
  trust_level?: string;
}

export interface MaturityWindowParams {
  start_date?: string;
  end_date?: string;
  window_days?: number;
  institution_id?: string;
  assigned_office?: string;
  bank_name?: string;
  page?: number;
  page_size?: number;
}

export interface PriorityQueueParams {
  min_score?: number;
  institution_id?: string;
  assigned_office?: string;
  bank_name?: string;
  page?: number;
  page_size?: number;
}

export const commandCenterApi = {
  /** Consolidated high-level command center overview */
  getOverview: (windowDays: number = 90) =>
    apiClient.get<CommandCenterOverviewResponse>(`/dashboard/command-center?window_days=${windowDays}`),

  /** Category A: Status counts breakdown */
  getStatusCounts: (params?: StatusCountsParams) => {
    const sp = new URLSearchParams();
    if (params?.window_days) sp.append('window_days', params.window_days.toString());
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.assigned_office) sp.append('assigned_office', params.assigned_office);
    if (params?.bank_name) sp.append('bank_name', params.bank_name);
    if (params?.trust_level) sp.append('trust_level', params.trust_level);
    const qs = sp.toString();
    return apiClient.get<StatusCountsResponse>(`/dashboard/status-counts${qs ? `?${qs}` : ''}`);
  },

  /** Category B: Maturity window query */
  getMaturityWindow: (params?: MaturityWindowParams) => {
    const sp = new URLSearchParams();
    if (params?.start_date) sp.append('start_date', params.start_date);
    if (params?.end_date) sp.append('end_date', params.end_date);
    if (params?.window_days) sp.append('window_days', params.window_days.toString());
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.assigned_office) sp.append('assigned_office', params.assigned_office);
    if (params?.bank_name) sp.append('bank_name', params.bank_name);
    if (params?.page) sp.append('page', params.page.toString());
    if (params?.page_size) sp.append('page_size', params.page_size.toString());
    const qs = sp.toString();
    return apiClient.get<MaturityWindowResponse>(`/dashboard/maturity-window${qs ? `?${qs}` : ''}`);
  },

  /** Category C: Overdue & escalated work */
  getOverdueEscalated: (params?: { institution_id?: string; assigned_office?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.assigned_office) sp.append('assigned_office', params.assigned_office);
    if (params?.limit) sp.append('limit', params.limit.toString());
    const qs = sp.toString();
    return apiClient.get<OverdueEscalatedResponse>(`/dashboard/overdue-escalated${qs ? `?${qs}` : ''}`);
  },

  /** Category D: Verification desk queue & health */
  getVerificationQueue: (params?: { institution_id?: string; bank_name?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.bank_name) sp.append('bank_name', params.bank_name);
    if (params?.limit) sp.append('limit', params.limit.toString());
    const qs = sp.toString();
    return apiClient.get<VerificationQueueResponse>(`/dashboard/verification-queue${qs ? `?${qs}` : ''}`);
  },

  /** Category E: Document completeness */
  getDocumentCompleteness: (params?: { institution_id?: string }) => {
    const sp = new URLSearchParams();
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    const qs = sp.toString();
    return apiClient.get<DocumentCompletenessResponse>(`/dashboard/document-completeness${qs ? `?${qs}` : ''}`);
  },

  /** Category F: Release & refund blockers */
  getReleaseBlockers: (params?: { institution_id?: string; case_type?: string; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.case_type) sp.append('case_type', params.case_type);
    if (params?.limit) sp.append('limit', params.limit.toString());
    const qs = sp.toString();
    return apiClient.get<ReleaseBlockersResponse>(`/dashboard/release-blockers${qs ? `?${qs}` : ''}`);
  },

  /** Category G: Month-wise maturity load */
  getMaturityLoad: (params?: { calendar_year?: number; institution_id?: string; bank_name?: string; assigned_office?: string }) => {
    const sp = new URLSearchParams();
    if (params?.calendar_year) sp.append('calendar_year', params.calendar_year.toString());
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.bank_name) sp.append('bank_name', params.bank_name);
    if (params?.assigned_office) sp.append('assigned_office', params.assigned_office);
    const qs = sp.toString();
    return apiClient.get<MonthWiseMaturityLoadResponse>(`/dashboard/maturity-load${qs ? `?${qs}` : ''}`);
  },

  /** Category H: Operational priority queue */
  getPriorityQueue: (params?: PriorityQueueParams) => {
    const sp = new URLSearchParams();
    if (params?.min_score !== undefined) sp.append('min_score', params.min_score.toString());
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.assigned_office) sp.append('assigned_office', params.assigned_office);
    if (params?.bank_name) sp.append('bank_name', params.bank_name);
    if (params?.page) sp.append('page', params.page.toString());
    if (params?.page_size) sp.append('page_size', params.page_size.toString());
    const qs = sp.toString();
    return apiClient.get<PriorityQueueResponse>(`/dashboard/priority-queue${qs ? `?${qs}` : ''}`);
  },

  /** Central Metric Dictionary */
  getMetricDictionary: (category?: string) => {
    const qs = category ? `?category=${encodeURIComponent(category)}` : '';
    return apiClient.get<MetricDictionaryResponse>(`/dashboard/metrics/dictionary${qs}`);
  },

  /** Reusable search endpoint */
  search: (params: Record<string, any>) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        sp.append(k, String(v));
      }
    });
    return apiClient.get<{ total_count: number; records: any[] }>(`/dashboard/search?${sp.toString()}`);
  },

  /** Unified Instrument Search */
  searchInstruments: (params: Record<string, any>) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        sp.append(k, String(v));
      }
    });
    const qs = sp.toString();
    return apiClient.get<InstrumentSearchResponse>(`/dashboard/search/instruments${qs ? `?${qs}` : ''}`);
  },

  /** Unified Release Case Search */
  searchReleaseCases: (params: Record<string, any>) => {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        sp.append(k, String(v));
      }
    });
    const qs = sp.toString();
    return apiClient.get<ReleaseCaseSearchResponse>(`/dashboard/search/release-cases${qs ? `?${qs}` : ''}`);
  },

  /** Comprehensive Instrument Detail & History Snapshot */
  getInstrumentDetailSnapshot: (instrumentId: string) => {
    return apiClient.get<InstrumentDetailSnapshotResponse>(`/dashboard/instruments/${instrumentId}/detail`);
  },

  /** Scrutiny Observations list */
  getObservations: (instrumentId: string) => {
    return apiClient.get<ScrutinyObservationItem[]>(`/dashboard/instruments/${instrumentId}/observations`);
  },

  /** Create an append-only scrutiny observation */
  createObservation: (instrumentId: string, data: ScrutinyObservationCreateRequest) => {
    return apiClient.post<ScrutinyObservationItem>(`/dashboard/instruments/${instrumentId}/observations`, data);
  },

  /** Amend / supersede an existing scrutiny observation */
  amendObservation: (observationId: string, data: ScrutinyObservationAmendRequest) => {
    return apiClient.post<ScrutinyObservationItem>(`/dashboard/observations/${observationId}/amend`, data);
  },

  /** Resolve an observation note */
  resolveObservation: (observationId: string, data: ScrutinyObservationResolveRequest) => {
    return apiClient.post<ScrutinyObservationItem>(`/dashboard/observations/${observationId}/resolve`, data);
  },

  // ---------------------------------------------------------------------------
  // Operational Reports & Exports (PRD-FR-074 & Prompt 4)
  // ---------------------------------------------------------------------------

  /** Pending Verification Report */
  getPendingVerificationReport: (params?: ReportQueryParams) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    return apiClient.get<PendingVerificationReportResponse>(`/dashboard/reports/pending-verification${qs ? `?${qs}` : ''}`);
  },

  /** Upcoming Maturities Report */
  getUpcomingMaturitiesReport: (params?: ReportQueryParams) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    return apiClient.get<UpcomingMaturitiesReportResponse>(`/dashboard/reports/upcoming-maturities${qs ? `?${qs}` : ''}`);
  },

  /** Missing Documents Report */
  getMissingDocumentsReport: (params?: ReportQueryParams) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    return apiClient.get<MissingDocumentsReportResponse>(`/dashboard/reports/missing-documents${qs ? `?${qs}` : ''}`);
  },

  /** Interventions Required Report */
  getInterventionsReport: (params?: ReportQueryParams) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    return apiClient.get<InterventionsReportResponse>(`/dashboard/reports/interventions${qs ? `?${qs}` : ''}`);
  },

  /** Audit Evidence Pack per Instrument */
  getAuditEvidencePack: (instrumentId: string) => {
    return apiClient.get<AuditEvidencePackResponse>(`/dashboard/reports/evidence-pack/${instrumentId}`);
  },

  /** Download Report as CSV */
  downloadReportCsv: async (reportType: string, params?: ReportQueryParams) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    const cleanType = reportType.toLowerCase().replace(/_/g, '-');
    const url = `${apiClient.getBaseUrl()}/dashboard/reports/${cleanType}/export/csv${qs ? `?${qs}` : ''}`;
    
    const res = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Export download failed' }));
      throw new Error(err.detail || err.error || `CSV Export Failed (${res.status})`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `${cleanType}_export.csv`;
    
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
  },

  /** Download Report as PDF */
  downloadReportPdf: async (reportType: string, params?: ReportQueryParams) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    const qs = sp.toString();
    const cleanType = reportType.toLowerCase().replace(/_/g, '-');
    const url = `${apiClient.getBaseUrl()}/dashboard/reports/${cleanType}/export/pdf${qs ? `?${qs}` : ''}`;
    
    const res = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Export download failed' }));
      throw new Error(err.detail || err.error || `PDF Export Failed (${res.status})`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `${cleanType}_export.pdf`;
    
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
  },
};

export interface ReportQueryParams {
  window_days?: number;
  date_from?: string;
  date_to?: string;
  institution_id?: string;
  bank_name?: string;
  assigned_office?: string;
  trust_level?: string;
  status?: string;
  verification_status?: string;
  checklist_outcome?: string;
  intervention_type?: string;
  severity?: string;
  limit?: number;
  skip?: number;
}

