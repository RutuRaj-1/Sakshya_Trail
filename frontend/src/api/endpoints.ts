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
    city?: string;
    state?: string;
    is_synthetic?: boolean;
    institution_type?: string;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.append('search', params.search);
    if (params?.city) sp.append('city', params.city);
    if (params?.state) sp.append('state', params.state);
    if (params?.is_synthetic !== undefined) sp.append('is_synthetic', String(params.is_synthetic));
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
  verifyExternal: (id: string) =>
    apiClient.post<any>(`/institutions/${id}/verify-external`),
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
    city?: string;
    is_synthetic?: boolean;
    status?: string;
    trust_level?: string;
    maturity_start?: string;
    maturity_end?: string;
    maturity_indicator?: string;
    sort_by?: string;
    sort_order?: string;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.append('search', params.search);
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.city) sp.append('city', params.city);
    if (params?.is_synthetic !== undefined) sp.append('is_synthetic', String(params.is_synthetic));
    if (params?.status) sp.append('status', params.status);
    if (params?.trust_level) sp.append('trust_level', params.trust_level);
    if (params?.maturity_start) sp.append('maturity_start', params.maturity_start);
    if (params?.maturity_end) sp.append('maturity_end', params.maturity_end);
    if (params?.maturity_indicator) sp.append('maturity_indicator', params.maturity_indicator);
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

  // Operational Gateway Status (Prompt 2)
  getIntegrationStatus: () =>
    apiClient.get<any>('/verification/integration-status'),
};

export const lifecycleApi = {
  getEvaluation: (instrumentId: string) =>
    apiClient.get<import('@/types/lifecycle').LifecycleEvaluation>(
      `/lifecycle/instruments/${instrumentId}/evaluation`
    ),
  evaluateInstrument: (instrumentId: string, forceRecord: boolean = false) =>
    apiClient.post<import('@/types/lifecycle').LifecycleEvaluation>(
      `/lifecycle/instruments/${instrumentId}/evaluate`,
      { force_record: forceRecord }
    ),
  listNotifications: (instrumentId: string) =>
    apiClient.get<import('@/types/lifecycle').NotificationListResponse>(
      `/lifecycle/instruments/${instrumentId}/notifications`
    ),
  retryNotification: (notificationId: string, reason?: string) =>
    apiClient.post<import('@/types/lifecycle').LifecycleNotification>(
      `/lifecycle/notifications/${notificationId}/retry`,
      { reason }
    ),
  dispatchDueReminders: (instrumentId?: string) =>
    apiClient.post<{ dispatched_count: number; message: string }>(
      '/lifecycle/notifications/dispatch-due',
      { instrument_id: instrumentId }
    ),
  listFailedNotifications: (page: number = 1, limit: number = 50) =>
    apiClient.get<import('@/types/lifecycle').NotificationListResponse>(
      `/lifecycle/notifications/failed?page=${page}&limit=${limit}`
    ),
  getUserInbox: (unreadOnly: boolean = false) =>
    apiClient.get<import('@/types/lifecycle').NotificationListResponse>(
      `/lifecycle/notifications/inbox?unread_only=${unreadOnly}`
    ),
  markNotificationRead: (notificationId: string) =>
    apiClient.post<{ success: boolean; message: string }>(
      `/lifecycle/notifications/${notificationId}/read`
    ),
  markAllNotificationsRead: () =>
    apiClient.post<{ success: boolean; message: string; marked_read: number }>(
      '/lifecycle/notifications/read-all'
    ),
  getAdminOversightFeed: (page: number = 1, limit: number = 50) =>
    apiClient.get<import('@/types/lifecycle').NotificationListResponse>(
      `/lifecycle/admin/oversight?page=${page}&limit=${limit}`
    ),
  // Lineage & Renewal Methods (Module 5 Prompt 4)
  getLineage: (instrumentId: string) =>
    apiClient.get<import('@/types/lifecycle').LineageTreeResponse>(
      `/lifecycle/instruments/${instrumentId}/lineage`
    ),
  getRenewalDraft: (instrumentId: string) =>
    apiClient.get<import('@/types/lifecycle').RenewalDraftResponse>(
      `/lifecycle/instruments/${instrumentId}/renewal-draft`
    ),
  createSuccessorRenewal: (
    instrumentId: string,
    payload: import('@/types/lifecycle').RenewalCreateSuccessorRequest
  ) =>
    apiClient.post<import('@/types/lifecycle').RenewalSuccessorCreatedResponse>(
      `/lifecycle/instruments/${instrumentId}/renew`,
      payload
    ),
  validateLineage: (payload: {
    predecessor_instrument_id: string;
    successor_instrument_id: string;
    relationship_type?: string;
    allow_authorized_transfer?: boolean;
  }) => apiClient.post<any>('/lifecycle/lineage/validate', payload),
  linkLineage: (payload: {
    predecessor_instrument_id: string;
    successor_instrument_id: string;
    relationship_type?: string;
    reason_or_reference?: string;
    policy_id?: string;
    allow_authorized_transfer?: boolean;
  }) =>
    apiClient.post<import('@/types/lifecycle').LineageResponse>(
      '/lifecycle/lineage/link',
      payload
    ),
  getContinuity: (instrumentId: string) =>
    apiClient.get<import('@/types/lifecycle').ContinuityAssessmentResponse>(
      `/lifecycle/instruments/${instrumentId}/continuity`
    ),
  correctLineage: (
    lineageId: string,
    payload: import('@/types/lifecycle').LineageCorrectionRequest
  ) =>
    apiClient.post<import('@/types/lifecycle').LineageResponse>(
      `/lifecycle/lineage/${lineageId}/correct`,
      payload
    ),
  getCanonicalStages: () => apiClient.get<any[]>('/lifecycle/canonical-stages'),
};

