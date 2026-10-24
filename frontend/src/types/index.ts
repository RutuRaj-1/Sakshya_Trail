/**
 * Core Domain Types for FDR Sentinel
 */

export interface SystemHealth {
  status: 'alive' | 'healthy' | 'degraded' | 'unreachable';
  timestamp: string;
  service: string;
  version: string;
  environment: string;
}

export interface DatabaseHealth {
  status: 'connected' | 'unreachable';
  is_ready: boolean;
  dialect: string;
  latency_ms?: number;
  error?: string | null;
}

export interface ReadinessState {
  status: 'ready' | 'degraded' | 'not_ready';
  is_ready: boolean;
  timestamp: string;
  components: {
    database: DatabaseHealth;
    api: {
      status: string;
      version: string;
      environment: string;
    };
  };
}

export type ApplicationRole =
  | 'SYSTEM_ADMIN'
  | 'SCRUTINY_OFFICER'
  | 'BRANCH_HEAD'
  | 'COMPETENT_AUTHORITY'
  | 'FINANCE_OFFICER'
  | 'INSTITUTION_USER'
  | 'AUDITOR';

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: ApplicationRole;
  is_active: boolean;
  must_change_password: boolean;
  institution_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  items: User[];
  total: number;
  skip: number;
  limit: number;
}

export interface RoleInfo {
  name: string;
  display_name: string;
  description: string;
  is_internal?: boolean;
  requires_institution?: boolean;
}

export interface Institution {
  id: string;
  code: string;
  aicte_id?: string;
  legal_name: string;
  name?: string;
  display_name?: string | null;
  institution_type: string;
  category?: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state: string;
  postal_code: string;
  assigned_office?: string | null;
  is_active: boolean;
  status?: string;
  is_synthetic?: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstitutionListResponse {
  items: Institution[];
  total: number;
  skip: number;
  limit: number;
}

export type TrustLevel =
  | 'L0_DECLARED'
  | 'L1_DOCUMENT_CONSISTENT'
  | 'L2_OFFICER_VERIFIED'
  | 'L3_BANK_CONFIRMED';

export type MaturityIndicator =
  | 'ACTIVE'
  | 'EXPIRING_SOON'
  | 'EXPIRED';

export interface Instrument {
  id: string;
  institution_id: string;
  institution_code?: string | null;
  institution_name?: string | null;
  instrument_type: string;
  reference_number: string;
  bank_name: string;
  branch?: string | null;
  amount: string | number;
  currency: string;
  issue_date: string;
  maturity_date: string;
  maturity_indicator: MaturityIndicator;
  lien_holder?: string | null;
  lien_details?: string | null;
  assigned_office?: string | null;
  status: string; // Administrative workflow status: DRAFT, REGISTERED
  trust_level: TrustLevel; // Separate trust hierarchy: L0, L1, L2, L3
  verification_level: string; // Compatibility alias for trust_level
  joint_with_aicte: boolean;
  lien_marked: boolean;
  is_synthetic: boolean;
  created_by_user_id?: string | null;
  updated_by_user_id?: string | null;
  remarks?: string | null;
  created_at: string;
  updated_at: string;
}

export interface InstrumentListResponse {
  items: Instrument[];
  total: number;
  skip: number;
  limit: number;
}

export interface DuplicateMatch {
  id: string;
  reference_number: string;
  bank_name: string;
  institution_id: string;
  institution_name?: string | null;
  institution_code?: string | null;
  amount: string | number;
  issue_date: string;
  maturity_date: string;
  status: string;
  trust_level: string;
  created_at: string;
}

export interface DuplicateWarningDetail {
  warning_message: string;
  matching_records: DuplicateMatch[];
}

export interface InstrumentSummary {
  total_instruments: number;
  active_count: number;
  expiring_soon_count: number;
  under_scrutiny_count: number;
  released_count: number;
  total_deposit_value: string | number;
}
