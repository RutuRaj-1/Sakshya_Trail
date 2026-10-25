import { apiClient } from './client';

export type ReleaseRequestType = 'RELEASE' | 'DISCHARGE' | 'REFUND';
export type ReleaseCaseType = 'STANDARD_MATURITY_RELEASE' | 'EARLY_CLOSURE' | 'FORCED_MATURITY';
export type ReleaseWorkflowStatus = 
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'RETURNED_FOR_CORRECTION'
  | 'READY_FOR_AUTHORITY'
  | 'APPROVED'
  | 'REJECTED'
  | 'RELEASE_ORDER_RECORDED'
  | 'BANK_SIDE_ACTION_PENDING'
  | 'COMPLETED'
  | 'CLOSED'
  | 'CANCELLED';

export type ReleaseDecisionType = 
  | 'SUBMIT'
  | 'RETURN_FOR_CORRECTION'
  | 'RECOMMEND_FOR_AUTHORITY'
  | 'APPROVE'
  | 'REJECT'
  | 'CANCEL';

export type BankActionStatus = 'PENDING' | 'CONFIRMED' | 'DISPUTED';

export interface ReleaseRequest {
  id: string;
  case_number: string;
  instrument_id: string;
  institution_id: string;
  request_type: ReleaseRequestType;
  case_type: ReleaseCaseType;
  policy_profile_id?: string;
  policy_version?: number;
  requester_id: string;
  request_reason: string;
  workflow_status: ReleaseWorkflowStatus;
  assigned_reviewer_id?: string;
  assigned_office?: string;
  latest_assessment_id?: string;
  submitted_at?: string;
  closed_at?: string;
  closure_notes?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ReleaseChecklistItem {
  id: string;
  item_code: string;
  title: string;
  explanation: string;
  requirement_type: string;
  is_mandatory_blocker: boolean;
  evaluation_type: string;
  expected_evidence_source: string;
  is_active: boolean;
}

export interface ChecklistProfile {
  id: string;
  profile_code: string;
  name: string;
  version: number;
  request_type: ReleaseRequestType;
  case_type: ReleaseCaseType;
  status: string;
  is_demo: boolean;
  demo_disclaimer: string;
  description?: string;
  effective_from?: string;
  effective_to?: string;
  created_at: string;
  items: ReleaseChecklistItem[];
}

export interface ReadinessCheckResult {
  id: string;
  item_code: string;
  status: string;
  is_mandatory_blocker: boolean;
  explanation: string;
  evidence_references_json?: string;
  source_module: string;
  evaluated_at: string;
}

export interface ReadinessAssessment {
  id: string;
  release_request_id: string;
  profile_id: string;
  profile_version: number;
  assessment_outcome: 'READY_FOR_APPROVAL' | 'BLOCKED' | 'PENDING_REVIEW' | 'INCOMPLETE';
  total_items_count: number;
  satisfied_count: number;
  blockers_count: number;
  pending_count: number;
  advisory_flags_count: number;
  summary_notes?: string;
  evaluated_by_user_id?: string;
  evaluated_at: string;
  results: ReadinessCheckResult[];
}

export interface ReleaseDecision {
  id: string;
  release_request_id: string;
  actor_user_id: string;
  actor_role: string;
  decision_type: ReleaseDecisionType;
  reason: string;
  policy_version?: number;
  readiness_assessment_id?: string;
  evidence_references_json?: string;
  previous_status: ReleaseWorkflowStatus;
  new_status: ReleaseWorkflowStatus;
  created_at: string;
}

export interface ReleaseOrderRecord {
  id: string;
  release_request_id: string;
  order_reference_number: string;
  order_date: string;
  responsible_officer_id: string;
  supporting_document_id?: string;
  status: string;
  bank_action_status: BankActionStatus;
  bank_action_notes?: string;
  bank_action_confirmed_at?: string;
  is_synthetic_demo: boolean;
  notes?: string;
  created_at: string;
}

export interface ReleaseRequestDetailResponse extends ReleaseRequest {
  policy_profile?: ChecklistProfile;
  assessments: ReadinessAssessment[];
  decisions: ReleaseDecision[];
  observations: Array<{
    id: string;
    release_request_id: string;
    officer_user_id: string;
    observation_type: string;
    notes: string;
    is_blocking: boolean;
    created_at: string;
  }>;
  release_orders: ReleaseOrderRecord[];
}

export const releaseApi = {
  // List release requests
  list: (params?: {
    status?: ReleaseWorkflowStatus;
    institution_id?: string;
    search?: string;
    page?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.append('status', params.status);
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.search) sp.append('search', params.search);
    if (params?.page !== undefined) sp.append('page', String(params.page));
    if (params?.limit !== undefined) sp.append('limit', String(params.limit));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<ReleaseRequest[]>(`/release/requests${query}`);
  },

  // Get request details
  getDetail: (id: string) => apiClient.get<ReleaseRequestDetailResponse>(`/release/requests/${id}`),

  // Create new request
  create: (payload: {
    instrument_id: string;
    request_type: ReleaseRequestType;
    case_type: ReleaseCaseType;
    request_reason: string;
    policy_profile_id?: string;
  }) => apiClient.post<ReleaseRequest>('/release/requests', payload),

  // Get active checklist profile
  getActiveProfile: (request_type?: ReleaseRequestType, case_type?: ReleaseCaseType) => {
    const sp = new URLSearchParams();
    if (request_type) sp.append('request_type', request_type);
    if (case_type) sp.append('case_type', case_type);
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<ChecklistProfile>(`/release/profiles/active${query}`);
  },

  // Evaluate readiness
  evaluateReadiness: (id: string, force_reevaluate?: boolean) => {
    const sp = force_reevaluate ? '?force_reevaluate=true' : '';
    return apiClient.post<ReadinessAssessment>(`/release/requests/${id}/evaluate-readiness${sp}`, {});
  },

  // Get latest readiness
  getReadiness: (id: string) => apiClient.get<ReadinessAssessment>(`/release/requests/${id}/readiness`),

  // Get readiness history
  getReadinessHistory: (id: string, limit?: number) => {
    const sp = limit ? `?limit=${limit}` : '';
    return apiClient.get<ReadinessAssessment[]>(`/release/requests/${id}/readiness/history${sp}`);
  },

  // Check release gate
  checkGate: (id: string, target_status?: string) => {
    const sp = target_status ? `?target_status=${target_status}` : '';
    return apiClient.post<{
      gate_passes: boolean;
      denial_reason?: string;
      assessment: ReadinessAssessment;
    }>(`/release/requests/${id}/check-gate${sp}`, {});
  },

  // Officer actions
  startReview: (id: string) => apiClient.post<ReleaseRequest>(`/release/requests/${id}/start-review`, {}),

  returnForCorrection: (id: string, reason: string, deficiency_references?: string) => {
    const sp = new URLSearchParams();
    sp.append('reason', reason);
    if (deficiency_references) sp.append('deficiency_references', deficiency_references);
    const query = `?${sp.toString()}`;
    return apiClient.post<ReleaseDecision>(`/release/requests/${id}/return-for-correction${query}`, {});
  },

  recommendForAuthority: (id: string, reason: string) => {
    const sp = `?reason=${encodeURIComponent(reason)}`;
    return apiClient.post<ReleaseDecision>(`/release/requests/${id}/recommend-for-authority${sp}`, {});
  },

  // Authority actions
  approve: (id: string, reason: string) => {
    const sp = `?reason=${encodeURIComponent(reason)}`;
    return apiClient.post<ReleaseDecision>(`/release/requests/${id}/approve${sp}`, {});
  },

  reject: (id: string, reason: string) => {
    const sp = `?reason=${encodeURIComponent(reason)}`;
    return apiClient.post<ReleaseDecision>(`/release/requests/${id}/reject${sp}`, {});
  },

  // Release order
  recordOrder: (id: string, payload: {
    order_reference_number: string;
    order_date: string;
    supporting_document_id?: string;
    is_synthetic_demo?: boolean;
    notes?: string;
  }) => apiClient.post<ReleaseOrderRecord>(`/release/requests/${id}/record-order`, payload),

  // Bank confirmation
  confirmBankAction: (id: string, bank_action_notes?: string) => {
    const sp = bank_action_notes ? `?bank_action_notes=${encodeURIComponent(bank_action_notes)}` : '';
    return apiClient.post<ReleaseRequest>(`/release/requests/${id}/confirm-bank-action${sp}`, {});
  },

  // Close case
  closeCase: (id: string, closure_notes?: string) => {
    const sp = closure_notes ? `?closure_notes=${encodeURIComponent(closure_notes)}` : '';
    return apiClient.post<ReleaseRequest>(`/release/requests/${id}/close-case${sp}`, {});
  },
};
