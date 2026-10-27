import React from 'react';
import {
  FilePlus2,
  UploadCloud,
  FileCheck2,
  ShieldCheck,
  Clock,
  RefreshCw,
  DoorOpen,
  Scale,
  ClipboardList,
  AlertTriangle,
} from 'lucide-react';
import type { ApplicationRole } from '@/types';

/**
 * Stage Identifiers for the Nine Canonical FDR Workflow Stages.
 * Canonical Source of Truth: SIH 2026 Problem Statement 26265 PRD.
 */
export type CanonicalStageId =
  | 'STAGE_1_SUBMISSION_REGISTRATION'
  | 'STAGE_2_DOCUMENT_EVIDENCE'
  | 'STAGE_3_VALIDATION_DISCREPANCY'
  | 'STAGE_4_SCRUTINY_REVIEW'
  | 'STAGE_5_BANK_VERIFICATION_TRUST'
  | 'STAGE_6_LIFECYCLE_MONITORING'
  | 'STAGE_7_RENEWAL_LINEAGE'
  | 'STAGE_8_RELEASE_READINESS'
  | 'STAGE_9_MAKER_CHECKER_CLOSURE';

/**
 * Legacy stage identifiers preserved for internal tracker state machine compatibility.
 */
export type LegacyStageId =
  | 'STAGE_1_REGISTER'
  | 'STAGE_2_SUBMIT_ATTACH'
  | 'STAGE_3_VALIDATE'
  | 'STAGE_4_VERIFY'
  | 'STAGE_5_MONITOR'
  | 'STAGE_6_RENEW_REPLACE'
  | 'STAGE_7_RELEASE_GATE'
  | 'STAGE_8_AUTHORIZE'
  | 'STAGE_9_CLOSE_AUDIT';

export interface StageEndpointContract {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  description: string;
  isPrivileged: boolean;
  allowedRoles: ApplicationRole[];
}

export interface StageMappingDefinition {
  stageNumber: number;
  canonicalId: CanonicalStageId;
  legacyStageId: LegacyStageId;
  label: string;
  moduleName: string;
  businessPurpose: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  defaultRoute: string;
  backendEndpoints: string[];
  endpointsContract?: StageEndpointContract[];
  permittedReadRoles: ApplicationRole[];
  allowedRoles?: ApplicationRole[]; // alias for permittedReadRoles for backward compat
  permittedActionRoles: Record<string, ApplicationRole[]>;
  preconditions: string[];
  exitConditions: string[];
  auditEvents: string[];
  knownLimitations?: string[];
  limitations?: string; // string summary for backward compat
  badgeKey?: 'reviewQueueCount' | 'verificationQueueCount' | 'releaseCasesCount';
}

const ALL_ROLES: ApplicationRole[] = [
  'INSTITUTION_USER',
  'SCRUTINY_OFFICER',
  'BRANCH_HEAD',
  'COMPETENT_AUTHORITY',
  'FINANCE_OFFICER',
  'SYSTEM_ADMIN',
  'AUDITOR',
];

const BUREAU_INTERNAL_ROLES: ApplicationRole[] = [
  'SCRUTINY_OFFICER',
  'BRANCH_HEAD',
  'COMPETENT_AUTHORITY',
  'FINANCE_OFFICER',
  'SYSTEM_ADMIN',
  'AUDITOR',
];

/**
 * Authoritative Canonical Nine-Stage FDR Workflow Pipeline Definition.
 * EXACT ORDER:
 * 1. FDR Submission & Registration
 * 2. Document Upload & Evidence
 * 3. Validation & Discrepancy Detection
 * 4. Scrutiny & Review
 * 5. Bank Verification & Trust
 * 6. Lifecycle Monitoring
 * 7. Renewal & Successor Lineage
 * 8. Release Readiness
 * 9. Maker-Checker Decision & Closure
 */
