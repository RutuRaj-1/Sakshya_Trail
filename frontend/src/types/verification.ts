/**
 * Module 4 — Trust, Provenance & Verification Desk
 * TypeScript type definitions mirroring backend Pydantic schemas.
 */

// --- Provenance ---------------------------------------------------------------

export interface FieldProvenanceItem {
  id: string;
  instrument_id: string;
  field_name: string;
  recorded_value: string;
  source_type: string;
  source_actor_id?: string | null;
  source_service_id?: string | null;
  source_timestamp: string;
  evidence_reference?: string | null;
  related_document_id?: string | null;
  related_document_version_id?: string | null;
  related_validation_run_id?: string | null;
  prior_provenance_id?: string | null;
  is_active: boolean;
  created_at: string;
}

// --- Trust Assessment ---------------------------------------------------------

export interface TrustAssessmentItem {
  id: string;
  instrument_id: string;
  field_name?: string | null;
  trust_level: string;
  supporting_evidence_references_json?: string | null;
  supporting_document_version_id?: string | null;
  related_verification_response_id?: string | null;
  assessing_user_id?: string | null;
  assessing_service?: string | null;
  reason: string;
  assessment_timestamp: string;
  trust_rule_version: number;
  status: string;
  is_downgrade: boolean;
  concurrency_version: number;
  prior_assessment_id?: string | null;
  source_authorization_config?: string | null;
  created_at: string;
}

export interface TrustTransitionHistoryItem {
  id: string;
  instrument_id: string;
  field_name?: string | null;
  prior_trust_level: string;
  new_trust_level: string;
  actor_user_id?: string | null;
  actor_service?: string | null;
  timestamp: string;
  reason: string;
  evidence_references_json?: string | null;
  trigger_type: string;
  outcome: string;
  is_downgrade: boolean;
  previous_assessment_id?: string | null;
  new_assessment_id?: string | null;
  concurrency_version_before?: number | null;
}

export interface AggregateTrustSummary {
  instrument_id: string;
  aggregate_trust_level: string;
  fields_by_level: Record<string, string[]>;
  uncovered_fields: string[];
  note: string;
}

// --- Verification Requests & Responses ---------------------------------------

export interface VerificationResponseItem {
  id: string;
  request_id: string;
  request_code?: string | null;
  instrument_id: string;
  channel: string;
  source_classification: string;
  source_identifier?: string | null;
  result: string;
  bank_reference_number?: string | null;
  bank_values_json?: string | null;
  field_comparisons_json?: string | null;
  is_simulated: boolean;
  responded_at: string;
  received_at: string;
  notes?: string | null;
  created_at: string;
}

export interface VerificationRequestItem {
  id: string;
  instrument_id: string;
  reference_code: string;
  channel: string;
  status: string;
  requested_fields_json?: string | null;
  attempt_count: number;
  last_attempt_at?: string | null;
  next_retry_at?: string | null;
  error_details?: string | null;
  closed_at?: string | null;
  closed_reason?: string | null;
  created_at: string;
  responses?: VerificationResponseItem[] | null;
}

// --- Request Payloads ---------------------------------------------------------

export interface CreateVerificationRequestPayload {
  channel?: string;
  requested_fields?: string[] | null;
  correlation_id?: string | null;
  notes?: string | null;
}

export interface DispatchVerificationPayload {
  scenario?: string;
}

export interface ManualVerificationRecordPayload {
  external_reference: string;
  communication_date: string;
  result?: string;
  reason: string;
  evidence_document_version_id?: string | null;
  bank_values?: Record<string, unknown> | null;
}

export interface L2OfficerDecisionPayload {
  reason: string;
  field_name?: string | null;
  supporting_document_version_id?: string | null;
  evidence_references?: string[] | null;
  expected_concurrency_version?: number | null;
}

export interface TrustDowngradePayload {
  target_trust_level: string;
  reason: string;
  field_name?: string | null;
  evidence_references?: string[] | null;
  triggering_event?: string | null;
  expected_concurrency_version?: number | null;
}

export interface CancelVerificationPayload {
  reason: string;
}

export interface RetryVerificationPayload {
  scenario?: string | null;
}
