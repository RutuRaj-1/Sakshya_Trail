/**
 * Module 7 — Command Center, Search, Reporting & Audit
 * Frontend TypeScript Type Definitions
 */

export interface MetricDefinition {
  metric_id: string;
  display_label: string;
  category: string;
  prd_mapping: string;
  description: string;
  calculation_rule: string;
  inclusion_criteria: string;
  exclusion_criteria: string;
  date_basis: string;
  supported_filters: string[];
  authorization_scope: string;
  unconfigured_handling: string;
  api_endpoint: string;
}

export interface MetricDictionaryResponse {
  total_metrics: number;
  metrics: MetricDefinition[];
}

export interface StatusCountsResponse {
  metric_id: string;
  active_count: number;
  expiring_soon_count: number;
  matured_count: number;
  renewed_count: number;
  released_count: number;
  pending_count: number;
  total_instruments: number;
  total_deposit_value: string;
  window_days: number;
  date_basis: string;
  metadata: Record<string, any>;
}

export interface MaturityWindowRecordItem {
  id: string;
  reference_number: string;
  institution_id: string;
  institution_name?: string | null;
  bank_name: string;
  branch?: string | null;
  amount: string;
  issue_date: string;
  maturity_date: string;
  days_to_maturity: number;
  status: string;
  trust_level: string;
  assigned_office?: string | null;
}

export interface MaturityWindowResponse {
  metric_id: string;
  start_date: string;
  end_date: string;
  total_instruments: number;
  total_deposit_value: string;
  by_bank: Record<string, number>;
  by_office: Record<string, number>;
  page: number;
  page_size: number;
  total_records: number;
  records: MaturityWindowRecordItem[];
}

export interface OverdueItem {
  record_id: string;
  record_type: 'INSTRUMENT' | 'RELEASE_CASE' | string;
  reference_number: string;
  institution_id: string;
  institution_name?: string | null;
  assigned_office?: string | null;
  assignee_id?: string | null;
  assignee_name?: string | null;
  due_date?: string | null;
  days_overdue: number;
  is_escalated: boolean;
  escalation_role?: string | null;
  due_condition: string;
}

export interface OverdueEscalatedResponse {
  metric_id: string;
  total_overdue: number;
  total_escalated: number;
  by_office: Record<string, number>;
  by_assignee?: Record<string, number> | null;
  records: OverdueItem[];
}

export interface VerificationQueueItem {
  request_id: string;
  reference_code: string;
  instrument_id: string;
  instrument_reference: string;
  institution_id: string;
  institution_name?: string | null;
  bank_name: string;
  channel: string;
  status: string;
  created_at: string;
  age_days: number;
  attempt_count: number;
  is_source_unavailable: boolean;
}

export interface VerificationQueueResponse {
  metric_id: string;
  total_outstanding: number;
  average_age_days: number;
  age_distribution: Record<string, number>;
  source_unavailable_count: number;
  failed_count: number;
  records: VerificationQueueItem[];
}

export interface DocumentCompletenessResponse {
  metric_id: string;
  policy_configured: boolean;
  policy_version?: number | null;
  policy_status_message?: string | null;
  present_count: number;
  missing_count: number;
  unreadable_count: number;
  wrong_category_count: number;
  awaiting_confirmation_count: number;
  missing_categories_breakdown: Record<string, number>;
  metadata: Record<string, any>;
}

export interface ReleaseBlockerCaseItem {
  case_id: string;
  case_number: string;
  instrument_id: string;
  instrument_reference: string;
  institution_id: string;
  institution_name?: string | null;
  case_type: string;
  workflow_status: string;
  blockers_count: number;
  unsatisfied_item_codes: string[];
  latest_assessment_outcome: string;
}

export interface ReleaseBlockersResponse {
  metric_id: string;
  policy_configured: boolean;
  policy_version?: number | null;
  total_active_release_requests: number;
  blocked_requests_count: number;
  ready_requests_count: number;
  unmet_mandatory_items_count: number;
  blockers_by_requirement_type: Record<string, number>;
  cases: ReleaseBlockerCaseItem[];
}

export interface MonthWiseMaturityPoint {
  year: number;
  month: number;
  month_label: string;
  instrument_count: number;
  total_amount: string;
}

export interface MonthWiseMaturityLoadResponse {
  metric_id: string;
  calendar_year?: number | null;
  points: MonthWiseMaturityPoint[];
  grand_total_instruments: number;
  grand_total_amount: string;
  disclaimer: string;
}

export interface PriorityQueueItem {
  instrument_id: string;
  reference_number: string;
  institution_id: string;
  institution_name?: string | null;
  bank_name: string;
  amount: string;
  maturity_date: string;
  days_to_maturity: number;
  status: string;
  trust_level: string;
  priority_score: number;
  urgency_factor: number;
  discrepancy_factor: number;
  trust_factor: number;
  overdue_factor: number;
}

export interface PriorityQueueResponse {
  metric_id: string;
  total_count: number;
  page: number;
  page_size: number;
  weights_applied: Record<string, number>;
  items: PriorityQueueItem[];
}

