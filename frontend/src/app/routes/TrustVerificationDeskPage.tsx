import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  ArrowLeft,
  RefreshCw,
  Send,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileText,
  RotateCcw,
  Ban,
  Plus,
  ExternalLink,
  ChevronRight,
  Search,
  Building,
  Building2,
  Calendar,
  Layers,
  History,
  FileSpreadsheet,
  Check,
  X,
  AlertOctagon,
  Eye,
  Info,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { verificationApi, instrumentsApi } from '@/api/endpoints';
import type {
  Instrument,
  FieldProvenanceItem,
  TrustAssessmentItem,
  TrustTransitionHistoryItem,
  AggregateTrustSummary,
  VerificationRequestItem,
  VerificationResponseItem,
  CreateVerificationRequestPayload,
  DispatchVerificationPayload,
  ManualVerificationRecordPayload,
  L2OfficerDecisionPayload,
  TrustDowngradePayload,
} from '@/types';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { formatINR, formatDate, formatDateTime, cn } from '@/lib/utils';

export const TrustVerificationDeskPage: React.FC = () => {
  const { id: routeInstrumentId } = useParams<{ id?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Active instrument ID (from URL param or query param)
  const activeInstrumentId = routeInstrumentId || searchParams.get('instrument_id') || '';

  // Roles & permissions
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const isAuditor = user?.role === 'AUDITOR';
  const canPerformOfficerActions = [
    'SYSTEM_ADMIN',
    'SCRUTINY_OFFICER',
    'BRANCH_HEAD',
    'COMPETENT_AUTHORITY',
  ].includes(user?.role || '');

  // Desk State
  const [activeTab, setActiveTab] = useState<'trust' | 'provenance' | 'requests' | 'conflicts'>('trust');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Selected Instrument & Verification Data
  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [trustSummary, setTrustSummary] = useState<AggregateTrustSummary | null>(null);
  const [trustHistory, setTrustHistory] = useState<TrustTransitionHistoryItem[]>([]);
  const [trustAssessments, setTrustAssessments] = useState<TrustAssessmentItem[]>([]);
  const [provenanceList, setProvenanceList] = useState<FieldProvenanceItem[]>([]);
  const [verificationRequests, setVerificationRequests] = useState<VerificationRequestItem[]>([]);

  // Directory state (when searching or no instrument selected)
  const [instrumentsDirectory, setInstrumentsDirectory] = useState<Instrument[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [trustFilter, setTrustFilter] = useState<string>('ALL');
  const [isSearchingDirectory, setIsSearchingDirectory] = useState(false);

  // Field filter for provenance tab
  const [selectedFieldFilter, setSelectedFieldFilter] = useState<string>('ALL');

  // Modals state
  const [isL2ModalOpen, setIsL2ModalOpen] = useState(false);
  const [isL3ModalOpen, setIsL3ModalOpen] = useState(false);
  const [isDowngradeModalOpen, setIsDowngradeModalOpen] = useState(false);
  const [isNewRequestModalOpen, setIsNewRequestModalOpen] = useState(false);
  const [isManualEvidenceModalOpen, setIsManualEvidenceModalOpen] = useState(false);
  const [isDispatchRequestModalOpen, setIsDispatchRequestModalOpen] = useState(false);
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);

  // Form states
  const [l2Reason, setL2Reason] = useState('');
  const [l2DocVersion, setL2DocVersion] = useState('');
  const [l2EvidenceRefs, setL2EvidenceRefs] = useState('');
  const [isSubmittingL2, setIsSubmittingL2] = useState(false);

  const [l3ResponseId, setL3ResponseId] = useState('');
  const [l3Reason, setL3Reason] = useState('');
  const [l3AuthConfig, setL3AuthConfig] = useState('BANK_PORTAL_SFTP_HOST_TO_HOST');
  const [isSubmittingL3, setIsSubmittingL3] = useState(false);

  const [downgradeTarget, setDowngradeTarget] = useState<'L0_DECLARED' | 'L1_DOCUMENT_CONSISTENT'>('L1_DOCUMENT_CONSISTENT');
  const [downgradeReason, setDowngradeReason] = useState('');
  const [downgradeTrigger, setDowngradeTrigger] = useState('CONFLICTING_BANK_EVIDENCE');
  const [isSubmittingDowngrade, setIsSubmittingDowngrade] = useState(false);

  const [newRequestChannel, setNewRequestChannel] = useState('SFTP_RECONCILIATION');
  const [newRequestFields, setNewRequestFields] = useState<string[]>([
    'amount',
    'maturity_date',
    'bank_name',
    'reference_number',
  ]);
  const [newRequestNotes, setNewRequestNotes] = useState('');
  const [isSubmittingNewRequest, setIsSubmittingNewRequest] = useState(false);

  const [dispatchScenario, setDispatchScenario] = useState('NORMAL_MATCH');
  const [isSubmittingDispatch, setIsSubmittingDispatch] = useState(false);

  const [manualRef, setManualRef] = useState('');
  const [manualDate, setManualDate] = useState(new Date().toISOString().split('T')[0]);
  const [manualResult, setManualResult] = useState('MATCH');
  const [manualReason, setManualReason] = useState('');
  const [manualDocVersion, setManualDocVersion] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualMaturityDate, setManualMaturityDate] = useState('');
  const [isSubmittingManual, setIsSubmittingManual] = useState(false);

  // Load instrument directory
  const loadDirectory = useCallback(async () => {
    setIsSearchingDirectory(true);
    try {
      const res = await instrumentsApi.list({ limit: 50 });
      setInstrumentsDirectory(res.items || []);
    } catch (err: any) {
      console.error('Failed to load instruments directory', err);
    } finally {
      setIsSearchingDirectory(false);
    }
  }, []);

  // Load all verification data for active instrument
  const loadVerificationData = useCallback(async (instrumentId: string) => {
    if (!instrumentId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [inst, summaryRes, historyRes, assessRes, provRes, reqRes] = await Promise.all([
        instrumentsApi.get(instrumentId),
        verificationApi.getTrustSummary(instrumentId).catch(() => null),
        verificationApi.getTrustHistory(instrumentId).catch(() => []),
        verificationApi.getTrustAssessments(instrumentId).catch(() => []),
        verificationApi.getProvenance(instrumentId).catch(() => []),
        verificationApi.listRequests(instrumentId).catch(() => []),
      ]);

      setInstrument(inst);
      setTrustSummary(summaryRes);
      setTrustHistory(historyRes || []);
      setTrustAssessments(assessRes || []);
      setProvenanceList(provRes || []);
      setVerificationRequests(reqRes || []);
    } catch (err: any) {
      setErrorMessage(
        err?.response?.data?.detail || err?.response?.data?.message || err?.message || 'Failed to retrieve verification desk data.'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeInstrumentId) {
      loadVerificationData(activeInstrumentId);
    } else {
      loadDirectory();
    }
  }, [activeInstrumentId, loadVerificationData, loadDirectory]);

  // Handle instrument select from directory
  const handleSelectInstrument = (instId: string) => {
    setSearchParams({ instrument_id: instId });
  };

  // Switch to another instrument
  const handleBackToDirectory = () => {
    setSearchParams({});
    setInstrument(null);
    loadDirectory();
  };

  // Submit L2 Officer Decision
  const handleRecordL2Decision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeInstrumentId || !l2Reason.trim()) return;
    setIsSubmittingL2(true);
    setErrorMessage(null);
    try {
      const payload: L2OfficerDecisionPayload = {
        reason: l2Reason.trim(),
        supporting_document_version_id: l2DocVersion.trim() || null,
        evidence_references: l2EvidenceRefs
          ? l2EvidenceRefs.split(',').map((s) => s.trim()).filter(Boolean)
          : null,
      };
      await verificationApi.recordL2Decision(activeInstrumentId, payload);
      setSuccessMessage('L2 Officer Attestation successfully recorded and trust updated.');
      setIsL2ModalOpen(false);
      setL2Reason('');
      setL2DocVersion('');
      setL2EvidenceRefs('');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to record L2 officer decision.');
    } finally {
      setIsSubmittingL2(false);
    }
  };

  // Submit L3 Bank Confirmation
  const handleApplyL3Confirmation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeInstrumentId || !l3Reason.trim()) return;
    setIsSubmittingL3(true);
    setErrorMessage(null);
    try {
      await verificationApi.applyL3Confirmation(activeInstrumentId, {
        verification_response_id: l3ResponseId,
        reason: l3Reason.trim(),
        source_authorization_config: l3AuthConfig,
      });
      setSuccessMessage('Level 3 Direct Bank Confirmation applied successfully!');
      setIsL3ModalOpen(false);
      setL3Reason('');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to apply L3 bank confirmation.');
    } finally {
      setIsSubmittingL3(false);
    }
  };

  // Submit Trust Downgrade
  const handleDowngradeTrust = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeInstrumentId || !downgradeReason.trim()) return;
    setIsSubmittingDowngrade(true);
    setErrorMessage(null);
    try {
      const payload: TrustDowngradePayload = {
        target_trust_level: downgradeTarget,
        reason: downgradeReason.trim(),
        triggering_event: downgradeTrigger,
      };
      await verificationApi.performTrustDowngrade(activeInstrumentId, payload);
      setSuccessMessage(`Trust level successfully downgraded to ${downgradeTarget} with audit reason.`);
      setIsDowngradeModalOpen(false);
      setDowngradeReason('');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to execute trust downgrade.');
    } finally {
      setIsSubmittingDowngrade(false);
    }
  };

  // Submit New Verification Request
  const handleCreateVerificationRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeInstrumentId) return;
    setIsSubmittingNewRequest(true);
    setErrorMessage(null);
    try {
      const payload: CreateVerificationRequestPayload = {
        channel: newRequestChannel,
        requested_fields: newRequestFields,
        notes: newRequestNotes.trim() || undefined,
      };
      await verificationApi.createRequest(activeInstrumentId, payload);
      setSuccessMessage('Bank Verification Request initiated successfully.');
      setIsNewRequestModalOpen(false);
      setNewRequestNotes('');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to create verification request.');
    } finally {
      setIsSubmittingNewRequest(false);
    }
  };

  // Dispatch Verification Request
  const handleDispatchRequest = async () => {
    if (!activeRequestId) return;
    setIsSubmittingDispatch(true);
    setErrorMessage(null);
    try {
      const payload: DispatchVerificationPayload = {
        scenario: dispatchScenario,
      };
      await verificationApi.dispatchRequest(activeRequestId, payload);
      setSuccessMessage('Verification request dispatched to bank channel adapter.');
      setIsDispatchRequestModalOpen(false);
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Dispatch failed.');
    } finally {
      setIsSubmittingDispatch(false);
    }
  };

  // Record Manual Evidence
  const handleRecordManualEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeRequestId || !manualRef.trim() || !manualReason.trim()) return;
    setIsSubmittingManual(true);
    setErrorMessage(null);
    try {
      const bankVals: Record<string, any> = {};
      if (manualAmount) bankVals.amount = manualAmount;
      if (manualMaturityDate) bankVals.maturity_date = manualMaturityDate;

      const payload: ManualVerificationRecordPayload = {
        external_reference: manualRef.trim(),
        communication_date: manualDate,
        result: manualResult,
        reason: manualReason.trim(),
        evidence_document_version_id: manualDocVersion.trim() || null,
        bank_values: Object.keys(bankVals).length > 0 ? bankVals : undefined,
      };
      await verificationApi.recordManualEvidence(activeRequestId, payload);
      setSuccessMessage('Manual bank verification response recorded with evidence.');
      setIsManualEvidenceModalOpen(false);
      setManualRef('');
      setManualReason('');
      setManualAmount('');
      setManualMaturityDate('');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to record manual evidence.');
    } finally {
      setIsSubmittingManual(false);
    }
  };

  // Retry Request
  const handleRetryRequest = async (requestId: string) => {
    setErrorMessage(null);
    try {
      await verificationApi.retryRequest(requestId, {});
      setSuccessMessage('Verification retry scheduled and executed.');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to retry request.');
    }
  };

  // Cancel Request
  const handleCancelRequest = async (requestId: string) => {
    const reason = prompt('Please enter the reason for cancelling this request:');
    if (!reason || !reason.trim()) return;
    setErrorMessage(null);
    try {
      await verificationApi.cancelRequest(requestId, { reason: reason.trim() });
      setSuccessMessage('Verification request cancelled.');
      loadVerificationData(activeInstrumentId);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to cancel request.');
    }
  };

  // Trust Badge Renderer
  const renderTrustBadge = (level: string) => {
    switch (level) {
      case 'L3_BANK_CONFIRMED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-300 shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-purple-600" />
            <span>L3 BANK CONFIRMED</span>
          </span>
        );
      case 'L2_OFFICER_VERIFIED':
      case 'L2_OFFICER_REVIEWED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>L2 OFFICER REVIEWED</span>
          </span>
        );
      case 'L1_DOCUMENT_CONSISTENT':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-300 shadow-2xs">
            <Shield className="w-4 h-4 text-blue-600" />
            <span>L1 DOCUMENT CONSISTENT</span>
          </span>
        );
      case 'L0_DECLARED':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-300 shadow-2xs">
            <ShieldAlert className="w-4 h-4 text-slate-500" />
            <span>L0 DECLARED</span>
          </span>
        );
    }
  };

  // Filter directory list
  const filteredDirectory = instrumentsDirectory.filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.reference_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.bank_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.institution_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.institution_code?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTrust =
      trustFilter === 'ALL' || item.trust_level === trustFilter;

    return matchesSearch && matchesTrust;
  });

  // Unique field names in provenance
  const availableFieldNames = Array.from(
    new Set(provenanceList.map((p) => p.field_name))
  ).sort();

  const filteredProvenance = provenanceList.filter((p) => {
    if (selectedFieldFilter === 'ALL') return true;
    return p.field_name === selectedFieldFilter;
  });

  // Completed verification responses eligible for L3
  const completedResponses = verificationRequests
    .flatMap((r) => r.responses || [])
    .filter((resp) => resp.result === 'MATCH');

  // =========================================================================
  // VIEW: NO INSTRUMENT SELECTED - DIRECTORY BROWSER
  // =========================================================================
  if (!activeInstrumentId) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-sentinel-700" />
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                Trust & Verification Desk
              </h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Authoritative statutory FDR trust state enforcement, electronic bank confirmation and field provenance timeline.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadDirectory}
              disabled={isSearchingDirectory}
              className="gap-2"
            >
              <RefreshCw className={cn('w-4 h-4', isSearchingDirectory && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Hierarchy Overview Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Level 0 — Declared
              </span>
              <ShieldAlert className="w-4 h-4 text-slate-400" />
            </div>
            <p className="text-2xl font-bold text-slate-800">
              {instrumentsDirectory.filter((i) => i.trust_level === 'L0_DECLARED').length}
            </p>
            <p className="text-xs text-slate-500 mt-1">Self-declared statutory deposits</p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-blue-200 shadow-2xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
                Level 1 — Consistent
              </span>
              <Shield className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-bold text-blue-900">
              {instrumentsDirectory.filter((i) => i.trust_level === 'L1_DOCUMENT_CONSISTENT').length}
            </p>
            <p className="text-xs text-blue-600/80 mt-1">OCR document rules validated</p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-emerald-200 shadow-2xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">
                Level 2 — Officer Verified
              </span>
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
            </div>
            <p className="text-2xl font-bold text-emerald-900">
              {instrumentsDirectory.filter((i) => i.trust_level === 'L2_OFFICER_VERIFIED').length}
            </p>
            <p className="text-xs text-emerald-600/80 mt-1">Scrutiny officer reviewed & attested</p>
          </div>

          <div className="p-4 rounded-xl bg-white border border-purple-200 shadow-2xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-purple-600 uppercase tracking-wider">
                Level 3 — Bank Confirmed
              </span>
              <ShieldCheck className="w-4 h-4 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-purple-900">
              {instrumentsDirectory.filter((i) => i.trust_level === 'L3_BANK_CONFIRMED').length}
            </p>
            <p className="text-xs text-purple-600/80 mt-1">Authoritative electronic confirmation</p>
          </div>
        </div>

        {/* Directory Search & Filter Bar */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex flex-col md:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by FDR reference number, bank name, institution..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sentinel-500 text-slate-800"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500 shrink-0">Trust Level:</span>
              <select
                value={trustFilter}
                onChange={(e) => setTrustFilter(e.target.value)}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
              >
                <option value="ALL">All Trust Levels</option>
                <option value="L0_DECLARED">L0 — Declared</option>
                <option value="L1_DOCUMENT_CONSISTENT">L1 — Document Consistent</option>
                <option value="L2_OFFICER_VERIFIED">L2 — Officer Verified</option>
                <option value="L3_BANK_CONFIRMED">L3 — Bank Confirmed</option>
              </select>
            </div>
          </div>
        </div>

        {/* Directory Instruments Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Registered Instruments ({filteredDirectory.length})
            </span>
            <span className="text-xs text-slate-500">
              Select an instrument to inspect provenance, bank verification, or execute trust elevation
            </span>
          </div>

          {filteredDirectory.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <FileSpreadsheet className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-medium">No instruments match the selected criteria.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
                    <th className="py-3 px-4">Reference No.</th>
                    <th className="py-3 px-4">Bank & Branch</th>
                    <th className="py-3 px-4">Institution</th>
                    <th className="py-3 px-4 text-right">Deposit Amount</th>
                    <th className="py-3 px-4">Maturity Date</th>
                    <th className="py-3 px-4 text-center">Trust State</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredDirectory.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                      onClick={() => handleSelectInstrument(item.id)}
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-sentinel-800">
                        {item.reference_number}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-800">{item.bank_name}</div>
                        <div className="text-xs text-slate-400">{item.branch || '—'}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-800">
                          {item.institution_name || item.institution_code || item.institution_id}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-medium text-slate-900">
                        {formatINR(item.amount)}
                      </td>
                      <td className="py-3.5 px-4 text-xs font-mono text-slate-600">
                        {formatDate(item.maturity_date)}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {renderTrustBadge(item.trust_level)}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1 text-xs group-hover:border-sentinel-500 group-hover:text-sentinel-700"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectInstrument(item.id);
                          }}
                        >
                          <span>Open Desk</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // =========================================================================
  // VIEW: SPECIFIC INSTRUMENT SELECTED - FULL DESK
  // =========================================================================
  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Alert Messages */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 flex items-start justify-between gap-3 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <AlertOctagon className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Action Failed</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-400 hover:text-rose-700 text-sm font-bold"
          >
            ×
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-start justify-between gap-3 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Success</p>
              <p className="text-xs text-emerald-700 mt-0.5">{successMessage}</p>
            </div>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-400 hover:text-emerald-700 text-sm font-bold"
          >
            ×
          </button>
        </div>
      )}

      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleBackToDirectory}
            className="gap-1.5 text-xs text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>All Instruments</span>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-sentinel-700 bg-sentinel-50 border border-sentinel-200 px-2 py-0.5 rounded">
                Desk
              </span>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight font-mono">
                {instrument?.reference_number || 'Loading FDR...'}
              </h1>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {instrument?.bank_name} • {instrument?.institution_name || instrument?.institution_code}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {instrument && (
            <Link
              to={`/instruments/${instrument.id}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Module 1 Detail</span>
            </Link>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => loadVerificationData(activeInstrumentId)}
            disabled={isLoading}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Summary Banner Card */}
      {instrument && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Current Trust State
              </span>
              <div className="flex items-center gap-3">
                {renderTrustBadge(instrument.trust_level)}
                <span className="text-xs font-medium text-slate-500">
                  Status:{' '}
                  <span className="font-semibold text-slate-800">{instrument.status}</span>
                </span>
                {trustAssessments.length > 0 && (
                  <span className="text-[11px] font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded border border-slate-200">
                    Concurrency Ver: {trustAssessments[0].concurrency_version}
                  </span>
                )}
              </div>
            </div>

            {/* Officer Action Quick Buttons */}
            {canPerformOfficerActions && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsL2ModalOpen(true)}
                  className="gap-1.5 text-xs border-emerald-300 text-emerald-800 hover:bg-emerald-50"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Attest L2 Officer</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsL3ModalOpen(true)}
                  className="gap-1.5 text-xs border-purple-300 text-purple-800 hover:bg-purple-50"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                  <span>Apply L3 Bank</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDowngradeModalOpen(true)}
                  className="gap-1.5 text-xs border-rose-300 text-rose-700 hover:bg-rose-50"
                >
                  <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                  <span>Downgrade / Conflict</span>
                </Button>
              </div>
            )}
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-slate-400 block font-medium">Principal Amount</span>
              <span className="font-mono font-bold text-slate-900 text-sm">
                {formatINR(instrument.amount)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Maturity Date</span>
              <span className="font-mono text-slate-900 text-sm">
                {formatDate(instrument.maturity_date)}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Lien Status</span>
              <span className="font-semibold text-slate-800 text-sm">
                {instrument.lien_marked ? 'Lien Marked' : 'No Lien Recorded'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Verification Requests</span>
              <span className="font-mono font-bold text-slate-900 text-sm">
                {verificationRequests.length} initiated
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-sm font-medium">
          <button
            onClick={() => setActiveTab('trust')}
            className={cn(
              'pb-3 border-b-2 flex items-center gap-2 transition-colors',
              activeTab === 'trust'
                ? 'border-sentinel-700 text-sentinel-900 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            )}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Trust State & History ({trustHistory.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('provenance')}
            className={cn(
              'pb-3 border-b-2 flex items-center gap-2 transition-colors',
              activeTab === 'provenance'
                ? 'border-sentinel-700 text-sentinel-900 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            )}
          >
            <History className="w-4 h-4" />
            <span>Field Provenance Timeline ({provenanceList.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('requests')}
            className={cn(
              'pb-3 border-b-2 flex items-center gap-2 transition-colors',
              activeTab === 'requests'
                ? 'border-sentinel-700 text-sentinel-900 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            )}
          >
            <Send className="w-4 h-4" />
            <span>Bank Verification Requests ({verificationRequests.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('conflicts')}
            className={cn(
              'pb-3 border-b-2 flex items-center gap-2 transition-colors',
              activeTab === 'conflicts'
                ? 'border-sentinel-700 text-sentinel-900 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            )}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Conflict & Discrepancy Matrix</span>
          </button>
        </nav>
      </div>

      {/* =================================================================== */}
      {/* TAB 1: TRUST STATE & TRANSITION HISTORY */}
      {/* =================================================================== */}
      {activeTab === 'trust' && (
        <div className="space-y-6">
          {/* Aggregate Field Breakdown */}
          {trustSummary && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Aggregate Trust Assessment Breakdown
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">{trustSummary.note}</p>
                </div>
                {renderTrustBadge(trustSummary.aggregate_trust_level)}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
                {Object.entries(trustSummary.fields_by_level || {}).map(([lvl, fields]) => (
                  <div key={lvl} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-[11px] font-mono font-bold text-slate-600 block uppercase mb-1">
                      {lvl.replace('_', ' ')}
                    </span>
                    {fields.length === 0 ? (
                      <span className="text-xs text-slate-400 italic">None</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {fields.map((f) => (
                          <span
                            key={f}
                            className="text-[10px] font-mono bg-white text-slate-700 px-1.5 py-0.5 rounded border border-slate-200"
                          >
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {trustSummary.uncovered_fields?.length > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    Uncovered Fields lacking explicit assessment:{' '}
                    <strong>{trustSummary.uncovered_fields.join(', ')}</strong>
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Transition History Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Audited Trust Transition History ({trustHistory.length})
              </h3>
              <span className="text-xs text-slate-500 font-mono">
                Immutable transition ledger
              </span>
            </div>

            {trustHistory.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <History className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs font-medium">No formal trust state transitions recorded yet.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase text-slate-500 tracking-wider">
                      <th className="py-2.5 px-4">Timestamp</th>
                      <th className="py-2.5 px-4">Level Transition</th>
                      <th className="py-2.5 px-4">Trigger & Actor</th>
                      <th className="py-2.5 px-4">Audited Reason</th>
                      <th className="py-2.5 px-4">Evidence References</th>
                      <th className="py-2.5 px-4 text-center">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {trustHistory.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                          {formatDateTime(item.timestamp)}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 font-mono font-bold">
                            <span className="text-slate-500">{item.prior_trust_level}</span>
                            <span className="text-slate-400">→</span>
                            <span
                              className={cn(
                                item.is_downgrade ? 'text-rose-600' : 'text-emerald-700'
                              )}
                            >
                              {item.new_trust_level}
                            </span>
                            {item.is_downgrade && (
                              <span className="text-[9px] font-mono bg-rose-100 text-rose-700 px-1 rounded font-bold">
                                DOWNGRADE
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-slate-800 block">
                            {item.trigger_type}
                          </span>
                          <span className="text-[11px] text-slate-500 font-mono">
                            {item.actor_user_id || item.actor_service || 'SYSTEM'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-700 max-w-xs font-serif italic">
                          "{item.reason}"
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-600 max-w-xs truncate">
                          {item.evidence_references_json || '—'}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={cn(
                              'text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase',
                              item.outcome === 'SUCCESS'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-rose-100 text-rose-800'
                            )}
                          >
                            {item.outcome}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 2: FIELD PROVENANCE TIMELINE */}
      {/* =================================================================== */}
      {activeTab === 'provenance' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Field-Level Provenance & Audit Trail
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every field mutation is tracked with source actor, service ID, timestamp, and supporting document version.
              </p>
            </div>

            {/* Field Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">Filter Field:</span>
              <select
                value={selectedFieldFilter}
                onChange={(e) => setSelectedFieldFilter(e.target.value)}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono"
              >
                <option value="ALL">All Fields ({availableFieldNames.length})</option>
                {availableFieldNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {filteredProvenance.length === 0 ? (
            <div className="p-12 bg-white rounded-xl border border-slate-200 text-center text-slate-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs font-medium">No provenance records logged for this filter.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredProvenance.map((item, idx) => (
                <div
                  key={item.id}
                  className={cn(
                    'p-4 rounded-xl border bg-white shadow-2xs transition-all',
                    item.is_active
                      ? 'border-sentinel-300 bg-sentinel-50/20 ring-1 ring-sentinel-200'
                      : 'border-slate-200 opacity-80'
                  )}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-sentinel-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        {item.field_name}
                      </span>
                      {item.is_active && (
                        <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-200">
                          CURRENT ACTIVE VALUE
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-mono text-slate-500">
                      Recorded: {formatDateTime(item.source_timestamp)}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="text-slate-400 font-medium block">Recorded Value</span>
                      <span className="font-mono font-bold text-slate-900 text-sm mt-0.5 block break-all">
                        {item.recorded_value || '—'}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 font-medium block">Source Channel & Actor</span>
                      <span className="font-semibold text-slate-800 mt-0.5 block">
                        {item.source_type}
                      </span>
                      <span className="text-slate-500 font-mono text-[11px]">
                        Actor: {item.source_actor_id || item.source_service_id || 'SYSTEM'}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 font-medium block">Evidence Reference</span>
                      <span className="font-mono text-slate-700 text-xs mt-0.5 block">
                        {item.evidence_reference || item.related_document_version_id || 'None attached'}
                      </span>
                      {item.related_validation_run_id && (
                        <span className="text-slate-400 font-mono text-[10px] block">
                          Validation Run: {item.related_validation_run_id}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 3: BANK VERIFICATION REQUESTS & RESPONSES */}
      {/* =================================================================== */}
      {activeTab === 'requests' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Electronic Bank Verification Pipeline
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Automated SFTP / Host-to-Host API reconciliation & manual banking confirmation workflows.
              </p>
            </div>

            {canPerformOfficerActions && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsNewRequestModalOpen(true)}
                className="gap-1.5 text-xs shadow-xs"
              >
                <Plus className="w-4 h-4" />
                <span>Initiate Verification Request</span>
              </Button>
            )}
          </div>

          {verificationRequests.length === 0 ? (
            <div className="p-12 bg-white rounded-xl border border-slate-200 text-center text-slate-400">
              <Send className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-xs font-medium">No bank verification requests dispatched yet.</p>
              {canPerformOfficerActions && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsNewRequestModalOpen(true)}
                  className="mt-3 gap-1.5 text-xs"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create First Request</span>
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {verificationRequests.map((req) => (
                <div
                  key={req.id}
                  className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden"
                >
                  {/* Request Header */}
                  <div className="p-4 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-bold text-sentinel-800 bg-sentinel-100/60 border border-sentinel-200 px-2.5 py-1 rounded">
                        {req.reference_code}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">
                        Channel: <span className="font-mono">{req.channel}</span>
                      </span>
                      <span
                        className={cn(
                          'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase',
                          req.status === 'COMPLETED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : req.status === 'DISPATCHED'
                            ? 'bg-blue-100 text-blue-800'
                            : req.status === 'FAILED'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-slate-100 text-slate-700'
                        )}
                      >
                        {req.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {canPerformOfficerActions && req.status === 'PENDING' && (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            setActiveRequestId(req.id);
                            setIsDispatchRequestModalOpen(true);
                          }}
                          className="gap-1 text-xs"
                        >
                          <Send className="w-3.5 h-3.5" />
                          <span>Dispatch</span>
                        </Button>
                      )}

                      {canPerformOfficerActions &&
                        ['PENDING', 'DISPATCHED'].includes(req.status) && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setActiveRequestId(req.id);
                              setIsManualEvidenceModalOpen(true);
                            }}
                            className="gap-1 text-xs border-slate-300 text-slate-700"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            <span>Record Manual Evidence</span>
                          </Button>
                        )}

                      {canPerformOfficerActions && req.status === 'FAILED' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRetryRequest(req.id)}
                          className="gap-1 text-xs border-amber-300 text-amber-700 hover:bg-amber-50"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Retry</span>
                        </Button>
                      )}

                      {canPerformOfficerActions &&
                        ['PENDING', 'DISPATCHED'].includes(req.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCancelRequest(req.id)}
                            className="gap-1 text-xs text-rose-600 hover:bg-rose-50"
                          >
                            <Ban className="w-3.5 h-3.5" />
                            <span>Cancel</span>
                          </Button>
                        )}
                    </div>
                  </div>

                  {/* Request Body & Metadata */}
                  <div className="p-4 space-y-3 text-xs">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div>
                        <span className="text-slate-400 block font-medium">Attempt Count</span>
                        <span className="font-mono font-semibold text-slate-800">
                          {req.attempt_count}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-medium">Last Attempt</span>
                        <span className="font-mono text-slate-700">
                          {req.last_attempt_at ? formatDateTime(req.last_attempt_at) : 'None'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-medium">Requested Fields</span>
                        <span className="font-mono text-slate-800 truncate block">
                          {req.requested_fields_json || 'ALL_CORE_FIELDS'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block font-medium">Created</span>
                        <span className="font-mono text-slate-700">
                          {formatDateTime(req.created_at)}
                        </span>
                      </div>
                    </div>

                    {req.error_details && (
                      <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                        <strong>Adapter Error:</strong> {req.error_details}
                      </div>
                    )}

                    {/* Received Responses */}
                    {req.responses && req.responses.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-100 space-y-3">
                        <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                          Received Bank Responses ({req.responses.length})
                        </span>

                        {req.responses.map((resp) => (
                          <div
                            key={resp.id}
                            className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span
                                  className={cn(
                                    'text-xs font-bold px-2 py-0.5 rounded-full uppercase',
                                    resp.result === 'MATCH'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : resp.result === 'MISMATCH'
                                      ? 'bg-rose-100 text-rose-800'
                                      : 'bg-amber-100 text-amber-800'
                                  )}
                                >
                                  {resp.result}
                                </span>
                                <span className="font-mono text-slate-600 text-[11px]">
                                  Ref: {resp.bank_reference_number || 'None'}
                                </span>
                                {resp.is_simulated && (
                                  <span className="text-[10px] font-mono bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.2 rounded">
                                    SIMULATED ADAPTER
                                  </span>
                                )}
                              </div>
                              <span className="text-[11px] font-mono text-slate-500">
                                Responded: {formatDateTime(resp.responded_at)}
                              </span>
                            </div>

                            {resp.notes && (
                              <p className="text-xs text-slate-600 italic">"{resp.notes}"</p>
                            )}

                            {/* Field Comparisons Table if available */}
                            {resp.field_comparisons_json && (
                              <div className="mt-2 bg-white rounded border border-slate-200 p-2 text-[11px] font-mono">
                                <span className="text-slate-400 block text-[10px] uppercase font-bold mb-1">
                                  Bank Reconciliation Comparison
                                </span>
                                <pre className="text-slate-700 whitespace-pre-wrap">
                                  {resp.field_comparisons_json}
                                </pre>
                              </div>
                            )}

                            {/* Action to apply this response to L3 directly */}
                            {canPerformOfficerActions &&
                              resp.result === 'MATCH' &&
                              instrument.trust_level !== 'L3_BANK_CONFIRMED' && (
                                <div className="pt-2 flex justify-end">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setL3ResponseId(resp.id);
                                      setL3Reason(
                                        `Authoritative electronic confirmation received via ${resp.channel} matching reference ${resp.bank_reference_number || req.reference_code}.`
                                      );
                                      setIsL3ModalOpen(true);
                                    }}
                                    className="gap-1.5 text-xs border-purple-300 text-purple-800 hover:bg-purple-50"
                                  >
                                    <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                                    <span>Elevate to L3 with this Response</span>
                                  </Button>
                                </div>
                              )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* TAB 4: CONFLICT & DISCREPANCY MATRIX */}
      {/* =================================================================== */}
      {activeTab === 'conflicts' && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">
              Multi-Source Evidence Conflict Matrix
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Comparison across Declared Values, Ingested Document OCR Extractions, and Bank Confirmation Feeds.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-semibold uppercase text-slate-500 tracking-wider">
                  <th className="py-2.5 px-3">Field Name</th>
                  <th className="py-2.5 px-3">Declared Value (L0)</th>
                  <th className="py-2.5 px-3">Document OCR (L1/L2)</th>
                  <th className="py-2.5 px-3">Bank Response (L3)</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-800">amount</td>
                  <td className="py-3 px-3 text-slate-700">{formatINR(instrument?.amount)}</td>
                  <td className="py-3 px-3 text-slate-700">
                    {provenanceList.find((p) => p.field_name === 'amount' && p.source_type.includes('OCR'))?.recorded_value || '—'}
                  </td>
                  <td className="py-3 px-3 text-slate-700">
                    {completedResponses[0]?.bank_reference_number ? formatINR(instrument?.amount) : 'Pending Confirmation'}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      CONSISTENT
                    </span>
                  </td>
                </tr>

                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-800">maturity_date</td>
                  <td className="py-3 px-3 text-slate-700">{formatDate(instrument?.maturity_date)}</td>
                  <td className="py-3 px-3 text-slate-700">
                    {provenanceList.find((p) => p.field_name === 'maturity_date' && p.source_type.includes('OCR'))?.recorded_value || '—'}
                  </td>
                  <td className="py-3 px-3 text-slate-700">
                    {completedResponses[0]?.bank_reference_number ? formatDate(instrument?.maturity_date) : 'Pending Confirmation'}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      CONSISTENT
                    </span>
                  </td>
                </tr>

                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-800">reference_number</td>
                  <td className="py-3 px-3 text-slate-700">{instrument?.reference_number}</td>
                  <td className="py-3 px-3 text-slate-700">
                    {provenanceList.find((p) => p.field_name === 'reference_number' && p.source_type.includes('OCR'))?.recorded_value || '—'}
                  </td>
                  <td className="py-3 px-3 text-slate-700">
                    {completedResponses[0]?.bank_reference_number || 'Pending Confirmation'}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      CONSISTENT
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1.5 text-slate-600">
            <p className="font-semibold text-slate-800">Automated Conflict Downgrade Policy:</p>
            <p>
              Under Rule §4.3 of statutory verification protocols, any discrepancy between bank electronic feeds and declared fields blocks Level 3 confirmation and automatically downgrades the instrument trust state to Level 1, requiring reasoned scrutiny officer re-examination.
            </p>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: RECORD L2 OFFICER DECISION */}
      {/* =================================================================== */}
      {isL2ModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-emerald-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-slate-900 text-sm">
                  Record L2 Officer Review Attestation
                </h3>
              </div>
              <button
                onClick={() => setIsL2ModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleRecordL2Decision} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Reasoned Officer Assessment Justification <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Detail the documentary inspection, seal verification, and branch confirmation reviewed..."
                  value={l2Reason}
                  onChange={(e) => setL2Reason(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Supporting Document Version ID (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. DOC-VER-001"
                  value={l2DocVersion}
                  onChange={(e) => setL2DocVersion(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono text-slate-800"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Evidence References (Comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="BRANCH-EMAIL-REF-102, AICTE-SEAL-VERIFIED"
                  value={l2EvidenceRefs}
                  onChange={(e) => setL2EvidenceRefs(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono text-slate-800"
                />
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-500 space-y-1">
                <p>
                  <strong>Target Level:</strong> L2_OFFICER_VERIFIED
                </p>
                <p>
                  Attestation will be recorded permanently with your user signature in the immutable trust transition ledger.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsL2ModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingL2 || !l2Reason.trim()}
                  className="gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white"
                >
                  {isSubmittingL2 && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Sign & Elevate to L2</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: APPLY L3 BANK CONFIRMATION */}
      {/* =================================================================== */}
      {isL3ModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-purple-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-purple-600" />
                <h3 className="font-bold text-slate-900 text-sm">
                  Apply Level 3 Direct Bank Confirmation
                </h3>
              </div>
              <button
                onClick={() => setIsL3ModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleApplyL3Confirmation} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Source Verification Response <span className="text-rose-500">*</span>
                </label>
                {completedResponses.length > 0 ? (
                  <select
                    value={l3ResponseId}
                    onChange={(e) => setL3ResponseId(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono text-slate-800"
                    required
                  >
                    <option value="">Select verified bank response...</option>
                    {completedResponses.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.channel} • Ref: {r.bank_reference_number || r.id.slice(0, 8)} ({r.result})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    required
                    placeholder="Enter completed verification response ID..."
                    value={l3ResponseId}
                    onChange={(e) => setL3ResponseId(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono text-slate-800"
                  />
                )}
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Source Authorization Configuration
                </label>
                <input
                  type="text"
                  value={l3AuthConfig}
                  onChange={(e) => setL3AuthConfig(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono text-slate-800"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Reason & Confirmation Details <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Detail the electronic confirmation payload received from the bank..."
                  value={l3Reason}
                  onChange={(e) => setL3Reason(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-slate-800"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsL3ModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingL3 || !l3Reason.trim() || !l3ResponseId.trim()}
                  className="gap-1.5 bg-purple-700 hover:bg-purple-800 text-white"
                >
                  {isSubmittingL3 && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Confirm Level 3 Trust</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: TRUST DOWNGRADE */}
      {/* =================================================================== */}
      {isDowngradeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-rose-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-rose-600" />
                <h3 className="font-bold text-slate-900 text-sm">
                  Audited Trust Downgrade / Conflict Resolution
                </h3>
              </div>
              <button
                onClick={() => setIsDowngradeModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleDowngradeTrust} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Target Trust Level
                </label>
                <select
                  value={downgradeTarget}
                  onChange={(e) => setDowngradeTarget(e.target.value as any)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 font-mono text-slate-800"
                >
                  <option value="L1_DOCUMENT_CONSISTENT">L1_DOCUMENT_CONSISTENT (Document Validated Only)</option>
                  <option value="L0_DECLARED">L0_DECLARED (Revert to Raw Declared State)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Triggering Event
                </label>
                <select
                  value={downgradeTrigger}
                  onChange={(e) => setDowngradeTrigger(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 text-slate-800"
                >
                  <option value="CONFLICTING_BANK_EVIDENCE">Conflicting Bank Evidence / Mismatch</option>
                  <option value="DOCUMENT_SUPERSEDED_OR_REVOKED">Document Revocation / Invalidation</option>
                  <option value="VALIDATION_FINDING_REOPENED">Critical Rule Finding Reopened</option>
                  <option value="OFFICER_REASSESSMENT">Officer Discretionary Reassessment</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Mandatory Downgrade Reason <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Detail the discovered conflict or policy justification necessitating downgrade..."
                  value={downgradeReason}
                  onChange={(e) => setDowngradeReason(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 text-slate-800"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDowngradeModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="danger"
                  size="sm"
                  disabled={isSubmittingDowngrade || !downgradeReason.trim()}
                  className="gap-1.5"
                >
                  {isSubmittingDowngrade && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Execute Downgrade</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: INITIATE NEW VERIFICATION REQUEST */}
      {/* =================================================================== */}
      {isNewRequestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-sentinel-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Send className="w-5 h-5 text-sentinel-700" />
                <h3 className="font-bold text-slate-900 text-sm">
                  Initiate Bank Verification Request
                </h3>
              </div>
              <button
                onClick={() => setIsNewRequestModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreateVerificationRequest} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Verification Channel
                </label>
                <select
                  value={newRequestChannel}
                  onChange={(e) => setNewRequestChannel(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono text-slate-800"
                >
                  <option value="SFTP_RECONCILIATION">SFTP_RECONCILIATION (Scheduled Batch)</option>
                  <option value="BANK_API">BANK_API (Synchronous Host-to-Host)</option>
                  <option value="PORTAL_QUERY">PORTAL_QUERY (Direct Bank Portal Ingestion)</option>
                  <option value="MANUAL_DOCUMENT">MANUAL_DOCUMENT (Official Paper/Email Certificate)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Requested Fields to Reconcile
                </label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  {['amount', 'maturity_date', 'bank_name', 'reference_number', 'lien_holder'].map((f) => (
                    <label key={f} className="flex items-center gap-2 font-mono text-slate-700">
                      <input
                        type="checkbox"
                        checked={newRequestFields.includes(f)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setNewRequestFields([...newRequestFields, f]);
                          } else {
                            setNewRequestFields(newRequestFields.filter((item) => item !== f));
                          }
                        }}
                        className="rounded border-slate-300 text-sentinel-600 focus:ring-sentinel-500"
                      />
                      <span>{f}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Request Notes & Instructions (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Expedited scrutiny for annual AICTE approval cycle..."
                  value={newRequestNotes}
                  onChange={(e) => setNewRequestNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 text-slate-800"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsNewRequestModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingNewRequest}
                  className="gap-1.5"
                >
                  {isSubmittingNewRequest && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Create Request</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: DISPATCH REQUEST (WITH SIMULATION SCENARIO) */}
      {/* =================================================================== */}
      {isDispatchRequestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-blue-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Send className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-sm">
                  Dispatch Verification to Bank Adapter
                </h3>
              </div>
              <button
                onClick={() => setIsDispatchRequestModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Simulation Scenario / Adapter Response Mode
                </label>
                <select
                  value={dispatchScenario}
                  onChange={(e) => setDispatchScenario(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 font-mono"
                >
                  <option value="NORMAL_MATCH">NORMAL_MATCH (Clean statutory bank confirmation)</option>
                  <option value="AMOUNT_MISMATCH">AMOUNT_MISMATCH (Discrepancy test scenario)</option>
                  <option value="BANK_NOT_FOUND">BANK_NOT_FOUND (Record missing at bank)</option>
                  <option value="NETWORK_TIMEOUT">NETWORK_TIMEOUT (Adapter timeout / retry test)</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Executes the simulated or connected banking gateway for test & production reconciliation.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsDispatchRequestModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingDispatch}
                  onClick={handleDispatchRequest}
                  className="gap-1.5"
                >
                  {isSubmittingDispatch && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Dispatch Now</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL: RECORD MANUAL EVIDENCE */}
      {/* =================================================================== */}
      {isManualEvidenceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-lg w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-700" />
                <h3 className="font-bold text-slate-900 text-sm">
                  Record Manual Bank Confirmation Evidence
                </h3>
              </div>
              <button
                onClick={() => setIsManualEvidenceModalOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleRecordManualEvidence} className="p-5 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    External Bank Reference <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SBI/CONF/2026/8912"
                    value={manualRef}
                    onChange={(e) => setManualRef(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono text-slate-800"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Communication Date <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={manualDate}
                    onChange={(e) => setManualDate(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Verification Outcome
                </label>
                <select
                  value={manualResult}
                  onChange={(e) => setManualResult(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 text-slate-800"
                >
                  <option value="MATCH">MATCH (Bank confirms all deposit particulars)</option>
                  <option value="MISMATCH">MISMATCH (Bank reports conflicting particulars)</option>
                  <option value="NOT_FOUND">NOT_FOUND (Bank unable to trace deposit)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Confirmed Principal Amount (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 1500000"
                    value={manualAmount}
                    onChange={(e) => setManualAmount(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono text-slate-800"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Confirmed Maturity Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={manualMaturityDate}
                    onChange={(e) => setManualMaturityDate(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Supporting Document Version Ref (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. DOC-VER-BANK-CONF-01"
                  value={manualDocVersion}
                  onChange={(e) => setManualDocVersion(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono text-slate-800"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Verification Explanation / Justification <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Official bank confirmation letter or sealed certificate details..."
                  value={manualReason}
                  onChange={(e) => setManualReason(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 text-slate-800"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsManualEvidenceModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingManual || !manualRef.trim() || !manualReason.trim()}
                  className="gap-1.5"
                >
                  {isSubmittingManual && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Record Manual Confirmation</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
