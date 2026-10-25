export type MaturityStage =
  | 'ACTIVE'
  | 'MATURING_SOON'
  | 'CRITICAL_WINDOW'
  | 'MATURED'
  | 'EXPIRED';

export type LifecycleValidityStatus =
  | 'VALID'
  | 'PENDING_RENEWAL'
  | 'DEFAULTED'
  | 'RELEASE_APPROVED'
  | 'RELEASED';

export type NotificationChannel =
  | 'IN_APP'
  | 'EMAIL'
  | 'MOCK_SMS';

export type NotificationDeliveryStatus =
  | 'CREATED'
  | 'ATTEMPTED'
  | 'ACCEPTED'
  | 'DELIVERED'
  | 'FAILED'
  | 'MOCKED';

export interface NotificationDeliveryAttempt {
  id: string;
  attempt_number: number;
  attempted_at: string;
  status: NotificationDeliveryStatus;
  provider_name?: string | null;
  provider_reference?: string | null;
  failure_category?: string | null;
  failure_details?: string | null;
  is_mock: boolean;
}

export interface LifecycleNotification {
  id: string;
  instrument_id: string;
  event_type: string;
  milestone_days?: number | null;
  recipient_role: string;
  recipient_user_id?: string | null;
  channel: NotificationChannel;
  status: NotificationDeliveryStatus;
  template_id?: string | null;
  template_version?: string | null;
  rendered_title: string;
  rendered_message: string;
  retry_count: number;
  max_retries: number;
  last_attempted_at?: string | null;
  final_delivered_at?: string | null;
  is_mock: boolean;
  mock_disclaimer?: string | null;
  is_read: boolean;
  read_at?: string | null;
  failure_category?: string | null;
  failure_details?: string | null;
  created_at: string;
  attempts: NotificationDeliveryAttempt[];
}

export interface NotificationListResponse {
  notifications: LifecycleNotification[];
  total_count: number;
}

export interface LifecycleEvaluation {
  id: string;
  instrument_id: string;
  evaluation_date: string;
  days_to_maturity: number;
  maturity_stage: MaturityStage;
  validity_status: LifecycleValidityStatus;
  institution_action_due_date?: string | null;
  officer_action_due_date?: string | null;
  is_overdue: boolean;
  is_escalated: boolean;
  overdue_days: number;
  requires_immediate_action: boolean;
  applied_policy_version: number;
  created_at: string;
}

export type LineageRelationshipType =
  | 'RENEWAL'
  | 'REPLACEMENT'
  | 'AMENDMENT'
  | 'ROLLOVER';

export type LineageRelationshipStatus =
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'CANCELLED'
  | 'DISPUTED';

export type ContinuityIndicator =
  | 'CONTINUOUS'
  | 'GAP_DETECTED'
  | 'OVERLAP_DETECTED'
  | 'UNDETERMINED';

export type ContinuityOutcome =
  | 'CONTINUITY_UNDETERMINED'
  | 'CONTINUITY_WITHIN_CONFIGURED_TOLERANCE'
  | 'POTENTIAL_GAP'
  | 'POTENTIAL_OVERLAP'
  | 'POLICY_UNCONFIGURED';

export interface LineageCorrectionHistoryItem {
  action: string;
  reason: string;
  actor_user_id: string;
  actor_role: string;
  timestamp: string;
  old_status?: string | null;
  old_reason?: string | null;
  version_before?: number;
}

export interface LineageResponse {
  id: string;
  predecessor_instrument_id: string;
  successor_instrument_id: string;
  institution_id: string;
  relationship_type: LineageRelationshipType;
  relationship_status: LineageRelationshipStatus;
  reason_or_reference?: string | null;
  policy_id?: string | null;
  policy_version?: number | null;
  validity_gap_days?: number | null;
  validity_overlap_days?: number | null;
  continuity_indicator: ContinuityIndicator;
  continuity_details_json?: string | null;
  correction_history_json?: string | null;
  concurrency_version: number;
  created_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LineageChainItem {
  instrument_id: string;
  reference_number: string;
  bank_name: string;
  amount: string;
  issue_date?: string | null;
  maturity_date?: string | null;
  status: string;
  trust_level: string;
  depth: number;
}

export interface LineageTreeResponse {
  current_instrument_id: string;
  ancestors: LineageChainItem[];
  successors: LineageChainItem[];
  direct_predecessor_lineage?: LineageResponse | null;
  direct_successor_lineage?: LineageResponse | null;
}

export interface RenewalDraftResponse {
  predecessor_instrument_id: string;
  institution_id: string;
  suggested_fields: {
    bank_name: string;
    branch?: string | null;
    amount: string;
    currency: string;
    suggested_issue_date: string;
    suggested_maturity_date: string;
    suggested_effective_date?: string | null;
    lien_holder?: string | null;
    lien_details?: string | null;
    joint_with_aicte?: boolean;
    assigned_office?: string | null;
  };
  predecessor_summary: {
    id: string;
    reference_number: string;
    bank_name: string;
    branch?: string | null;
    amount: string;
    currency: string;
    issue_date?: string | null;
    maturity_date?: string | null;
    status: string;
    trust_level: string;
  };
  policy_summary: {
    policy_id: string;
    policy_code: string;
    version: number;
    max_allowed_gap_days: number;
    max_allowed_overlap_days: number;
    renewal_comparison_method: string;
  };
}

export interface RenewalCreateSuccessorRequest {
  bank_name: string;
  branch?: string;
  reference_number: string;
  amount: number | string;
  currency?: string;
  issue_date: string;
  maturity_date: string;
  effective_date?: string;
  lien_holder?: string;
  lien_details?: string;
  joint_with_aicte?: boolean;
  relationship_type?: LineageRelationshipType;
  reason_or_reference?: string;
}

export interface RenewalSuccessorCreatedResponse {
  successor_instrument_id: string;
  predecessor_instrument_id: string;
  lineage_id: string;
  reference_number: string;
  trust_level: string;
  status: string;
  validity_gap_days?: number | null;
  validity_overlap_days?: number | null;
  continuity_indicator: ContinuityIndicator;
  lineage: LineageResponse;
}

export interface ContinuityAssessmentResponse {
  lineage_id?: string | null;
  predecessor_instrument_id: string;
  successor_instrument_id: string;
  dates_compared: {
    predecessor_maturity?: string | null;
    successor_comparison_date?: string | null;
  };
  date_source_fields: {
    predecessor: string;
    successor: string;
  };
  comparison_semantics: string;
  gap_days?: number | null;
  overlap_days?: number | null;
  policy_version?: number | null;
  outcome: ContinuityOutcome;
  explanation: string;
  is_provisional: boolean;
  detector_type: string;
  finding_id?: string | null;
  evaluated_at?: string | null;
}

export interface LineageCorrectionRequest {
  action: 'DEACTIVATE' | 'SUPERSEDE' | 'UPDATE_REASON';
  reason: string;
  expected_concurrency_version?: number;
}