export const CANONICAL_FDR_STAGES: StageMappingDefinition[] = [
  {
    stageNumber: 1,
    canonicalId: 'STAGE_1_SUBMISSION_REGISTRATION',
    legacyStageId: 'STAGE_1_REGISTER',
    label: 'FDR Submission & Registration',
    moduleName: 'Module 1: Intake & Registration',
    businessPurpose:
      'Intake and initial registration of institutional security deposit FDR certificates pledged under statutory AICTE terms.',
    description: 'Initial intake, deposit reference, bank branch, and term configuration.',
    icon: FilePlus2,
    defaultRoute: '/instruments',
    backendEndpoints: ['/api/v1/instruments'],
    permittedReadRoles: ALL_ROLES,
    allowedRoles: ALL_ROLES,
    permittedActionRoles: {
      register_fdr: ['INSTITUTION_USER', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'Institution must be active and registered in bureau database.',
      'Authenticated session with institution tenancy or bureau administrative scope.',
    ],
    exitConditions: [
      'Instrument persisted with unique reference number, amount, maturity date, and status REGISTERED or DRAFT.',
      'Initial trust level recorded as L0_DECLARED.',
    ],
    auditEvents: ['INSTRUMENT_REGISTERED', 'NOTIFICATION_DISPATCHED'],
    knownLimitations: [
      'Module 1 static expiry window (<=90d) operates independently from Module 5 dynamic policy rules until unified.',
    ],
    limitations: 'Static expiry window operates independently from dynamic policy rules.',
  },
  {
    stageNumber: 2,
    canonicalId: 'STAGE_2_DOCUMENT_EVIDENCE',
    legacyStageId: 'STAGE_2_SUBMIT_ATTACH',
    label: 'Document Upload & Evidence',
    moduleName: 'Module 2: Evidence & Documents',
    businessPurpose:
      'Upload certified FDR scan copy, calculate SHA-256 integrity hash digest, perform scan checks, and lock evidence.',
    description: 'Upload certified FDR scan, SHA-256 byte digest, and submission lock.',
    icon: UploadCloud,
    defaultRoute: '/documents',
    backendEndpoints: ['/api/v1/documents', '/api/v1/instruments/{id}/documents'],
    permittedReadRoles: ALL_ROLES,
    allowedRoles: ALL_ROLES,
    permittedActionRoles: {
      upload_evidence: ['INSTITUTION_USER', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'FDR certificate record must exist in database.',
      'Uploader must be authenticated and permitted (Auditors strictly excluded from uploading).',
    ],
    exitConditions: [
      'File stored with valid SHA-256 byte hash digest recorded in database.',
      'Scan status set to CLEAN or processing completed without security flags.',
    ],
    auditEvents: ['DOCUMENT_UPLOADED', 'DOCUMENT_HASH_VERIFIED'],
    knownLimitations: [
      'OCR text extraction is simulated in local development environments.',
    ],
    limitations: 'OCR text extraction simulated in local environment.',
  },
  {
    stageNumber: 3,
    canonicalId: 'STAGE_3_VALIDATION_DISCREPANCY',
    legacyStageId: 'STAGE_3_VALIDATE',
    label: 'Validation & Discrepancy Detection',
    moduleName: 'Module 3: Validation Engine',
    businessPurpose:
      'Execute deterministic rule engine verifying mandatory deposit parameters, term thresholds, date sequences, and flagging discrepancies.',
    description: 'Deterministic rule engine: term thresholds, date order, and scrutiny findings.',
    icon: AlertTriangle,
    defaultRoute: '/findings/queue?status=OPEN',
    backendEndpoints: ['/api/v1/findings/queue', '/api/v1/findings/{id}'],
    permittedReadRoles: BUREAU_INTERNAL_ROLES,
    allowedRoles: BUREAU_INTERNAL_ROLES,
    permittedActionRoles: {
      execute_rules: ['SYSTEM_ADMIN'],
      triage_findings: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'FDR metadata and uploaded document evidence available.',
    ],
    exitConditions: [
      'Rule evaluation completed; zero findings or findings persisted in review queue with severity classification.',
    ],
    auditEvents: ['VALIDATION_RUN_COMPLETED', 'DISCREPANCY_FLAGGED'],
    knownLimitations: [
      'Rule thresholds are static; dynamic multi-currency cross-checks not active.',
    ],
    badgeKey: 'reviewQueueCount',
  },
  {
    stageNumber: 4,
    canonicalId: 'STAGE_4_SCRUTINY_REVIEW',
    legacyStageId: 'STAGE_4_VERIFY',
    label: 'Scrutiny & Review',
    moduleName: 'Module 3: Scrutiny Desk',
    businessPurpose:
      'Bureau officer examination of discrepancies, recording append-only observations, and returning cases for institutional correction.',
    description: 'Officer examination, finding observation recording, and correction returns.',
    icon: ClipboardList,
    defaultRoute: '/findings/queue?status=IN_REVIEW',
    backendEndpoints: [
      '/api/v1/findings/queue',
      '/api/v1/dashboard/instruments/{id}/observations',
      '/api/v1/instruments/{id}/return-for-correction',
    ],
    permittedReadRoles: BUREAU_INTERNAL_ROLES,
    allowedRoles: BUREAU_INTERNAL_ROLES,
    permittedActionRoles: {
      record_observation: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
      return_for_correction: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
      resolve_finding: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'Discrepancy findings present in scrutiny queue.',
      'Officer has jurisdictional bureau review authorization.',
    ],
    exitConditions: [
      'All open observations addressed and findings marked RESOLVED, or instrument returned to institution with status RETURNED_FOR_CORRECTION.',
    ],
    auditEvents: ['OBSERVATION_RECORDED', 'INSTRUMENT_RETURNED_FOR_CORRECTION', 'FINDING_RESOLVED'],
    knownLimitations: [
      'Return-for-correction requires manual institution re-submission in current release.',
    ],
  },
  {
    stageNumber: 5,
    canonicalId: 'STAGE_5_BANK_VERIFICATION_TRUST',
    legacyStageId: 'STAGE_4_VERIFY',
    label: 'Bank Verification & Trust',
    moduleName: 'Module 4: Trust Desk',
    businessPurpose:
      'Establish cryptographic trust tier (L0 to L3). Dispatch external bank verification requests, evaluate response tokens, and record officer L2 attestation.',
    description: '4-tier trust assessment (L0–L3), officer attestation, and bank confirmation.',
    icon: ShieldCheck,
    defaultRoute: '/verification',
    backendEndpoints: [
      '/api/v1/verification/instruments/{id}/trust',
      '/api/v1/verification/instruments/{id}/trust/l2-officer-decision',
      '/api/v1/verification/requests',
      '/api/v1/verification/summary',
    ],
    permittedReadRoles: BUREAU_INTERNAL_ROLES,
    allowedRoles: BUREAU_INTERNAL_ROLES,
    permittedActionRoles: {
      dispatch_request: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
      record_l2_decision: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
      record_bank_response: ['SYSTEM_ADMIN'],
    },
    preconditions: [
      'Instrument registered with valid bank code and IFSC/branch identifiers.',
      'Document evidence available for officer inspection.',
    ],
    exitConditions: [
      'Trust level upgraded to L2_OFFICER_CONFIRMED (officer attestation) or L3_BANK_VERIFIED (genuine bank API/SFTP confirmation).',
      'Trust assessment score and audit event persisted.',
    ],
    auditEvents: ['TRUST_ASSESSMENT_COMPLETED', 'L2_OFFICER_CONFIRMED', 'VERIFICATION_DISPATCHED'],
    knownLimitations: [
      'External SFTP/Core-Banking connectors operate in simulated dispatch mode in development environments; simulated responses cannot produce genuine L3.',
    ],
    badgeKey: 'verificationQueueCount',
  },
  {
    stageNumber: 6,
    canonicalId: 'STAGE_6_LIFECYCLE_MONITORING',
    legacyStageId: 'STAGE_5_MONITOR',
    label: 'Lifecycle Monitoring',
    moduleName: 'Module 5: Lifecycle Scheduler',
    businessPurpose:
      'Continuous statutory calendar surveillance, maturity window triage (30/60/90 days), automated reminder escalation, and active lien maintenance.',
    description: 'Active statutory validity, daily calendar windows (30/60/90d), and reminders.',
    icon: Clock,
    defaultRoute: '/monitoring',
    backendEndpoints: [
      '/api/v1/lifecycle/instruments/{id}/evaluation',
      '/api/v1/dashboard/maturity-window',
      '/api/v1/lifecycle/instruments/{id}/notifications',
    ],
    permittedReadRoles: ALL_ROLES,
    allowedRoles: ALL_ROLES,
    permittedActionRoles: {
      run_daily_scheduler: ['SYSTEM_ADMIN'],
      dispatch_reminders: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD'],
      dismiss_notification: ['INSTITUTION_USER', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY', 'FINANCE_OFFICER', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'Instrument in status REGISTERED or ACTIVE with valid maturity date.',
    ],
    exitConditions: [
      'Daily lifecycle evaluation recorded.',
      'Maturity alerts dispatched to institution stakeholders at 90d, 60d, 30d, and maturity.',
    ],
    auditEvents: ['LIFECYCLE_EVALUATION_COMPLETED', 'REMINDER_DISPATCHED'],
    knownLimitations: [
      'Recurring daily scheduler triggered on-demand via API in test harness.',
    ],
  },
  {
    stageNumber: 7,
    canonicalId: 'STAGE_7_RENEWAL_LINEAGE',
    legacyStageId: 'STAGE_6_RENEW_REPLACE',
    label: 'Renewal & Successor Lineage',
    moduleName: 'Module 5: Lineage & Renewal',
    businessPurpose:
      'Manage deposit rollover, create successor FDR certificate with predecessor lineage linking, enforce continuity integrity, and record replacement.',
    description: 'Predecessor-successor linking, continuous tenure, and rollover governance.',
    icon: RefreshCw,
    defaultRoute: '/monitoring?tab=renewals',
    backendEndpoints: [
      '/api/v1/lifecycle/instruments/{id}/lineage',
      '/api/v1/lifecycle/instruments/{id}/renewal-draft',
      '/api/v1/lifecycle/instruments/{id}/renew',
      '/api/v1/lifecycle/lineage/validate',
    ],
    permittedReadRoles: ALL_ROLES,
    allowedRoles: ALL_ROLES,
    permittedActionRoles: {
      create_renewal_draft: ['INSTITUTION_USER', 'SCRUTINY_OFFICER', 'SYSTEM_ADMIN'],
      submit_successor: ['INSTITUTION_USER', 'SYSTEM_ADMIN'],
      approve_renewal_link: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'Predecessor instrument must be active or expiring (maturity within window or expired).',
      'Successor certificate details provided with unbroken statutory tenure.',
    ],
    exitConditions: [
      'Successor instrument created and linked to predecessor in lineage graph.',
      'Predecessor status transitioned to RENEWED or RENEWED_SUPERSEDED.',
      'Continuity score and audit lineage link verified.',
    ],
    auditEvents: ['RENEWAL_SUCCESSOR_CREATED', 'LINEAGE_LINKED'],
    knownLimitations: [
      'Cross-bank rollovers require manual verification of new bank mandate.',
    ],
  },
  {
    stageNumber: 8,
    canonicalId: 'STAGE_8_RELEASE_READINESS',
    legacyStageId: 'STAGE_7_RELEASE_GATE',
    label: 'Release Readiness',
    moduleName: 'Module 6: Readiness Assessment',
    businessPurpose:
      'Pre-discharge compliance verification. Audit mandatory readiness checklist, check legal holds and court injunctions, and ensure zero blockers before authority decision.',
    description: 'Pre-discharge compliance checklist, legal hold checks, and zero-blocker gate.',
    icon: DoorOpen,
    defaultRoute: '/release?status=UNDER_REVIEW',
    backendEndpoints: [
      '/api/v1/release/requests',
      '/api/v1/release/requests/{id}/evaluate-readiness',
      '/api/v1/release/requests/{id}/readiness',
    ],
    permittedReadRoles: BUREAU_INTERNAL_ROLES,
    allowedRoles: BUREAU_INTERNAL_ROLES,
    permittedActionRoles: {
      create_release_case: ['INSTITUTION_USER', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'FINANCE_OFFICER', 'SYSTEM_ADMIN'],
      evaluate_readiness: ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'FINANCE_OFFICER', 'SYSTEM_ADMIN'],
      manage_legal_holds: ['BRANCH_HEAD', 'SYSTEM_ADMIN'],
    },
    preconditions: [
      'Statutory obligations fulfilled or release petition initiated.',
      'Auditor restricted from creating release cases.',
    ],
    exitConditions: [
      'All checklist gates passed (statutory tenure, no active lien disputes, no legal holds).',
      'Release readiness confirmed with zero blockers and readiness score 100%.',
    ],
    auditEvents: ['RELEASE_READINESS_EVALUATED', 'LEGAL_HOLD_CHECKED'],
    knownLimitations: [
      'Court stay registry checks require manual legal clearance entry.',
    ],
    badgeKey: 'releaseCasesCount',
  },
  {
    stageNumber: 9,
    canonicalId: 'STAGE_9_MAKER_CHECKER_CLOSURE',
    legacyStageId: 'STAGE_8_AUTHORIZE',
    label: 'Maker-Checker Decision & Closure',
    moduleName: 'Module 6: Competent Authority & Closure',
    businessPurpose:
      'Grouped operational closure: (9a) Competent Authority statutory sanction, (9b) Finance Officer release-order recording, (9c) Downstream bank-action evidence, and (9d) Case closure in immutable audit ledger.',
    description: 'Competent Authority release sanction, Finance Officer order recording, and closure.',
    icon: Scale,
    defaultRoute: '/release?status=READY_FOR_AUTHORITY',
    backendEndpoints: [
      '/api/v1/release/requests/{id}/approve',
      '/api/v1/release/requests/{id}/record-order',
      '/api/v1/release/requests/{id}/confirm-bank-action',
      '/api/v1/release/requests/{id}/close-case',
    ],
    permittedReadRoles: BUREAU_INTERNAL_ROLES,
    allowedRoles: BUREAU_INTERNAL_ROLES,
    permittedActionRoles: {
      sanction_release: ['COMPETENT_AUTHORITY'],
      record_release_order: ['FINANCE_OFFICER'],
      record_bank_action: ['FINANCE_OFFICER', 'BRANCH_HEAD'],
      close_case: ['FINANCE_OFFICER', 'BRANCH_HEAD'],
    },
    preconditions: [
      'Readiness checklist passed with zero blockers.',
      'Distinct role assignments: Competent Authority sanctions; Finance Officer records financial order.',
    ],
    exitConditions: [
      '9a: Statutory release approved or rejected by Competent Authority.',
      '9b: Financial release order recorded exclusively by Finance Officer.',
      '9c: Bank execution confirmation and settlement evidence recorded.',
      '9d: Release case marked CLOSED with final tamper-evident audit record.',
    ],
    auditEvents: [
      'RELEASE_APPROVED',
      'RELEASE_ORDER_RECORDED',
      'RELEASE_BANK_ACTION_RECORDED',
      'RELEASE_CASE_CLOSED',
    ],
    knownLimitations: [
      'Downstream bank execution evidence uploaded via manual bank advice scan in current release.',
    ],
  },
];
