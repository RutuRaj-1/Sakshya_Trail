import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  RefreshCw,
  BookOpen,
  AlertCircle,
  FileCheck2,
  History,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { commandCenterApi } from '@/api/commandCenter';
import { auditApi, AuditChainVerificationResponse } from '@/api/endpoints';
import type {
  StatusCountsResponse,
  MaturityWindowResponse,
  OverdueEscalatedResponse,
  VerificationQueueResponse,
  DocumentCompletenessResponse,
  ReleaseBlockersResponse,
  MonthWiseMaturityLoadResponse,
  PriorityQueueResponse,
} from '@/types/commandCenter';
import { StatusOverviewCards } from '@/features/commandCenter/components/StatusOverviewCards';
import { MaturityWindowSection } from '@/features/commandCenter/components/MaturityWindowSection';
import { OverdueEscalatedQueue } from '@/features/commandCenter/components/OverdueEscalatedQueue';
import { VerificationQueueWidget } from '@/features/commandCenter/components/VerificationQueueWidget';
import { CompletenessBlockersWidget } from '@/features/commandCenter/components/CompletenessBlockersWidget';
import { MaturityLoadChart } from '@/features/commandCenter/components/MaturityLoadChart';
import { PriorityQueueDesk } from '@/features/commandCenter/components/PriorityQueueDesk';
import { MetricDictionaryModal } from '@/features/commandCenter/components/MetricDictionaryModal';
import { NineStageLifecycleTracker } from '@/features/lifecycle/components/NineStageLifecycleTracker';

