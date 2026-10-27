import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FilePlus2,
  UploadCloud,
  FileCheck2,
  ShieldCheck,
  Clock,
  RefreshCw,
  DoorOpen,
  Scale,
  Archive,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  ShieldAlert,
  ClipboardList,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/features/auth/AuthContext';
import type { Instrument } from '@/types';
import type { InstrumentDetailSnapshotResponse } from '@/types/commandCenter';

export type StageId =
  | 'STAGE_1_REGISTER'
  | 'STAGE_2_SUBMIT_ATTACH'
  | 'STAGE_3_VALIDATE'
  | 'STAGE_4_VERIFY'
  | 'STAGE_5_MONITOR'
  | 'STAGE_6_RENEW_REPLACE'
  | 'STAGE_7_RELEASE_GATE'
  | 'STAGE_8_AUTHORIZE'
  | 'STAGE_9_CLOSE_AUDIT';

export interface StageDefinition {
  id: StageId;
  stageNumber: number;
  label: string;
  moduleName: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  defaultRoute: string;
  targetQueueLabel: string;
  actionLabel: string;
}

export const LIFECYCLE_STAGES: StageDefinition[] = [
  {
    id: 'STAGE_1_REGISTER',
    stageNumber: 1,
    label: 'FDR Submission & Registration',
    moduleName: 'Module 1: Intake & Registration',
    description: 'Initial intake, deposit reference, bank branch, and term configuration.',
    icon: FilePlus2,
    defaultRoute: '/instruments',
    targetQueueLabel: 'Draft Registry',
    actionLabel: 'Record New FDR',
  },
  {
    id: 'STAGE_2_SUBMIT_ATTACH',
    stageNumber: 2,
    label: 'Document Upload & Evidence',
    moduleName: 'Module 2: Evidence & Documents',
    description: 'Upload certified FDR scan, SHA-256 byte digest, and submission lock.',
    icon: UploadCloud,
    defaultRoute: '/documents',
    targetQueueLabel: 'Evidence Hub',
    actionLabel: 'Attach Documents',
  },
  {
    id: 'STAGE_3_VALIDATE',
    stageNumber: 3,
    label: 'Validation & Discrepancy Detection',
    moduleName: 'Module 3: Validation Engine',
    description: 'Deterministic rule engine: term thresholds, date order, and scrutiny findings.',
    icon: FileCheck2,
    defaultRoute: '/findings/queue?status=OPEN',
    targetQueueLabel: 'Validation Findings',
    actionLabel: 'Scrutinize Discrepancies',
  },
  {
    id: 'STAGE_4_VERIFY',
    stageNumber: 4,
    label: 'Scrutiny & Review',
    moduleName: 'Module 3: Scrutiny Desk',
    description: 'Officer examination, finding observation recording, and correction returns.',
    icon: ClipboardList,
    defaultRoute: '/findings/queue?status=IN_REVIEW',
    targetQueueLabel: 'Scrutiny Queue',
    actionLabel: 'Examine Observations',
  },
  {
    id: 'STAGE_5_MONITOR',
    stageNumber: 5,
    label: 'Bank Verification & Trust',
    moduleName: 'Module 4: Trust Desk',
    description: '4-tier trust assessment (L0–L3), officer attestation, and bank confirmation.',
    icon: ShieldCheck,
    defaultRoute: '/verification',
    targetQueueLabel: 'Verification Desk',
    actionLabel: 'Verify Trust Provenance',
  },
  {
    id: 'STAGE_6_RENEW_REPLACE',
    stageNumber: 6,
    label: 'Lifecycle Monitoring',
    moduleName: 'Module 5: Lifecycle Scheduler',
    description: 'Active statutory validity, daily calendar windows (30/60/90d), and reminders.',
    icon: Clock,
    defaultRoute: '/monitoring',
    targetQueueLabel: 'Monitoring Desk',
    actionLabel: 'Track Maturities',
  },
  {
    id: 'STAGE_7_RELEASE_GATE',
    stageNumber: 7,
    label: 'Renewal & Successor Lineage',
    moduleName: 'Module 5: Lineage & Renewal',
    description: 'Predecessor-successor linking, continuous tenure, and rollover governance.',
    icon: RefreshCw,
    defaultRoute: '/monitoring?tab=renewals',
    targetQueueLabel: 'Renewal Lineage',
    actionLabel: 'Initiate Rollover',
  },
  {
    id: 'STAGE_8_AUTHORIZE',
    stageNumber: 8,
    label: 'Release Readiness',
    moduleName: 'Module 6: Readiness Assessment',
    description: 'Pre-discharge compliance checklist, legal hold checks, and zero-blocker gate.',
    icon: DoorOpen,
    defaultRoute: '/release?status=UNDER_REVIEW',
    targetQueueLabel: 'Readiness Gate',
    actionLabel: 'Evaluate Blockers',
  },
  {
    id: 'STAGE_9_CLOSE_AUDIT',
    stageNumber: 9,
    label: 'Maker-Checker Decision & Closure',
    moduleName: 'Module 6: Competent Authority & Closure',
    description: 'Maker-checker release sanction, Finance Officer order recording, and closure.',
    icon: Scale,
    defaultRoute: '/release?status=READY_FOR_AUTHORITY',
    targetQueueLabel: 'Authority Desk',
    actionLabel: 'Sanction & Close Case',
  },
];

