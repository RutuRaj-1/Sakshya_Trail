import { apiClient } from './client';
import type {
  SystemHealth,
  ReadinessState,
  RoleInfo,
  Institution,
  InstitutionListResponse,
  Instrument,
  InstrumentListResponse,
  InstrumentSummary,
  DashboardSummary,
  User,
  UserListResponse,
  ReviewQueueListResponse,
  ValidationFindingItem,
} from '@/types';
import type {
  FieldProvenanceItem,
  TrustAssessmentItem,
  TrustTransitionHistoryItem,
  AggregateTrustSummary,
  VerificationRequestItem,
  VerificationResponseItem,
  CreateVerificationRequestPayload,
  DispatchVerificationPayload,
  ManualVerificationRecordPayload,
  L2OfficerDecisionPayload,
  TrustDowngradePayload,
  CancelVerificationPayload,
  RetryVerificationPayload,
} from '@/types/verification';

export const healthApi = {
  getLiveness: () => apiClient.get<SystemHealth>('/health/live'),
  getReadiness: () => apiClient.get<ReadinessState>('/health/ready'),
};

export const authApi = {
  login: (credentials: { email: string; password: string }) =>
    apiClient.post<{ success: boolean; message: string; user: User; access_token: string }>(
      '/auth/login',
      credentials
    ),
  logout: () => apiClient.post<{ success: boolean; message: string }>('/auth/logout'),
  me: () => apiClient.get<User>('/auth/me'),
  changePassword: (payload: { current_password: string; new_password: string; confirm_new_password: string }) =>
    apiClient.post<{ success: boolean; message: string }>('/auth/change-password', payload),
  getRoles: () => apiClient.get<RoleInfo[]>('/auth/roles'),
};

export const institutionsApi = {
  list: (params?: {
    search?: string;
    state?: string;
    institution_type?: string;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.append('search', params.search);
    if (params?.state) sp.append('state', params.state);
    if (params?.institution_type) sp.append('institution_type', params.institution_type);
    if (params?.is_active !== undefined) sp.append('is_active', String(params.is_active));
    if (params?.skip !== undefined) sp.append('skip', String(params.skip));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<InstitutionListResponse>(`/institutions${query}`);
  },
  get: (id: string) => apiClient.get<Institution>(`/institutions/${id}`),
  create: (data: Partial<Institution>) => apiClient.post<Institution>('/institutions', data),
  update: (id: string, data: Partial<Institution>) =>
    apiClient.patch<Institution>(`/institutions/${id}`, data),
  setStatus: (id: string, is_active: boolean, reason?: string) =>
    apiClient.post<Institution>(`/institutions/${id}/status`, { is_active, reason }),
};

export const usersApi = {
  list: (params?: {
    search?: string;
    role?: string;
    is_active?: boolean;
    institution_id?: string;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.append('search', params.search);
    if (params?.role) sp.append('role', params.role);
    if (params?.is_active !== undefined) sp.append('is_active', String(params.is_active));
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.skip !== undefined) sp.append('skip', String(params.skip));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<UserListResponse>(`/auth/users${query}`);
  },
  get: (id: string) => apiClient.get<User>(`/auth/users/${id}`),
  provision: (data: {
    full_name: string;
    email: string;
    password: string;
    role: string;
    institution_id?: string | null;
    must_change_password?: boolean;
  }) => apiClient.post<User>('/auth/users', data),
  update: (id: string, data: { full_name?: string; role?: string; institution_id?: string | null }) =>
    apiClient.patch<User>(`/auth/users/${id}`, data),
  setStatus: (id: string, is_active: boolean, reason?: string) =>
    apiClient.post<User>(`/auth/users/${id}/status`, { is_active, reason }),
  resetPassword: (id: string, temporary_password?: string) =>
    apiClient.post<{
      success: boolean;
      message: string;
      temporary_password: string;
      must_change_password: boolean;
    }>(`/auth/users/${id}/reset-password`, { temporary_password }),
};

export const instrumentsApi = {
  list: (params?: {
    search?: string;
    institution_id?: string;
    status?: string;
    trust_level?: string;
    maturity_start?: string;
    maturity_end?: string;
    sort_by?: string;
    sort_order?: string;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.append('search', params.search);
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.status) sp.append('status', params.status);
    if (params?.trust_level) sp.append('trust_level', params.trust_level);
    if (params?.maturity_start) sp.append('maturity_start', params.maturity_start);
    if (params?.maturity_end) sp.append('maturity_end', params.maturity_end);
    if (params?.sort_by) sp.append('sort_by', params.sort_by);
    if (params?.sort_order) sp.append('sort_order', params.sort_order);
    if (params?.skip !== undefined) sp.append('skip', String(params.skip));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<InstrumentListResponse>(`/instruments${query}`);
  },
  get: (id: string) => apiClient.get<Instrument>(`/instruments/${id}`),
  create: (data: Partial<Instrument> & { confirm_duplicate?: boolean }) =>
    apiClient.post<Instrument>('/instruments', data),
  update: (id: string, data: Partial<Instrument> & { confirm_duplicate?: boolean }) =>
    apiClient.patch<Instrument>(`/instruments/${id}`, data),
  getSummary: () => apiClient.get<InstrumentSummary>('/instruments/summary'),
};

export const dashboardApi = {
  getSummary: () => apiClient.get<DashboardSummary>('/dashboard/summary'),
};

export const findingsApi = {
  getQueue: (params?: {
    status?: string[];
    severity?: string;
    category?: string;
    rule_id?: string;
    instrument_id?: string;
    institution_id?: string;
    search?: string;
    sort_by?: string;
    sort_order?: string;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.status && params.status.length > 0) {
      params.status.forEach((st) => sp.append('status', st));
    }
    if (params?.severity) sp.append('severity', params.severity);
    if (params?.category) sp.append('category', params.category);
    if (params?.rule_id) sp.append('rule_id', params.rule_id);
    if (params?.instrument_id) sp.append('instrument_id', params.instrument_id);
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.search) sp.append('search', params.search);
    if (params?.sort_by) sp.append('sort_by', params.sort_by);
    if (params?.sort_order) sp.append('sort_order', params.sort_order);
    if (params?.skip !== undefined) sp.append('skip', String(params.skip));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<ReviewQueueListResponse>(`/findings/queue${query}`);
  },

  get: (id: string) => apiClient.get<ValidationFindingItem>(`/findings/${id}`),

  transitionStatus: (
    id: string,
    data: {
      target_status: string;
      reason?: string;
      expected_concurrency_version?: number;
    }
  ) => apiClient.post<ValidationFindingItem>(`/findings/${id}/status`, data),

  assign: (id: string, data: { assigned_to_user_id: string }) =>
    apiClient.post<ValidationFindingItem>(`/findings/${id}/assign`, data),

  addObservation: (id: string, data: { observation_text: string }) =>
    apiClient.post<ValidationFindingItem>(`/findings/${id}/observations`, data),

  reEvaluate: (id: string) =>
    apiClient.post<ValidationFindingItem>(`/findings/${id}/re-evaluate`),

  returnForCorrection: (instrument_id: string, data: { explanation: string }) =>
    apiClient.post<{ status: string; instrument_id: string; remarks: string }>(
      `/instruments/${instrument_id}/return-for-correction`,
      data
    ),
};

