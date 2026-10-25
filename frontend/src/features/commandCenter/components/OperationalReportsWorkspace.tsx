import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet,
  FileText,
  Download,
  AlertTriangle,
  Clock,
  ShieldCheck,
  ExternalLink,
  RefreshCw,
  SlidersHorizontal,
  FileCheck2,
  AlertCircle,
  Eye,
  Info,
  Calendar,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { commandCenterApi, type ReportQueryParams } from '@/api/commandCenter';
import type {
  PendingVerificationReportResponse,
  UpcomingMaturitiesReportResponse,
  MissingDocumentsReportResponse,
  InterventionsReportResponse,
  AuditEvidencePackResponse,
} from '@/types/commandCenter';

type ReportTab = 'PENDING_VERIFICATION' | 'UPCOMING_MATURITIES' | 'MISSING_DOCUMENTS' | 'INTERVENTIONS';

export const OperationalReportsWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Role permissions
  const canExport = [
    'SYSTEM_ADMIN',
    'SCRUTINY_OFFICER',
    'AUDITOR',
    'BRANCH_HEAD',
    'COMPETENT_AUTHORITY',
    'FINANCE_OFFICER',
  ].includes(user?.role || '');

  // Active Report Tab
  const [activeTab, setActiveTab] = useState<ReportTab>('PENDING_VERIFICATION');

  // Filter States
  const [windowDays, setWindowDays] = useState<number>(90);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [bankName, setBankName] = useState<string>('');
  const [assignedOffice, setAssignedOffice] = useState<string>('');
  const [trustLevel, setTrustLevel] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [verificationStatus, setVerificationStatus] = useState<string>('');
  const [checklistOutcome, setChecklistOutcome] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [interventionType, setInterventionType] = useState<string>('');

  // Data States
  const [pendingData, setPendingData] = useState<PendingVerificationReportResponse | null>(null);
  const [maturitiesData, setMaturitiesData] = useState<UpcomingMaturitiesReportResponse | null>(null);
  const [missingDocsData, setMissingDocsData] = useState<MissingDocumentsReportResponse | null>(null);
  const [interventionsData, setInterventionsData] = useState<InterventionsReportResponse | null>(null);

  // Evidence Pack Modal State
  const [evidencePackLoading, setEvidencePackLoading] = useState<boolean>(false);
  const [evidencePackData, setEvidencePackData] = useState<AuditEvidencePackResponse | null>(null);
  const [showEvidenceModal, setShowEvidenceModal] = useState<boolean>(false);

  // Loading & Exporting States
  const [loading, setLoading] = useState<boolean>(false);
  const [exportingCsv, setExportingCsv] = useState<boolean>(false);
  const [exportingPdf, setExportingPdf] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Build current query parameters
  const getQueryParams = useCallback((): ReportQueryParams => {
    return {
      window_days: windowDays,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      bank_name: bankName || undefined,
      assigned_office: assignedOffice || undefined,
      trust_level: trustLevel || undefined,
      status: statusFilter || undefined,
      verification_status: verificationStatus || undefined,
      checklist_outcome: checklistOutcome || undefined,
      severity: severityFilter || undefined,
      intervention_type: interventionType || undefined,
    };
  }, [
    windowDays,
    dateFrom,
    dateTo,
    bankName,
    assignedOffice,
    trustLevel,
    statusFilter,
    verificationStatus,
    checklistOutcome,
    severityFilter,
    interventionType,
  ]);

  // Fetch Report Data on Tab or Filter Change
  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = getQueryParams();

    try {
      if (activeTab === 'PENDING_VERIFICATION') {
        const res = await commandCenterApi.getPendingVerificationReport(params);
        setPendingData(res);
      } else if (activeTab === 'UPCOMING_MATURITIES') {
        const res = await commandCenterApi.getUpcomingMaturitiesReport(params);
        setMaturitiesData(res);
      } else if (activeTab === 'MISSING_DOCUMENTS') {
        const res = await commandCenterApi.getMissingDocumentsReport(params);
        setMissingDocsData(res);
      } else if (activeTab === 'INTERVENTIONS') {
        const res = await commandCenterApi.getInterventionsReport(params);
        setInterventionsData(res);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate operational report.');
    } finally {
      setLoading(false);
    }
  }, [activeTab, getQueryParams]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Reset Filters
  const handleResetFilters = () => {
    setWindowDays(90);
    setDateFrom('');
    setDateTo('');
    setBankName('');
    setAssignedOffice('');
    setTrustLevel('');
    setStatusFilter('');
    setVerificationStatus('');
    setChecklistOutcome('');
    setSeverityFilter('');
    setInterventionType('');
  };

  // Export Handlers
  const handleExportCsv = async () => {
    if (!canExport) return;
    setExportingCsv(true);
    try {
      await commandCenterApi.downloadReportCsv(activeTab, getQueryParams());
    } catch (err: any) {
      alert(`CSV Export Failed: ${err.message}`);
    } finally {
      setExportingCsv(false);
    }
  };

  const handleExportPdf = async () => {
    if (!canExport) return;
    setExportingPdf(true);
    try {
      await commandCenterApi.downloadReportPdf(activeTab, getQueryParams());
    } catch (err: any) {
      alert(`PDF Export Failed: ${err.message}`);
    } finally {
      setExportingPdf(false);
    }
  };

  // Open Evidence Pack Modal
  const handleOpenEvidencePack = async (instrumentId: string) => {
    setEvidencePackLoading(true);
    setShowEvidenceModal(true);
    try {
      const data = await commandCenterApi.getAuditEvidencePack(instrumentId);
      setEvidencePackData(data);
    } catch (err: any) {
      alert(`Failed to load evidence pack: ${err.message}`);
      setShowEvidenceModal(false);
    } finally {
      setEvidencePackLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#0D2538] border border-[#1e3c54] p-6 rounded-[10px] shadow-lg">
        <div>
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-6 h-6 text-[#0F766E]" />
            <h1 className="text-2xl font-bold text-white tracking-tight">Operational Reports Workspace</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Official operational intelligence, compliance drill-down, and regulatory export desk (PRD-FR-074).
          </p>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCsv}
            disabled={!canExport || exportingCsv || loading}
            title={canExport ? 'Export filtered report as secure CSV' : 'Export permission required (Officer/Auditor/Admin)'}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm ${
              canExport
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 hover:border-slate-600'
                : 'bg-slate-900 text-slate-600 border border-slate-800 cursor-not-allowed'
            }`}
          >
            {exportingCsv ? <RefreshCw className="w-4 h-4 animate-spin text-[#0F766E]" /> : <Download className="w-4 h-4" />}
            <span>Export CSV</span>
          </button>

          <button
            onClick={handleExportPdf}
            disabled={!canExport || exportingPdf || loading}
            title={canExport ? 'Export official compliance PDF' : 'Export permission required (Officer/Auditor/Admin)'}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all shadow-sm ${
              canExport
                ? 'bg-[#0F766E] hover:bg-[#09544E] text-white shadow-sentinel-950/40'
                : 'bg-slate-900 text-slate-600 border border-slate-800 cursor-not-allowed'
            }`}
          >
            {exportingPdf ? <RefreshCw className="w-4 h-4 animate-spin text-white" /> : <FileText className="w-4 h-4" />}
            <span>Export PDF</span>
          </button>
        </div>
      </div>

      {/* Tabs Selector */}
      <div className="flex border-b border-[#C9D3DB] space-x-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('PENDING_VERIFICATION')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
            activeTab === 'PENDING_VERIFICATION'
              ? 'border-[#0F766E] text-[#0F766E] bg-[#EEF6FA]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538] hover:bg-[#F5F4EF]'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Pending Verification</span>
          {pendingData && (
            <span className="ml-1.5 px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-300 font-mono">
              {pendingData.total_records}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('UPCOMING_MATURITIES')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
            activeTab === 'UPCOMING_MATURITIES'
              ? 'border-[#0F766E] text-[#0F766E] bg-[#EEF6FA]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538] hover:bg-[#F5F4EF]'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Upcoming Maturities</span>
          {maturitiesData && (
            <span className="ml-1.5 px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-300 font-mono">
              {maturitiesData.total_records}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('MISSING_DOCUMENTS')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
            activeTab === 'MISSING_DOCUMENTS'
              ? 'border-[#0F766E] text-[#0F766E] bg-[#EEF6FA]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538] hover:bg-[#F5F4EF]'
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          <span>Missing Documents</span>
          {missingDocsData && (
            <span className="ml-1.5 px-2 py-0.5 text-xs rounded-full bg-slate-800 text-slate-300 font-mono">
              {missingDocsData.total_records}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('INTERVENTIONS')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
            activeTab === 'INTERVENTIONS'
              ? 'border-[#0F766E] text-[#0F766E] bg-[#EEF6FA]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538] hover:bg-[#F5F4EF]'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Interventions Required</span>
          {interventionsData && (
            <span className="ml-1.5 px-2 py-0.5 text-xs rounded-full bg-amber-950/60 text-amber-300 border border-amber-800/60 font-mono">
              {interventionsData.total_records}
            </span>
          )}
        </button>
      </div>

      {/* Filter Control Bar */}
      <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-[10px] space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-300 text-sm font-semibold">
            <SlidersHorizontal className="w-4 h-4 text-[#0F766E]" />
            <span>Operational Filter Criteria</span>
          </div>
          <button
            onClick={handleResetFilters}
            className="text-xs text-[#0F766E] hover:text-sentinel-300 underline font-mono"
          >
            Reset Filters
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {/* Window / Date Range */}
          {activeTab === 'UPCOMING_MATURITIES' && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Window Range</label>
                <select
                  value={windowDays}
                  onChange={(e) => setWindowDays(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
                >
                  <option value={30}>Next 30 Days</option>
                  <option value={60}>Next 60 Days</option>
                  <option value={90}>Next 90 Days</option>
                  <option value={180}>Next 180 Days</option>
                  <option value={365}>Next 365 Days</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">From Date</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">To Date</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
                />
              </div>
            </>
          )}

          {/* Bank Name */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Bank Name</label>
            <input
              type="text"
              placeholder="Filter by bank..."
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500 placeholder-slate-600"
            />
          </div>

          {/* Assigned Office */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Assigned Office</label>
            <input
              type="text"
              placeholder="e.g. Western Regional..."
              value={assignedOffice}
              onChange={(e) => setAssignedOffice(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500 placeholder-slate-600"
            />
          </div>

          {/* Trust Level */}
          {(activeTab === 'PENDING_VERIFICATION' || activeTab === 'UPCOMING_MATURITIES') && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Trust Level</label>
              <select
                value={trustLevel}
                onChange={(e) => setTrustLevel(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
              >
                <option value="">All Trust Levels</option>
                <option value="L0_DECLARED">L0 - Declared</option>
                <option value="L1_DOCUMENT_CONSISTENT">L1 - Document Consistent</option>
                <option value="L2_OFFICER_VERIFIED">L2 - Officer Verified</option>
                <option value="L3_BANK_CONFIRMED">L3 - Bank Confirmed</option>
              </select>
            </div>
          )}

          {/* Verification Status */}
          {activeTab === 'PENDING_VERIFICATION' && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Verification Status</label>
              <select
                value={verificationStatus}
                onChange={(e) => setVerificationStatus(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
              >
                <option value="">All Statuses</option>
                <option value="PENDING">Pending</option>
                <option value="NOT_SUBMITTED">Never Submitted</option>
                <option value="TIMEOUT">Timed Out</option>
                <option value="SOURCE_UNAVAILABLE">Source Unavailable</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>
          )}

          {/* Checklist Outcome */}
          {activeTab === 'MISSING_DOCUMENTS' && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Checklist Outcome</label>
              <select
                value={checklistOutcome}
                onChange={(e) => setChecklistOutcome(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
              >
                <option value="">All Outcomes</option>
                <option value="MISSING">Missing Document</option>
                <option value="UNREADABLE">Unreadable / Corrupt Scan</option>
                <option value="WRONG_CATEGORY">Wrong Category</option>
                <option value="AWAITING_CONFIRMATION">Awaiting Confirmation</option>
              </select>
            </div>
          )}

          {/* Severity Filter */}
          {(activeTab === 'MISSING_DOCUMENTS' || activeTab === 'INTERVENTIONS') && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Severity</label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          )}

          {/* Intervention Type */}
          {activeTab === 'INTERVENTIONS' && (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Intervention Type</label>
              <select
                value={interventionType}
                onChange={(e) => setInterventionType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sentinel-500"
              >
                <option value="">All Types</option>
                <option value="OVERDUE_ESCALATION">Overdue & Escalated</option>
                <option value="UNRESOLVED_DISCREPANCY">Unresolved Discrepancy</option>
                <option value="VERIFICATION_FAILED">Verification Failed / Unavailable</option>
                <option value="RELEASE_BLOCKER">Release Blockers</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Active Filter Criteria Summary Bar */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-2">
        <div className="flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-[#0F766E]" />
          <span>
            Showing records scoped by server-side tenancy. Export generation timestamp and applied filters are sealed in export headers.
          </span>
        </div>
        {loading && (
          <div className="flex items-center gap-1.5 text-[#0F766E]">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Querying verified records...</span>
          </div>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-800/80 rounded-[10px] text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <div>{error}</div>
        </div>
      )}

      {/* =========================================================================
          REPORT VIEW A: PENDING VERIFICATION
         ========================================================================= */}
      {activeTab === 'PENDING_VERIFICATION' && (
        <div className="bg-slate-900 border border-slate-800 rounded-[10px] overflow-hidden shadow-lg">
          <div className="p-4 border-b border-[#C9D3DB] flex items-center justify-between bg-slate-950/40">
            <div>
              <h2 className="text-base font-semibold text-white">Pending Electronic Verification Report</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Authorized instruments awaiting live bank or gateway confirmation. Explicitly distinguishes simulated vs live channels.
              </p>
            </div>
            {pendingData && (
              <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                {pendingData.total_records} Pending Instruments
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono tracking-wider border-b border-[#C9D3DB]">
                <tr>
                  <th className="py-3 px-4">Instrument Reference</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Bank & Branch</th>
                  <th className="py-3 px-4">Verification Status</th>
                  <th className="py-3 px-4">Channel Mode</th>
                  <th className="py-3 px-4">Pending Age</th>
                  <th className="py-3 px-4">Assigned Office</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {pendingData?.rows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500 italic">
                      No pending verification requests matching filter criteria.
                    </td>
                  </tr>
                ) : (
                  pendingData?.rows.map((row) => (
                    <tr key={row.instrument_id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-sentinel-300">
                        {row.reference_number}
                        {row.discrepancy_count > 0 && (
                          <span className="ml-2 px-1.5 py-0.2 text-[10px] bg-rose-950 text-rose-300 border border-rose-800 rounded">
                            {row.discrepancy_count} disc
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-200">
                        {row.institution_name || row.institution_id}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-slate-200">{row.bank_name}</div>
                        <div className="text-slate-500 text-[11px]">{row.branch || '—'}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                            row.verification_status === 'PENDING'
                              ? 'bg-amber-950 text-amber-300 border border-amber-800'
                              : row.verification_status === 'SOURCE_UNAVAILABLE'
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : row.verification_status === 'TIMEOUT'
                              ? 'bg-red-950 text-red-300 border border-red-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {row.verification_status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {row.is_simulated ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-yellow-950/80 text-yellow-300 border border-yellow-700/60">
                            SIMULATED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                            LIVE ({row.channel})
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {row.pending_age_days} days
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {row.assigned_office || 'Unassigned'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenEvidencePack(row.instrument_id)}
                            className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200"
                            title="Audit Evidence Pack"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => navigate(row.drill_down_path)}
                            className="flex items-center gap-1 text-[#0F766E] hover:text-sentinel-300 font-medium text-xs ml-1"
                          >
                            <span>Inspect</span>
                            <ExternalLink className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =========================================================================
          REPORT VIEW B: UPCOMING MATURITIES
         ========================================================================= */}
      {activeTab === 'UPCOMING_MATURITIES' && (
        <div className="space-y-4">
          {/* Statutory Notice Callout */}
          <div className="p-4 bg-blue-950/30 border border-blue-900/60 rounded-[10px] flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
            <div className="text-xs text-blue-200 leading-relaxed">
              <span className="font-semibold text-blue-100">Statutory Notice:</span> Approaching calendar maturity does not equate to release eligibility. Replacement instruments must be separately verified and validated prior to encashment or discharge authorization.
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-[10px] overflow-hidden shadow-lg">
            <div className="p-4 border-b border-[#C9D3DB] flex items-center justify-between bg-slate-950/40">
              <div>
                <h2 className="text-base font-semibold text-white">Upcoming Deposit Maturities Report</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Consistent with Command Center maturity definitions and date basis. Tracks linked renewals.
                </p>
              </div>
              {maturitiesData && (
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                    Total Deposit: ₹{Number(maturitiesData.total_deposit_value).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="text-xs font-mono text-sentinel-300 bg-sentinel-950 px-2.5 py-1 rounded border border-sentinel-800">
                    {maturitiesData.total_records} Records
                  </span>
                </div>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono tracking-wider border-b border-[#C9D3DB]">
                  <tr>
                    <th className="py-3 px-4">Instrument Reference</th>
                    <th className="py-3 px-4">Institution</th>
                    <th className="py-3 px-4">Bank</th>
                    <th className="py-3 px-4">Amount (INR)</th>
                    <th className="py-3 px-4">Maturity Date</th>
                    <th className="py-3 px-4">Days Left</th>
                    <th className="py-3 px-4">Trust Level</th>
                    <th className="py-3 px-4">Renewal Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {maturitiesData?.rows.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-500 italic">
                        No upcoming maturities found within the selected window.
                      </td>
                    </tr>
                  ) : (
                    maturitiesData?.rows.map((row) => (
                      <tr key={row.instrument_id} className="hover:bg-slate-800/50 transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-sentinel-300">
                          {row.reference_number}
                        </td>
                        <td className="py-3 px-4 text-slate-200">
                          {row.institution_name || row.institution_id}
                        </td>
                        <td className="py-3 px-4 text-slate-300">{row.bank_name}</td>
                        <td className="py-3 px-4 font-mono font-medium text-slate-100">
                          ₹{Number(row.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">{row.maturity_date}</td>
                        <td className="py-3 px-4 font-mono font-bold">
                          <span
                            className={
                              row.days_to_maturity < 0
                                ? 'text-rose-400'
                                : row.days_to_maturity <= 30
                                ? 'text-amber-400'
                                : 'text-slate-300'
                            }
                          >
                            {row.days_to_maturity < 0 ? `${Math.abs(row.days_to_maturity)}d overdue` : `${row.days_to_maturity}d`}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                            {row.trust_level}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                              row.renewal_status === 'RENEWAL_LINKED'
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {row.renewal_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleOpenEvidencePack(row.instrument_id)}
                              className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200"
                              title="Audit Evidence Pack"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => navigate(row.drill_down_path)}
                              className="flex items-center gap-1 text-[#0F766E] hover:text-sentinel-300 font-medium text-xs ml-1"
                            >
                              <span>Inspect</span>
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          REPORT VIEW C: MISSING DOCUMENTS
         ========================================================================= */}
      {activeTab === 'MISSING_DOCUMENTS' && (
        <div className="bg-slate-900 border border-slate-800 rounded-[10px] overflow-hidden shadow-lg">
          <div className="p-4 border-b border-[#C9D3DB] flex items-center justify-between bg-slate-950/40">
            <div>
              <h2 className="text-base font-semibold text-white">Missing & Non-Compliant Documents Report</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Cases with missing, unreadable, wrong-category, or awaiting-confirmation checklist items against versioned policies.
              </p>
            </div>
            {missingDocsData && (
              <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                {missingDocsData.total_records} Non-Compliant Findings
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono tracking-wider border-b border-[#C9D3DB]">
                <tr>
                  <th className="py-3 px-4">Instrument Reference</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Document Category</th>
                  <th className="py-3 px-4">Checklist Outcome</th>
                  <th className="py-3 px-4">Policy Ver</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Finding Summary</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {missingDocsData?.rows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500 italic">
                      All checklist documents fully satisfied for the queried criteria.
                    </td>
                  </tr>
                ) : (
                  missingDocsData?.rows.map((row) => (
                    <tr key={row.finding_id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-sentinel-300">
                        {row.reference_number}
                      </td>
                      <td className="py-3 px-4 text-slate-200">
                        {row.institution_name || row.institution_id}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {row.document_category}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                            row.checklist_outcome === 'MISSING'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}
                        >
                          {row.checklist_outcome}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        v{row.policy_version}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                            row.severity === 'HIGH' || row.severity === 'CRITICAL'
                              ? 'bg-red-950 text-red-300 border border-red-800'
                              : 'bg-yellow-950 text-yellow-300 border border-yellow-800'
                          }`}
                        >
                          {row.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300 max-w-xs truncate" title={row.finding_title}>
                        {row.finding_title}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => navigate(row.drill_down_path)}
                          className="flex items-center gap-1 text-[#0F766E] hover:text-sentinel-300 font-medium text-xs ml-auto"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =========================================================================
          REPORT VIEW D: INTERVENTIONS REQUIRED
         ========================================================================= */}
      {activeTab === 'INTERVENTIONS' && (
        <div className="bg-slate-900 border border-slate-800 rounded-[10px] overflow-hidden shadow-lg">
          <div className="p-4 border-b border-[#C9D3DB] flex items-center justify-between bg-slate-950/40">
            <div>
              <h2 className="text-base font-semibold text-white">Operational Interventions Report</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Cases requiring immediate officer follow-up: overdue renewals, escalations, discrepancy blockers, and failed sources. Neutral terminology applied.
              </p>
            </div>
            {interventionsData && (
              <span className="text-xs font-mono text-amber-400 bg-amber-950/60 px-2.5 py-1 rounded border border-amber-800/80">
                {interventionsData.total_records} Intervention Items
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-mono tracking-wider border-b border-[#C9D3DB]">
                <tr>
                  <th className="py-3 px-4">Intervention Type</th>
                  <th className="py-3 px-4">Reference</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Reason / Anomaly</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Age / Deadline</th>
                  <th className="py-3 px-4">Next Recommended Action</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {interventionsData?.rows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500 italic">
                      No cases requiring intervention matching selected criteria.
                    </td>
                  </tr>
                ) : (
                  interventionsData?.rows.map((row, idx) => (
                    <tr key={`${row.entity_id}-${idx}`} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-4 font-mono font-semibold">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] ${
                            row.intervention_type === 'OVERDUE_ESCALATION'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : row.intervention_type === 'RELEASE_BLOCKER'
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}
                        >
                          {row.intervention_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-sentinel-300">
                        {row.reference_number}
                      </td>
                      <td className="py-3 px-4 text-slate-200">
                        {row.institution_name || row.institution_id}
                      </td>
                      <td className="py-3 px-4 text-slate-300 max-w-xs leading-tight">
                        {row.reason_description}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            row.severity === 'CRITICAL'
                              ? 'bg-red-950 text-red-300 border border-red-800'
                              : row.severity === 'HIGH'
                              ? 'bg-orange-950 text-orange-300 border border-orange-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {row.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {row.age_days > 0 ? `${row.age_days}d age` : '—'}
                      </td>
                      <td className="py-3 px-4 text-slate-400 italic text-[11px] max-w-xs">
                        {row.next_appropriate_action}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => navigate(row.drill_down_path)}
                          className="flex items-center gap-1 text-[#0F766E] hover:text-sentinel-300 font-medium text-xs ml-auto"
                        >
                          <span>Review</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: AUDIT EVIDENCE PACK (EXTRACT)
         ========================================================================= */}
      {showEvidenceModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-[10px] max-w-3xl w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#C9D3DB] pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-[#0F766E]" />
                  <span>Instrument Audit Evidence Pack</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Extracted operational and regulatory provenance record.
                </p>
              </div>
              <button
                onClick={() => setShowEvidenceModal(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            {evidencePackLoading ? (
              <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-3">
                <RefreshCw className="w-8 h-8 animate-spin text-[#0F766E]" />
                <span className="text-sm">Compiling verified cryptographic digests...</span>
              </div>
            ) : evidencePackData ? (
              <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-2">
                {/* Uncertified Regulatory Disclaimer Callout */}
                <div className="p-3 bg-amber-950/40 border border-amber-800/80 rounded-lg flex items-start gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div className="text-[11px] text-amber-200 leading-snug">
                    <span className="font-semibold text-amber-100">Audit Disclaimer:</span> {evidencePackData.regulatory_disclaimer}
                  </div>
                </div>

                {/* Instrument Summary Card */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-4 rounded-lg border border-slate-800/80 font-mono text-xs">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Reference</span>
                    <span className="text-white font-bold">{evidencePackData.reference_number}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Bank</span>
                    <span className="text-white">{evidencePackData.bank_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Amount</span>
                    <span className="text-white">₹{Number(evidencePackData.amount).toLocaleString('en-IN')}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Audit Chain</span>
                    <span
                      className={`font-semibold ${
                        evidencePackData.audit_chain_verified ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {evidencePackData.chain_verification_status}
                    </span>
                  </div>
                </div>

                {/* Document Hashes Table */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                    Document Version SHA-256 Checksums
                  </h4>
                  <div className="border border-slate-800 rounded-lg overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 font-mono text-[10px]">
                        <tr>
                          <th className="py-2 px-3">Ver</th>
                          <th className="py-2 px-3">Category</th>
                          <th className="py-2 px-3">Filename</th>
                          <th className="py-2 px-3">SHA-256 Digest</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                        {evidencePackData.documents.map((doc, i) => (
                          <tr key={i} className="hover:bg-slate-800/40">
                            <td className="py-2 px-3 text-slate-400">v{doc.version_number}</td>
                            <td className="py-2 px-3 text-slate-300">{doc.category}</td>
                            <td className="py-2 px-3 text-slate-300">{doc.file_name}</td>
                            <td className="py-2 px-3 text-sentinel-300 font-mono text-[10px] truncate max-w-xs" title={doc.sha256_hash}>
                              {doc.sha256_hash}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Audit & Provenance Counters */}
                <div className="grid grid-cols-3 gap-3 text-center text-xs">
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block text-[10px] uppercase">Field Provenance</span>
                    <span className="text-base font-bold text-white font-mono">{evidencePackData.field_provenance_count}</span>
                  </div>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block text-[10px] uppercase">Scrutiny Notes</span>
                    <span className="text-base font-bold text-white font-mono">{evidencePackData.scrutiny_observations_count}</span>
                  </div>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-500 block text-[10px] uppercase">Audit Trail Events</span>
                    <span className="text-base font-bold text-white font-mono">{evidencePackData.audit_events_count}</span>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="flex justify-end pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowEvidenceModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg"
              >
                Close Evidence Extract
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