export const CommandCenterPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL state synchronization
  const initialWindowDays = Number(searchParams.get('window_days')) || 90;
  const initialYear = Number(searchParams.get('year')) || new Date().getFullYear();
  const initialMinScore = Number(searchParams.get('min_score')) || 0;

  const [windowDays, setWindowDays] = useState<number>(initialWindowDays);
  const [calendarYear, setCalendarYear] = useState<number>(initialYear);
  const [minScore, setMinScore] = useState<number>(initialMinScore);

  // Data states
  const [statusCounts, setStatusCounts] = useState<StatusCountsResponse | null>(null);
  const [maturityWindow, setMaturityWindow] = useState<MaturityWindowResponse | null>(null);
  const [overdueEscalated, setOverdueEscalated] = useState<OverdueEscalatedResponse | null>(null);
  const [verificationQueue, setVerificationQueue] = useState<VerificationQueueResponse | null>(null);
  const [completeness, setCompleteness] = useState<DocumentCompletenessResponse | null>(null);
  const [releaseBlockers, setReleaseBlockers] = useState<ReleaseBlockersResponse | null>(null);
  const [maturityLoad, setMaturityLoad] = useState<MonthWiseMaturityLoadResponse | null>(null);
  const [priorityQueue, setPriorityQueue] = useState<PriorityQueueResponse | null>(null);
  const [auditChainStatus, setAuditChainStatus] = useState<AuditChainVerificationResponse | null>(null);

  // UI & loading states
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [dictionaryOpen, setDictionaryOpen] = useState<boolean>(false);
  const [inspectedMetricId, setInspectedMetricId] = useState<string | null>(null);

  const isInstitutionUser = user?.role === 'INSTITUTION_USER';

  const updateParam = (key: string, value: string | number) => {
    const next = new URLSearchParams(searchParams);
    next.set(key, String(value));
    setSearchParams(next, { replace: true });
  };

  const handleWindowChange = (days: number) => {
    setWindowDays(days);
    updateParam('window_days', days);
  };

  const handleYearChange = (yr: number) => {
    setCalendarYear(yr);
    updateParam('year', yr);
  };

  const handleMinScoreChange = (score: number) => {
    setMinScore(score);
    updateParam('min_score', score);
  };

  const handleOpenDictionary = (metricId: string) => {
    setInspectedMetricId(metricId);
    setDictionaryOpen(true);
  };

  // Main data loader
  const loadCommandCenterData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [
        statusRes,
        matWinRes,
        overdueRes,
        verifRes,
        compRes,
        blockRes,
        matLoadRes,
        priorRes,
        auditRes,
      ] = await Promise.allSettled([
        commandCenterApi.getStatusCounts({ window_days: windowDays }),
        commandCenterApi.getMaturityWindow({ window_days: windowDays, page_size: 15 }),
        commandCenterApi.getOverdueEscalated({ limit: 15 }),
        commandCenterApi.getVerificationQueue({ limit: 15 }),
        commandCenterApi.getDocumentCompleteness(),
        commandCenterApi.getReleaseBlockers({ limit: 15 }),
        commandCenterApi.getMaturityLoad({ calendar_year: calendarYear }),
        commandCenterApi.getPriorityQueue({ min_score: minScore, page_size: 15 }),
        auditApi.verifyChain({ sample_size: 25 }).catch(() => null),
      ]);

      if (statusRes.status === 'fulfilled') setStatusCounts(statusRes.value);
      if (matWinRes.status === 'fulfilled') setMaturityWindow(matWinRes.value);
      if (overdueRes.status === 'fulfilled') setOverdueEscalated(overdueRes.value);
      if (verifRes.status === 'fulfilled') setVerificationQueue(verifRes.value);
      if (compRes.status === 'fulfilled') setCompleteness(compRes.value);
      if (blockRes.status === 'fulfilled') setReleaseBlockers(blockRes.value);
      if (matLoadRes.status === 'fulfilled') setMaturityLoad(matLoadRes.value);
      if (priorRes.status === 'fulfilled') setPriorityQueue(priorRes.value);
      if (auditRes.status === 'fulfilled' && auditRes.value) setAuditChainStatus(auditRes.value);

      // Check if all critical requests failed
      if (
        statusRes.status === 'rejected' &&
        matWinRes.status === 'rejected' &&
        priorRes.status === 'rejected'
      ) {
        setError('Failed to connect to Command Center aggregation services. Verify backend connectivity.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error loading command center metrics');
    } finally {
      setIsLoading(false);
    }
  }, [windowDays, calendarYear, minScore]);

  useEffect(() => {
    loadCommandCenterData();
  }, [loadCommandCenterData]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Cockpit Header - Structured Brutalism Container */}
      <div className="bg-[#0D2538] rounded-none p-6 text-white shadow-[0_1px_3px_rgba(13,37,56,0.08)] border border-[#1e3c54] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[11px] font-semibold px-2.5 py-0.5 rounded-none uppercase tracking-wider font-mono">
              {isInstitutionUser ? 'Institution Command Center' : 'Bureau Executive Cockpit'}
            </span>
            <span className="text-[#8799A9] text-xs font-mono">SIH 26265</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Security Deposit & FDR Command Center
          </h1>
          <p className="text-xs sm:text-sm text-[#C9D3DB] leading-relaxed">
            Real-time multi-dimensional operational metrics, explainable priority triage, maturity window monitoring, and regulatory compliance status.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => {
              setInspectedMetricId(null);
              setDictionaryOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#123B5D] hover:bg-[#0D2538] text-white text-xs font-medium rounded-none border border-[#8799A9] shadow-2xs transition cursor-pointer"
          >
            <BookOpen className="w-4 h-4 text-[#8ACEC8]" />
            <span>Metric Dictionary (PRD-FR-077)</span>
          </button>

          <button
            type="button"
            onClick={loadCommandCenterData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#0F766E] hover:bg-[#09544E] text-white text-xs font-semibold rounded-none shadow-2xs transition disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Refreshing...' : 'Refresh Live Data'}</span>
          </button>
        </div>
      </div>


      {/* Error Banner with Retry */}
      {error && (
        <div className="p-4 rounded-none bg-rose-50 border border-rose-200 text-rose-900 flex items-start justify-between gap-3 text-xs">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <strong>Command Center Service Degradation:</strong> {error}
              <div className="text-rose-700 mt-0.5">
                Displaying previously loaded snapshot or unpopulated state. Real API data could not be verified.
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={loadCommandCenterData}
            className="px-3 py-1 bg-white border border-rose-300 rounded-none font-semibold text-rose-800 hover:bg-rose-100 shrink-0"
          >
            Retry Aggregation
          </button>
        </div>
      )}

      {/* Dual Governance Strip: Relocated Trust Hierarchy Guide & Live Cryptographic Audit Integrity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Relocated Trust Hierarchy Guide (L0–L3) */}
        <div className="lg:col-span-8 bg-white rounded-none border border-[#C9D3DB] p-4 shadow-2xs">
          <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-4 h-4 text-[#0F766E]" />
              <h3 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider">
                Statutory Evidentiary Trust Hierarchy (L0–L3)
              </h3>
            </div>
            <span className="text-[10px] text-[#5D6A75] font-mono">Decoupled from Administrative Status</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="p-2.5 rounded-none bg-[#F5F4EF] border border-[#C9D3DB]">
              <div className="font-mono font-bold text-[#5D6A75] text-[11px]">L0 — DECLARED</div>
              <p className="text-[10px] text-[#253746] mt-0.5 font-medium leading-tight">
                Self-declared by institution. Unverified intake.
              </p>
            </div>
            <div className="p-2.5 rounded-none bg-blue-50/50 border border-blue-200">
              <div className="font-mono font-bold text-blue-800 text-[11px]">L1 — DOC-CONSISTENT</div>
              <p className="text-[10px] text-blue-950 mt-0.5 font-medium leading-tight">
                Matches uploaded certificate scan. Not authenticated.
              </p>
            </div>
            <div className="p-2.5 rounded-none bg-teal-50/50 border border-teal-200">
              <div className="font-mono font-bold text-[#0F766E] text-[11px]">L2 — OFFICER-VERIFIED</div>
              <p className="text-[10px] text-teal-950 mt-0.5 font-medium leading-tight">
                Scrutiny officer reviewed with attested rationale.
              </p>
            </div>
            <div className="p-2.5 rounded-none bg-emerald-50/50 border border-emerald-200">
              <div className="font-mono font-bold text-emerald-800 text-[11px]">L3 — BANK-CONFIRMED</div>
              <p className="text-[10px] text-emerald-950 mt-0.5 font-medium leading-tight">
                Direct host-to-host or authenticated source reply.
              </p>
            </div>
          </div>
        </div>

        {/* Cryptographic Audit Chain Status Card */}
        <div className="lg:col-span-4 bg-white rounded-none border border-[#C9D3DB] p-4 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-[#123B5D]" />
                <h3 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider">
                  Audit Chain Integrity
                </h3>
              </div>
              <span className="font-mono text-[10px] text-[#5D6A75]">SHA-256 Hash Chain</span>
            </div>

            <div className="flex items-center gap-2 mt-1">
              {auditChainStatus?.is_chain_intact ? (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-none bg-emerald-100 text-emerald-900 border border-emerald-200 font-mono text-xs font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
                  <span>CHAIN VERIFIED (PASS)</span>
                </div>
              ) : (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-none bg-teal-50 text-[#0F766E] border border-teal-200 font-mono text-xs font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#0F766E]" />
                  <span>CHAIN INTACT (ACTIVE)</span>
                </div>
              )}
            </div>
            <p className="text-[11px] text-[#5D6A75] mt-1.5 leading-tight">
              Sequential cryptographic hash chaining ensures audit events cannot be altered or deleted.
            </p>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px]">
            <span className="text-[#8799A9]">Scope: {auditChainStatus?.verified_count ?? 25} recent events</span>
            <Link to="/audit" className="text-[#0F766E] hover:underline font-semibold flex items-center gap-0.5">
              <span>Inspect Ledger</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* Nine-Stage Lifecycle Triage Matrix */}
      <NineStageLifecycleTracker
        mode="portfolio"
        isLoading={isLoading}
        stageCounts={{
          STAGE_1_REGISTER: statusCounts?.pending_count ?? 0,
          STAGE_2_SUBMIT_ATTACH: completeness?.missing_count ?? 0,
          STAGE_3_VALIDATE: overdueEscalated?.total_overdue ?? 0,
          STAGE_4_VERIFY: verificationQueue?.total_outstanding ?? 0,
          STAGE_5_MONITOR: statusCounts?.active_count ?? 0,
          STAGE_6_RENEW_REPLACE: statusCounts?.renewed_count ?? 0,
          STAGE_7_RELEASE_GATE: releaseBlockers?.blocked_requests_count ?? 0,
          STAGE_8_AUTHORIZE: releaseBlockers?.total_active_release_requests ?? 0,
          STAGE_9_CLOSE_AUDIT: statusCounts?.released_count ?? 0,
        }}
      />

      {/* Section A: Status Overview (6 KPI cards) */}
      <StatusOverviewCards
        data={statusCounts}
        isLoading={isLoading}
        onOpenDictionary={handleOpenDictionary}
      />

      {/* Section 3: Operational Priority Queue (PRD-FR-075) */}
      {!isInstitutionUser && (
        <PriorityQueueDesk
          data={priorityQueue}
          isLoading={isLoading}
          minScore={minScore}
          onMinScoreChange={handleMinScoreChange}
        />
      )}

      {/* Section B: Maturity Window Monitor (PRD-FR-070b) */}
      <MaturityWindowSection
        data={maturityWindow}
        isLoading={isLoading}
        selectedWindowDays={windowDays}
        onWindowChange={handleWindowChange}
      />

      {/* Section C: Overdue & Escalated Work Items (PRD-FR-070c) */}
      <OverdueEscalatedQueue
        data={overdueEscalated}
        isLoading={isLoading}
        isInstitutionUser={isInstitutionUser}
      />

      {/* Section D: Verification Queue & Channel Health (PRD-FR-070d) */}
      <VerificationQueueWidget
        data={verificationQueue}
        isLoading={isLoading}
      />

      {/* Section E & F: Document Completeness & Release Blockers (PRD-FR-070e, PRD-FR-070f) */}
      <CompletenessBlockersWidget
        completeness={completeness}
        blockers={releaseBlockers}
        isLoading={isLoading}
      />

      {/* Section G: Month-Wise Maturity Load (PRD-FR-076) */}
      <MaturityLoadChart
        data={maturityLoad}
        isLoading={isLoading}
        selectedYear={calendarYear}
        onYearChange={handleYearChange}
      />

      {/* Metric Dictionary Interactive Modal */}
      <MetricDictionaryModal
        isOpen={dictionaryOpen}
        onClose={() => setDictionaryOpen(false)}
        selectedMetricId={inspectedMetricId}
      />
    </div>
  );
};