// ─── Module 4 — Trust, Provenance & Verification Desk ─────────────────────────

export const verificationApi = {
  // Provenance
  getProvenance: (instrumentId: string) =>
    apiClient.get<FieldProvenanceItem[]>(`/verification/instruments/${instrumentId}/provenance`),
  getFieldProvenanceHistory: (instrumentId: string, fieldName: string) =>
    apiClient.get<FieldProvenanceItem[]>(
      `/verification/instruments/${instrumentId}/provenance/${encodeURIComponent(fieldName)}/history`
    ),

  // Trust assessments
  getTrustAssessments: (instrumentId: string) =>
    apiClient.get<TrustAssessmentItem[]>(`/verification/instruments/${instrumentId}/trust`),
  getTrustSummary: (instrumentId: string) =>
    apiClient.get<AggregateTrustSummary>(`/verification/instruments/${instrumentId}/trust/summary`),
  getTrustHistory: (instrumentId: string) =>
    apiClient.get<TrustTransitionHistoryItem[]>(
      `/verification/instruments/${instrumentId}/trust/history`
    ),

  // Dedicated trust operations
  recordL2Decision: (instrumentId: string, payload: L2OfficerDecisionPayload) =>
    apiClient.post<TrustAssessmentItem>(
      `/verification/instruments/${instrumentId}/trust/l2-officer-decision`,
      payload
    ),
  applyL3Confirmation: (
    instrumentId: string,
    payload: {
      verification_response_id: string;
      reason: string;
      source_authorization_config: string;
      field_name?: string | null;
      evidence_references?: string[] | null;
      requested_fields?: string[] | null;
      expected_concurrency_version?: number | null;
    }
  ) =>
    apiClient.post<TrustAssessmentItem>(
      `/verification/instruments/${instrumentId}/trust/l3-bank-confirmation`,
      payload
    ),
  performTrustDowngrade: (instrumentId: string, payload: TrustDowngradePayload) =>
    apiClient.post<TrustAssessmentItem>(
      `/verification/instruments/${instrumentId}/trust/downgrade`,
      payload
    ),

  // Verification requests
  listRequests: (instrumentId: string) =>
    apiClient.get<VerificationRequestItem[]>(
      `/verification/instruments/${instrumentId}/requests`
    ),
  createRequest: (instrumentId: string, payload: CreateVerificationRequestPayload) =>
    apiClient.post<VerificationRequestItem>(
      `/verification/instruments/${instrumentId}/requests`,
      payload
    ),
  getRequest: (requestId: string) =>
    apiClient.get<VerificationRequestItem>(`/verification/requests/${requestId}`),

  // Request actions
  dispatchRequest: (requestId: string, payload: DispatchVerificationPayload) =>
    apiClient.post<VerificationResponseItem>(`/verification/requests/${requestId}/dispatch`, payload),
  recordManualEvidence: (requestId: string, payload: ManualVerificationRecordPayload) =>
    apiClient.post<VerificationResponseItem>(
      `/verification/requests/${requestId}/manual-record`,
      payload
    ),
  retryRequest: (requestId: string, payload: RetryVerificationPayload) =>
    apiClient.post<VerificationResponseItem>(`/verification/requests/${requestId}/retry`, payload),
  cancelRequest: (requestId: string, payload: CancelVerificationPayload) =>
    apiClient.post<VerificationRequestItem>(`/verification/requests/${requestId}/cancel`, payload),

  // Responses
  getResponse: (responseId: string) =>
    apiClient.get<VerificationResponseItem>(`/verification/responses/${responseId}`),
};