interface PortfolioViewProps {
  mode: 'portfolio';
  stageCounts?: Record<StageId, number>;
  isLoading?: boolean;
}

interface InstrumentViewProps {
  mode: 'instrument';
  instrument: Instrument;
  snapshot?: InstrumentDetailSnapshotResponse | null;
  onNavigateTab?: (tabKey: string) => void;
  role?: string;
}

export type NineStageLifecycleTrackerProps = PortfolioViewProps | InstrumentViewProps;

export interface StageEvaluationResult {
  currentStageNumber: number;
  stageStatus: 'NORMAL' | 'BLOCKED' | 'WARNING' | 'COMPLETED';
  statusSummary: string;
  nextAction: string;
}

export function evaluateInstrumentLifecycleStage(
  instrument: Instrument,
  snapshot?: InstrumentDetailSnapshotResponse | null,
  userRole?: string
): StageEvaluationResult {
  const status = instrument.status;
  const trust = instrument.trust_level;
  const maturityIndicator = instrument.maturity_indicator;
  const hasDocuments = (snapshot?.documents?.length ?? 0) > 0;
  const observations = snapshot?.observations ?? [];
  const openObservations = observations.filter((o) => o.status === 'RECORDED');

  let currentStageNumber = 1;
  let stageStatus: 'NORMAL' | 'BLOCKED' | 'WARNING' | 'COMPLETED' = 'NORMAL';
  let statusSummary = '';
  let nextAction = '';

  const isInstUser = userRole === 'INSTITUTION_USER';
  const isOfficer = userRole === 'SCRUTINY_OFFICER' || userRole === 'BRANCH_HEAD';
  const isFinance = userRole === 'FINANCE_OFFICER';
  const isAuditor = userRole === 'AUDITOR';

  if (status === 'DRAFT') {
    currentStageNumber = hasDocuments ? 2 : 1;
    statusSummary = hasDocuments ? 'Evidence uploaded; pending final submission' : 'Initial FDR details recorded';
    if (isInstUser) {
      nextAction = hasDocuments ? 'Submit for statutory review' : 'Upload FDR certificate scan';
    } else {
      nextAction = hasDocuments ? 'Awaiting institutional submission' : 'Awaiting certificate upload by institution';
    }
  } else if (status === 'RETURNED_FOR_CORRECTION') {
    currentStageNumber = 3;
    stageStatus = 'WARNING';
    statusSummary = 'Case returned by scrutiny officer for institutional correction';
    nextAction = isInstUser
      ? 'Amend certificate details & resubmit'
      : 'Awaiting institutional correction & resubmission';
  } else if (status === 'SUBMITTED' || status === 'UNDER_SCRUTINY') {
    currentStageNumber = 3;
    if (openObservations.length > 0) {
      stageStatus = 'WARNING';
      statusSummary = `${openObservations.length} scrutiny observation(s) recorded`;
    } else {
      statusSummary = 'Under algorithmic and scrutiny officer review';
    }
    if (isOfficer) {
      nextAction = 'Examine findings in queue & record observation';
    } else if (isInstUser) {
      nextAction = 'Awaiting scrutiny officer validation outcome';
    } else if (isAuditor) {
      nextAction = 'Inspect scrutiny validation findings (read-only)';
    } else {
      nextAction = 'Review algorithmic scrutiny findings';
    }
  } else if (status === 'REGISTERED' || status === 'ACTIVE') {
    if (trust === 'L0_DECLARED') {
      currentStageNumber = 4;
      statusSummary = 'Declared status; pending officer attestation (L2) or bank verification (L3)';
      if (isOfficer) {
        nextAction = 'Dispatch bank confirmation request or record L2 decision';
      } else if (isInstUser) {
        nextAction = 'Awaiting bank confirmation / officer verification';
      } else {
        nextAction = 'Inspect trust provenance and verification status';
      }
    } else if (maturityIndicator === 'EXPIRING_SOON') {
      currentStageNumber = 5;
      stageStatus = 'WARNING';
      statusSummary = 'Approaching statutory maturity (within ≤ 90 days)';
      if (isInstUser) {
        nextAction = 'Initiate successor renewal or file release request';
      } else if (isFinance) {
        nextAction = 'Monitor reconciliation & prepare deposit accounting';
      } else {
        nextAction = 'Monitor maturity window & renewal timeline';
      }
    } else if (maturityIndicator === 'EXPIRED') {
      currentStageNumber = 6;
      stageStatus = 'WARNING';
      statusSummary = 'Matured deposit; awaiting successor renewal or release petition';
      nextAction = isInstUser
        ? 'Draft successor renewal instrument or file release request'
        : 'Track renewal continuity or release case filing';
    } else {
      currentStageNumber = 5;
      statusSummary = 'Active compliance: statutory lien marked and valid';
      nextAction = isAuditor
        ? 'Audit active lien & trust records'
        : 'Monitor periodic maturity timeline';
    }
  } else if (status === 'RENEWED' || status === 'RENEWED_SUPERSEDED') {
    currentStageNumber = 6;
    stageStatus = 'COMPLETED';
    statusSummary = 'Successfully renewed; active successor established in lineage';
    nextAction = 'View successor instrument lineage';
  } else if (status === 'RELEASED') {
    currentStageNumber = 9;
    stageStatus = 'COMPLETED';
    statusSummary = 'Deposit discharged by competent authority and verified in audit ledger';
    nextAction = isFinance
      ? 'Verify bank confirmation and account reconciliation'
      : 'Inspect permanent cryptographic audit record';
  }

  return { currentStageNumber, stageStatus, statusSummary, nextAction };
}

