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

export interface StageMappingDefinition {
  stageNumber: number;
  canonicalId: CanonicalStageId;
  legacyStageId: LegacyStageId;
  label: string;
  moduleName: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  defaultRoute: string;
  backendEndpoints: string[];
  allowedRoles?: ApplicationRole[];
  badgeKey?: 'reviewQueueCount' | 'verificationQueueCount' | 'releaseCasesCount';
  limitations?: string;
}

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
    description: 'Initial intake, deposit reference, bank branch, and term configuration.',
    icon: FilePlus2,
    defaultRoute: '/instruments',
    backendEndpoints: ['/api/v1/instruments'],
    // Accessible to all roles; creation button inside is restricted to INSTITUTION_USER, SYSTEM_ADMIN
  },
  {
    stageNumber: 2,
    canonicalId: 'STAGE_2_DOCUMENT_EVIDENCE',
    legacyStageId: 'STAGE_2_SUBMIT_ATTACH',
    label: 'Document Upload & Evidence',
    moduleName: 'Module 2: Evidence & Documents',
    description: 'Upload certified FDR scan, SHA-256 byte digest, and submission lock.',
    icon: UploadCloud,
    defaultRoute: '/documents',
    backendEndpoints: ['/api/v1/documents'],
    // Accessible to all roles; mutation upload is restricted to creators/officers, excluding AUDITOR
  },
  {
    stageNumber: 3,
    canonicalId: 'STAGE_3_VALIDATION_DISCREPANCY',
    legacyStageId: 'STAGE_3_VALIDATE',
    label: 'Validation & Discrepancy Detection',
    moduleName: 'Module 3: Validation Engine',
    description: 'Deterministic rule engine: term thresholds, date order, and scrutiny findings.',
    icon: AlertTriangle,
    defaultRoute: '/findings/queue?status=OPEN',
    backendEndpoints: ['/api/v1/findings/queue'],
    allowedRoles: [
      'SYSTEM_ADMIN',
      'SCRUTINY_OFFICER',
      'BRANCH_HEAD',
      'COMPETENT_AUTHORITY',
      'FINANCE_OFFICER',
      'AUDITOR',
    ],
    badgeKey: 'reviewQueueCount',
  },
  {
    stageNumber: 4,
    canonicalId: 'STAGE_4_SCRUTINY_REVIEW',
    legacyStageId: 'STAGE_4_VERIFY',
    label: 'Scrutiny & Review',
    moduleName: 'Module 3: Scrutiny Desk',
    description: 'Officer examination, finding observation recording, and correction returns.',
    icon: ClipboardList,
    defaultRoute: '/findings/queue?status=IN_REVIEW',
    backendEndpoints: ['/api/v1/findings/queue', '/api/v1/findings/{id}/observations'],
    allowedRoles: [
      'SYSTEM_ADMIN',
      'SCRUTINY_OFFICER',
      'BRANCH_HEAD',
      'COMPETENT_AUTHORITY',
      'FINANCE_OFFICER',
      'AUDITOR',
    ],
  },
  {
    stageNumber: 5,
    canonicalId: 'STAGE_5_BANK_VERIFICATION_TRUST',
    legacyStageId: 'STAGE_4_VERIFY',
    label: 'Bank Verification & Trust',
    moduleName: 'Module 4: Trust Desk',
    description: '4-tier trust assessment (L0–L3), officer attestation, and bank confirmation.',
    icon: ShieldCheck,
    defaultRoute: '/verification',
    backendEndpoints: [
      '/api/v1/verification/instruments/{id}/trust',
      '/api/v1/verification/instruments/{id}/trust/l2-officer-decision',
    ],
    allowedRoles: [
      'SYSTEM_ADMIN',
      'SCRUTINY_OFFICER',
      'BRANCH_HEAD',
      'COMPETENT_AUTHORITY',
      'FINANCE_OFFICER',
      'AUDITOR',
    ],
    badgeKey: 'verificationQueueCount',
  },
  {
    stageNumber: 6,
    canonicalId: 'STAGE_6_LIFECYCLE_MONITORING',
    legacyStageId: 'STAGE_5_MONITOR',
    label: 'Lifecycle Monitoring',
    moduleName: 'Module 5: Lifecycle Scheduler',
    description: 'Active statutory validity, daily calendar windows (30/60/90d), and reminders.',
    icon: Clock,
    defaultRoute: '/monitoring',
    backendEndpoints: [
      '/api/v1/lifecycle/instruments/{id}/evaluation',
      '/api/v1/dashboard/maturity-window',
    ],
  },
  {
    stageNumber: 7,
    canonicalId: 'STAGE_7_RENEWAL_LINEAGE',
    legacyStageId: 'STAGE_6_RENEW_REPLACE',
    label: 'Renewal & Successor Lineage',
    moduleName: 'Module 5: Lineage & Renewal',
    description: 'Predecessor-successor linking, continuous tenure, and rollover governance.',
    icon: RefreshCw,
    defaultRoute: '/monitoring?tab=renewals',
    backendEndpoints: [
      '/api/v1/lifecycle/instruments/{id}/lineage',
      '/api/v1/lifecycle/instruments/{id}/renew',
    ],
  },
  {
    stageNumber: 8,
    canonicalId: 'STAGE_8_RELEASE_READINESS',
    legacyStageId: 'STAGE_7_RELEASE_GATE',
    label: 'Release Readiness',
    moduleName: 'Module 6: Readiness Assessment',
    description: 'Pre-discharge compliance checklist, legal hold checks, and zero-blocker gate.',
    icon: DoorOpen,
    defaultRoute: '/release?status=UNDER_REVIEW',
    backendEndpoints: ['/api/v1/release/blockers', '/api/v1/release/{id}/evaluate-readiness'],
    badgeKey: 'releaseCasesCount',
  },
  {
    stageNumber: 9,
    canonicalId: 'STAGE_9_MAKER_CHECKER_CLOSURE',
    legacyStageId: 'STAGE_8_AUTHORIZE',
    label: 'Maker-Checker Decision & Closure',
    moduleName: 'Module 6: Competent Authority & Closure',
    description: 'Competent Authority release sanction, Finance Officer order recording, and closure.',
    icon: Scale,
    defaultRoute: '/release?status=READY_FOR_AUTHORITY',
    backendEndpoints: [
      '/api/v1/release/{id}/approve',
      '/api/v1/release/{id}/orders',
      '/api/v1/release/{id}/close',
    ],
  },
];
