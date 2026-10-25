import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  RefreshCw,
  BookOpen,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { commandCenterApi } from '@/api/commandCenter';
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
      ] = await Promise.allSettled([
        commandCenterApi.getStatusCounts({ window_days: windowDays }),
        commandCenterApi.getMaturityWindow({ window_days: windowDays, page_size: 15 }),
        commandCenterApi.getOverdueEscalated({ limit: 15 }),
        commandCenterApi.getVerificationQueue({ limit: 15 }),
        commandCenterApi.getDocumentCompleteness(),
        commandCenterApi.getReleaseBlockers({ limit: 15 }),
        commandCenterApi.getMaturityLoad({ calendar_year: calendarYear }),
        commandCenterApi.getPriorityQueue({ min_score: minScore, page_size: 15 }),
      ]);

      if (statusRes.status === 'fulfilled') setStatusCounts(statusRes.value);
      if (matWinRes.status === 'fulfilled') setMaturityWindow(matWinRes.value);
      if (overdueRes.status === 'fulfilled') setOverdueEscalated(overdueRes.value);
      if (verifRes.status === 'fulfilled') setVerificationQueue(verifRes.value);
      if (compRes.status === 'fulfilled') setCompleteness(compRes.value);
      if (blockRes.status === 'fulfilled') setReleaseBlockers(blockRes.value);
      if (matLoadRes.status === 'fulfilled') setMaturityLoad(matLoadRes.value);
      if (priorRes.status === 'fulfilled') setPriorityQueue(priorRes.value);

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
      {/* Top Cockpit Header */}
      <div className="bg-linear-to-r from-slate-900 via-slate-850 to-slate-900 rounded-2xl p-6 text-white shadow-lg border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="bg-sentinel-500/20 text-sentinel-300 border border-sentinel-400/30 text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">
              {isInstitutionUser ? 'Institution Command Center' : 'AICTE Bureau Executive Cockpit'}
            </span>
            <span className="text-slate-400 text-xs font-mono">Module 7 Operational Desk</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Security Deposit & FDR Command Center
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
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
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 shadow-xs transition"
          >
            <BookOpen className="w-4 h-4 text-sentinel-400" />
            <span>Metric Dictionary (PRD-FR-077)</span>
          </button>

          <button
            type="button"
            onClick={loadCommandCenterData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-sentinel-600 hover:bg-sentinel-700 text-white text-xs font-medium rounded-lg shadow-xs transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Refreshing...' : 'Refresh Live Data'}</span>
          </button>
        </div>
      </div>

      {/* Error Banner with Retry */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start justify-between gap-3 text-xs">
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
            className="px-3 py-1 bg-white border border-rose-300 rounded font-semibold text-rose-800 hover:bg-rose-100 shrink-0"
          >
            Retry Aggregation
          </button>
        </div>
      )}

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