export interface CommandCenterOverviewResponse {
  generated_at: string;
  user_role: string;
  scope_description: string;
  status_counts: StatusCountsResponse;
  maturity_window: MaturityWindowResponse;
  overdue_escalated: OverdueEscalatedResponse;
  verification_queue: VerificationQueueResponse;
  document_completeness: DocumentCompletenessResponse;
  release_blockers: ReleaseBlockersResponse;
  maturity_load: MonthWiseMaturityLoadResponse;
}

// =============================================================================
// Module 7 — Prompt 3: Unified Search, History & Observations
// =============================================================================

export interface InstrumentSearchItem {
  id: string;
  reference_number: string;
  institution_id: string;
  institution_name?: string | null;
  bank_name: string;
  branch?: string | null;
  amount: string;
  currency: string;
  issue_date: string;
  maturity_date: string;
  status: string;
  trust_level: string;
  assigned_office?: string | null;
  has_active_discrepancies: boolean;
  priority_category?: string | null;
  created_at: string;
}

export interface InstrumentSearchResponse {
  total_count: number;
  skip: number;
  limit: number;
  sort_by: string;
  sort_order: string;
  records: InstrumentSearchItem[];
}

export interface ReleaseCaseSearchItem {
  id: string;
  case_number: string;
  case_reference?: string | null;
  instrument_id: string;
  instrument_reference?: string | null;
  institution_id: string;
  institution_name?: string | null;
  request_type: string;
  case_type: string;
  workflow_status: string;
  readiness_outcome?: string | null;
  blockers_count: number;
  created_at: string;
}

export interface ReleaseCaseSearchResponse {
  total_count: number;
  skip: number;
  limit: number;
  sort_by: string;
  sort_order: string;
  records: ReleaseCaseSearchItem[];
}

export interface DocumentHistoryItem {
  id: string;
  document_id: string;
  version_number: number;
  category: string;
  uploader_user_id?: string | null;
  uploader_name?: string | null;
  uploaded_at: string;
  sha256_hash: string;
  file_name?: string | null;
  file_size_bytes?: number | null;
  is_verified: boolean;
  download_url: string;
}

export interface FieldProvenanceHistoryItem {
  id: string;
  field_name: string;
  recorded_value: string;
  previous_value?: string | null;
  source_type: string;
  source_actor_id?: string | null;
  actor_name?: string | null;
  evidence_reference?: string | null;
  reason?: string | null;
  created_at: string;
}

export interface LifecycleLineageItem {
  event_type: string;
  timestamp: string;
  actor_id?: string | null;
  summary: string;
  details: Record<string, any>;
  is_simulated: boolean;
}

export interface TimelineEventItem {
  event_type: string;
  timestamp: string;
  actor_id?: string | null;
  summary: string;
  details: Record<string, any>;
}

export interface ScrutinyObservationItem {
  id: string;
  instrument_id?: string | null;
  release_request_id?: string | null;
  finding_id?: string | null;
  supporting_document_id?: string | null;
  supporting_version_number?: number | null;
  observation_category: string;
  observation_text: string;
  author_user_id: string;
  author_name?: string | null;
  author_role: string;
  status: string;
  resolution_reason?: string | null;
  resolved_at?: string | null;
  resolved_by_user_id?: string | null;
  resolved_by_name?: string | null;
  supersedes_id?: string | null;
  superseded_by_id?: string | null;
  is_internal_only: boolean;
  created_at: string;
  updated_at: string;
}

export interface ActiveFindingSummary {
  id: string;
  rule_code: string;
  severity: string;
  message: string;
  field_name?: string | null;
  review_status: string;
  created_at?: string | null;
}

export interface InstrumentSnapshotData {
  id: string;
  reference_number: string;
  institution_id: string;
  institution_name?: string | null;
  bank_name: string;
  branch?: string | null;
  amount: string;
  currency: string;
  issue_date: string;
  maturity_date: string;
  status: string;
  trust_level: string;
  assigned_office?: string | null;
  lien_holder?: string | null;
  joint_with_aicte?: boolean;
  created_at: string;
  updated_at: string;
  active_discrepancy_count: number;
  pending_verification_count: number;
  active_findings: ActiveFindingSummary[];
  lineage_predecessors: Array<{ id: string; predecessor_id: string; status: string }>;
  lineage_successors: Array<{ id: string; successor_id: string; status: string }>;
}

export interface InstrumentDetailSnapshotResponse {
  instrument: InstrumentSnapshotData;
  documents: DocumentHistoryItem[];
  field_history: FieldProvenanceHistoryItem[];
  lifecycle_lineage: LifecycleLineageItem[];
  timeline: TimelineEventItem[];
  observations: ScrutinyObservationItem[];
}

export interface ScrutinyObservationCreateRequest {
  observation_text: string;
  observation_category?: string;
  finding_id?: string;
  supporting_document_id?: string;
  supporting_version_number?: number;
  is_internal_only?: boolean;
}

export interface ScrutinyObservationAmendRequest {
  observation_text: string;
  amendment_reason: string;
  is_internal_only?: boolean;
}

export interface ScrutinyObservationResolveRequest {
  resolution_reason: string;
}