export interface AuditEventItem {
  id: string;
  sequence_number?: number | null;
  created_at: string;
  action: string;
  entity_type: string;
  entity_id: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  actor_role?: string | null;
  outcome: string;
  request_id?: string | null;
  ip_address?: string | null;
  policy_version?: string | null;
  metadata?: Record<string, any>;
  previous_hash?: string | null;
  current_hash?: string | null;
}

export interface AuditQueryResponse {
  items: AuditEventItem[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface AuditChainVerificationResponse {
  status: 'PASS' | 'TAMPER_DETECTED' | 'ERROR';
  is_chain_intact: boolean;
  total_events_in_scope: number;
  verified_count: number;
  latest_sequence_number?: number | null;
  chain_head_hash?: string | null;
  first_inconsistency?: {
    sequence_number: number;
    event_id: string;
    failure_type: string;
    expected_hash?: string | null;
    actual_hash?: string | null;
    safe_explanation: string;
  } | null;
  verification_timestamp: string;
  verification_scope_description: string;
}

export const auditApi = {
  list: (params?: {
    entity_type?: string;
    entity_id?: string;
    action?: string;
    outcome?: string;
    actor_email?: string;
    actor_role?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.entity_type) sp.append('entity_type', params.entity_type);
    if (params?.entity_id) sp.append('entity_id', params.entity_id);
    if (params?.action) sp.append('action', params.action);
    if (params?.outcome) sp.append('outcome', params.outcome);
    if (params?.actor_email) sp.append('actor_email', params.actor_email);
    if (params?.actor_role) sp.append('actor_role', params.actor_role);
    if (params?.date_from) sp.append('date_from', params.date_from);
    if (params?.date_to) sp.append('date_to', params.date_to);
    if (params?.search) sp.append('search', params.search);
    if (params?.skip !== undefined) sp.append('skip', String(params.skip));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<AuditQueryResponse>(`/audit/events${query}`);
  },
  get: (id: string) => apiClient.get<AuditEventItem>(`/audit/events/${id}`),
  verifyChain: (params?: { sample_size?: number; start_sequence?: number }) => {
    const sp = new URLSearchParams();
    if (params?.sample_size) sp.append('sample_size', String(params.sample_size));
    if (params?.start_sequence) sp.append('start_sequence', String(params.start_sequence));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.post<AuditChainVerificationResponse>(`/audit/verify${query}`, {});
  },
};

export interface DocumentItem {
  id: string;
  category: string;
  title: string;
  status: string;
  current_version_number: number;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface ExtractedFieldsDetail {
  id: string;
  extraction_status: string;
  confidence_overall?: number | null;
  extracted_by?: string | null;
  doc_bank_name?: string | null;
  doc_bank_name_confidence?: number | null;
  doc_reference_number?: string | null;
  doc_reference_number_confidence?: number | null;
  doc_amount_str?: string | null;
  doc_amount_confidence?: number | null;
  doc_issue_date_str?: string | null;
  doc_issue_date_confidence?: number | null;
  doc_maturity_date_str?: string | null;
  doc_maturity_date_confidence?: number | null;
  doc_account_holder?: string | null;
  doc_account_holder_confidence?: number | null;
  doc_lien_holder?: string | null;
  doc_lien_holder_confidence?: number | null;
  error_details?: string | null;
  extracted_at?: string | null;
  status?: string;
  provider?: string;
  confidence_scores?: Record<string, number | null>;
  raw_text_excerpt?: string | null;
}

export interface DocumentVersionDetail {
  id: string;
  version_number: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256_hash: string;
  processing_status: string;
  scan_provider: string;
  uploader_user_id?: string;
  uploaded_at: string;
  extracted_fields?: ExtractedFieldsDetail | null;
  content_sha256?: string;
  original_filename?: string;
  scan_status?: string;
  file_size_bytes?: number;
  created_at?: string;
}

export interface DocumentDetail {
  id: string;
  instrument_id: string;
  institution_id: string;
  category: string;
  title: string;
  description?: string;
  status: string;
  current_version_id?: string;
  created_by_user_id?: string;
  created_at: string;
  updated_at: string;
  version_count: number;
  versions: DocumentVersionDetail[];
}

export const documentsApi = {
  listByInstrument: (instrumentId: string, params?: { offset?: number; limit?: number; category?: string }) => {
    const sp = new URLSearchParams();
    if (params?.offset !== undefined) sp.append('offset', String(params.offset));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    if (params?.category) sp.append('category', params.category);
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<{ total: number; offset: number; limit: number; items: DocumentItem[] }>(
      `/instruments/${instrumentId}/documents${query}`
    );
  },
  getDetail: (documentId: string) => apiClient.get<DocumentDetail>(`/documents/${documentId}`),
  upload: (instrumentId: string, formData: FormData) =>
    apiClient.post<{
      success: boolean;
      document_id: string;
      version_id: string;
      version_number: number;
      category: string;
      title: string;
      filename: string;
      content_type: string;
      file_size: string;
      sha256_hash: string;
      processing_status: string;
      scan_provider: string;
      extraction_status?: string | null;
      extracted_fields_id?: string | null;
      uploaded_at: string;
    }>(`/instruments/${instrumentId}/documents`, formData),
  uploadVersion: (documentId: string, formData: FormData) =>
    apiClient.post<{
      success: boolean;
      document_id: string;
      version_id: string;
      version_number: number;
      filename: string;
      content_type: string;
      file_size: string;
      sha256_hash: string;
      processing_status: string;
      scan_provider: string;
      extraction_status?: string | null;
      extracted_fields_id?: string | null;
      uploaded_at: string;
    }>(`/documents/${documentId}/versions`, formData),
  triggerExtraction: (documentId: string, versionId: string) =>
    apiClient.post<ExtractedFieldsDetail>(`/documents/${documentId}/versions/${versionId}/extract`),
  getDownloadUrl: (documentId: string, versionId: string) =>
    `/api/v1/documents/${documentId}/versions/${versionId}/content`,
};

