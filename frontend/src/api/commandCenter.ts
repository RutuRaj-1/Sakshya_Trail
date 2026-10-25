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
};