const PortfolioView: React.FC<PortfolioViewProps> = (props) => {
  const navigate = useNavigate();
  const { stageCounts, isLoading } = props;

    return (
      <section aria-labelledby="lifecycle-matrix-heading" className="space-y-3 font-sans">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 id="lifecycle-matrix-heading" className="text-sm font-bold text-[#0D2538] uppercase tracking-wider flex items-center gap-2">
              <span>Nine-Stage FDR Lifecycle Triage Matrix</span>
              <span className="text-[10px] font-mono font-semibold text-[#0F766E] bg-teal-50 border border-teal-200 px-2 py-0.5 rounded">
                Authoritative PRD Pipeline
              </span>
            </h2>
            <p className="text-xs text-[#5D6A75]">
              Real-time operational distribution across the statutory nine-stage deposit governance lifecycle. Click any stage to open its work queue.
            </p>
          </div>
          <div className="text-[11px] text-[#5D6A75] bg-[#F5F4EF] px-2.5 py-1 rounded border border-[#C9D3DB]">
            <span className="font-semibold text-[#253746]">Non-Linear:</span> Supports renewal loops (1–6), returned scrutiny, and direct releases.
          </div>
        </div>

        {/* 9 Stage Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-9 gap-2.5">
          {LIFECYCLE_STAGES.map((stage) => {
            const Icon = stage.icon;
            const count = stageCounts?.[stage.id] ?? 0;

            return (
              <div
                key={stage.id}
                onClick={() => navigate(stage.defaultRoute)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    navigate(stage.defaultRoute);
                  }
                }}
                tabIndex={0}
                role="button"
                aria-label={`Open stage ${stage.stageNumber}: ${stage.label}. ${count} active records.`}
                className={cn(
                  'group flex flex-col justify-between p-3 rounded-[8px] bg-white border border-[#C9D3DB] hover:border-[#0F766E] hover:shadow-xs transition-all cursor-pointer relative overflow-hidden select-none',
                  stage.stageNumber === 7 && count > 0 && 'border-amber-300 bg-amber-50/20'
                )}
              >
                {/* Top strip */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[10px] font-bold text-[#8799A9] group-hover:text-[#0F766E] transition-colors">
                      {String(stage.stageNumber).padStart(2, '0')}
                    </span>
                    <div className="p-1 rounded bg-[#F5F4EF] group-hover:bg-teal-50 text-[#5D6A75] group-hover:text-[#0F766E] transition-colors">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                  </div>

                  <h3 className="text-xs font-bold text-[#0D2538] group-hover:text-[#0F766E] transition-colors line-clamp-1">
                    {stage.label}
                  </h3>
                  <p className="text-[10px] text-[#8799A9] line-clamp-2 mt-0.5 leading-tight">
                    {stage.description}
                  </p>
                </div>

                {/* Bottom Count and Action */}
                <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between">
                  <div className="text-lg font-bold font-mono text-[#0D2538] leading-none">
                    {isLoading ? (
                      <div className="h-5 w-8 bg-slate-200 animate-pulse rounded" />
                    ) : (
                      count
                    )}
                  </div>
                  <div className="flex items-center text-[10px] font-medium text-[#0F766E] opacity-0 group-hover:opacity-100 transition-opacity">
                    <span>Queue</span>
                    <ChevronRight className="w-3 h-3 ml-0.5" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
  );
};

const InstrumentView: React.FC<InstrumentViewProps> = (props) => {
  const { user } = useAuth();
  const { instrument, snapshot, onNavigateTab, role } = props;
  const currentRole = role || user?.role;

  const evalResult = evaluateInstrumentLifecycleStage(instrument, snapshot, currentRole);

  return (
    <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-5 shadow-2xs font-sans space-y-4">
      {/* Tracker Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-[#0D2538] uppercase tracking-wider">
              Statutory Lifecycle Progress
            </span>
            <span
              className={cn(
                'text-[10px] font-mono font-semibold px-2 py-0.5 rounded',
                evalResult.stageStatus === 'WARNING'
                  ? 'bg-amber-100 text-amber-900 border border-amber-200'
                  : evalResult.stageStatus === 'COMPLETED'
                  ? 'bg-emerald-100 text-emerald-900 border border-emerald-200'
                  : 'bg-teal-50 text-teal-800 border border-teal-200'
              )}
            >
              Stage {evalResult.currentStageNumber}: {LIFECYCLE_STAGES[evalResult.currentStageNumber - 1].label}
            </span>

            {/* Separated Administrative, Trust, and Maturity Status Badges */}
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
              Admin: <strong>{instrument.status}</strong>
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
              Trust: <strong>{instrument.trust_level}</strong>
            </span>
            {instrument.maturity_indicator && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200">
                Maturity: <strong>{instrument.maturity_indicator}</strong>
              </span>
            )}
          </div>
          <p className="text-xs text-[#5D6A75] mt-1.5">
            {evalResult.statusSummary}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] text-[#5D6A75]">Next Action:</span>
          <span className="text-[11px] font-semibold text-[#0F766E] bg-teal-50 px-2.5 py-1 rounded border border-teal-200">
            {evalResult.nextAction}
          </span>
        </div>
      </div>

      {/* Horizontal Stage Timeline */}
      <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-9 gap-1.5 pt-1">
        {LIFECYCLE_STAGES.map((st) => {
          const isCurrent = st.stageNumber === evalResult.currentStageNumber;
          const isPassed = st.stageNumber < evalResult.currentStageNumber;
          const isUpcoming = st.stageNumber > evalResult.currentStageNumber;
          const Icon = st.icon;

          return (
            <div
              key={st.id}
              className={cn(
                'flex flex-col items-center p-2 rounded-[6px] text-center border transition-all text-xs',
                isCurrent && 'bg-[#123B5D] text-white border-[#0D2538] shadow-xs ring-1 ring-[#0F766E]',
                isPassed && 'bg-emerald-50 text-emerald-900 border-emerald-200',
                isUpcoming && 'bg-[#F5F4EF] text-[#8799A9] border-[#C9D3DB]'
              )}
              title={`${st.stageNumber}. ${st.label} — ${st.description}`}
            >
              <div className="flex items-center justify-center w-5 h-5 rounded-full mb-1">
                {isPassed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Icon className={cn('w-3.5 h-3.5', isCurrent ? 'text-[#8ACEC8]' : 'text-current')} />
                )}
              </div>
              <span className="font-mono text-[9px] font-bold block opacity-75">
                0{st.stageNumber}
              </span>
              <span className="font-semibold text-[10px] leading-tight line-clamp-1">
                {st.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Statutory Guardrail Notices */}
      <div className="bg-[#FEF7E8] border border-[#F8DEAE] rounded-[6px] p-2.5 flex items-start gap-2 text-[11px] text-[#8A5A00]">
        <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-[#8A5A00]" />
        <div className="leading-relaxed">
          <strong>Statutory Guardrails:</strong> (1) Uploading evidence or OCR consistency checks alone does <em>not</em> constitute genuine bank confirmation (Level 3 requires direct bank confirmation). (2) Competent Authority approval sanctions release but does <em>not</em> imply bank disbursement has completed (Stage 9 bank confirmation and closure required).
        </div>
      </div>

      <div className="text-[11px] text-[#5D6A75] flex items-center justify-between pt-1 border-t border-slate-100">
        <span>
          <strong>Note:</strong> Renewal (Stage 6) and Release (Stages 7–9) are branching paths. Deposits do not force-progress through all stages.
        </span>
        {onNavigateTab && (
          <button
            type="button"
            onClick={() => onNavigateTab('lineage')}
            className="text-[#0F766E] hover:underline font-semibold flex items-center gap-1 cursor-pointer"
          >
            <span>View Lineage Continuity</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};

export const NineStageLifecycleTracker: React.FC<NineStageLifecycleTrackerProps> = (props) => {
  if (props.mode === 'portfolio') {
    return <PortfolioView {...props} />;
  }
  return <InstrumentView {...props} />;
};
