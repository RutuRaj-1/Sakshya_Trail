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

export type FDRStatus = 
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_SCRUTINY'
  | 'VERIFIED'
  | 'ACTIVE'
  | 'MATURED'
  | 'RENEWED'
  | 'RELEASE_REQUESTED'
  | 'RELEASED';

export type VerificationLevel = 
  | 'L1_DECLARED'
  | 'L2_DOCUMENT_CONSISTENT'
  | 'L3_OFFICER_VERIFIED'
  | 'L4_BANK_CONFIRMED';

export interface Instrument {
  id: string;
  institution_id: string;
  reference_number: string;
  bank_name: string;
  branch?: string;
  amount: number;
  currency: string;
  issue_date: string;
  maturity_date: string;
  status: FDRStatus;
  verification_level: VerificationLevel;
  joint_with_aicte: boolean;
  lien_marked: boolean;
  remarks?: string;
  created_at: string;
  updated_at: string;
}

export interface InstrumentSummary {
  total_instruments: number;
  active_count: number;
  expiring_soon_count: number;
  under_scrutiny_count: number;
  released_count: number;
  total_deposit_value: number;
}
