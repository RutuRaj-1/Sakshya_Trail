import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { instrumentsApi } from '@/api/endpoints';
import { commandCenterApi } from '@/api/commandCenter';
import type { Instrument } from '@/types';
import type {
  InstrumentDetailSnapshotResponse,
  ScrutinyObservationItem,
} from '@/types/commandCenter';
import { Badge } from '@/components/common/Badge';
import { formatINR, formatDate } from '@/lib/utils';
import { InstrumentModal } from '@/features/instruments/InstrumentModal';
import { LifecycleNotificationHistory } from '@/features/lifecycle/LifecycleNotificationHistory';
import { RenewalLineageSection } from '@/features/lifecycle/RenewalLineageSection';
import { NineStageLifecycleTracker } from '@/features/lifecycle/components/NineStageLifecycleTracker';
import { useAuth } from '@/features/auth/AuthContext';
import {
  FileSpreadsheet,
  Building2,
  Calendar,
  ArrowLeft,
  Edit2,
  Shield,
  ShieldCheck,
  AlertTriangle,
  Lock,
  History,
  FileCode,
  Activity,
  MessageSquare,
  Plus,
  CornerDownRight,
  Download,
  Copy,
  Check,
  Clock,
  Layers,
} from 'lucide-react';

export const InstrumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const isScrutinyOfficer = user?.role === 'SCRUTINY_OFFICER';
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';
  const isAuditor = user?.role === 'AUDITOR';
  const canManageObservations = ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'AUDIT_EXAMINER'].includes(
    user?.role || ''
  );

  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [snapshot, setSnapshot] = useState<InstrumentDetailSnapshotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active detail tab
  const [activeTab, setActiveTab] = useState<
    'snapshot' | 'documents' | 'field_history' | 'lineage' | 'observations' | 'audit'
  >('snapshot');

  // Edit Registry Modal
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Scrutiny Observation Modals
  const [isCreateObsModalOpen, setIsCreateObsModalOpen] = useState(false);
  const [obsText, setObsText] = useState('');
  const [obsCategory, setObsCategory] = useState('GENERAL');
  const [obsInternalOnly, setObsInternalOnly] = useState(false);

  // Amend Observation Modal
  const [amendingObs, setAmendingObs] = useState<ScrutinyObservationItem | null>(null);
  const [amendText, setAmendText] = useState('');
  const [amendReason, setAmendReason] = useState('');

  // Resolve Observation Modal
  const [resolvingObs, setResolvingObs] = useState<ScrutinyObservationItem | null>(null);
  const [resolveReason, setResolveReason] = useState('');

  // Hash Copy Feedback
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const [instData, snapData] = await Promise.all([
        instrumentsApi.get(id),
        commandCenterApi.getInstrumentDetailSnapshot(id).catch((err) => {
          console.warn('Snapshot endpoint error; falling back to basic record:', err);
          return null;
        }),
      ]);
      setInstrument(instData);
      setSnapshot(snapData);
    } catch (err: any) {
      setError(
        err?.response?.data?.message || err?.message || 'Failed to retrieve instrument record.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Submit new observation
  const handleCreateObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !obsText.trim()) return;
    try {
      await commandCenterApi.createObservation(id, {
        observation_text: obsText.trim(),
        observation_category: obsCategory,
        is_internal_only: obsInternalOnly,
      });
      setIsCreateObsModalOpen(false);
      setObsText('');
      loadData();
    } catch (err: any) {
      alert(err?.response?.data?.message || 'Failed to record scrutiny observation.');
    }
  };

  // Submit observation amendment (supersession)
  const handleAmendObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amendingObs || !amendText.trim() || !amendReason.trim()) return;
    try {
      await commandCenterApi.amendObservation(amendingObs.id, {
        observation_text: amendText.trim(),
        amendment_reason: amendReason.trim(),
      });
      setAmendingObs(null);
      setAmendText('');
      setAmendReason('');
      loadData();
    } catch (err: any) {
      alert(err?.response?.data?.message || 'Failed to amend observation note.');
    }
  };

  // Submit observation resolution
  const handleResolveObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingObs || !resolveReason.trim()) return;
    try {
      await commandCenterApi.resolveObservation(resolvingObs.id, {
        resolution_reason: resolveReason.trim(),
      });
      setResolvingObs(null);
      setResolveReason('');
      loadData();
    } catch (err: any) {
      alert(err?.response?.data?.message || 'Failed to resolve observation note.');
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center text-[#5D6A75]">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#C9D3DB] border-t-sentinel-600 mb-3" />
        <p className="text-sm font-medium">Retrieving verified statutory FDR instrument & historical snapshot...</p>
      </div>
    );
  }

  if (error || !instrument) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-white rounded-[10px] border border-[#C9D3DB] text-center shadow-xs">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-[#253746]">Instrument Unavailable</h2>
        <p className="text-xs text-[#5D6A75] mt-1 max-w-md mx-auto">{error || 'Record was not found.'}</p>
        <button
          onClick={() => navigate('/instruments')}
          className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-[#253746] text-xs font-semibold rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Registry</span>
        </button>
      </div>
    );
  }

  const isOwnRecord = !isInstitutionUser || user?.institution_id === instrument.institution_id;
  const canEdit =
    (isSystemAdmin || isScrutinyOfficer || (isInstitutionUser && isOwnRecord)) &&
    ['DRAFT', 'REGISTERED'].includes(instrument.status);

  return (
    <div className="space-y-6 max-w-6xl mx-auto text-xs pb-16">
      {/* Top Action Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-[#5D6A75] hover:text-[#0D2538] font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Previous Page</span>
        </button>

        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#8799A9] bg-white hover:bg-[#F5F4EF] text-[#253746] font-semibold shadow-2xs transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>Edit Registry Information</span>
            </button>
          )}
        </div>
      </div>

      {/* Nine-Stage Lifecycle Tracker for this instrument */}
      <NineStageLifecycleTracker
        mode="instrument"
        instrument={instrument}
        snapshot={snapshot}
        onNavigateTab={(tabKey) => setActiveTab(tabKey as any)}
      />

      {/* Main FDR Certificate Header Card */}
      <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-[10px] bg-[#EEF6FA] border border-sentinel-100 text-[#123B5D] flex items-center justify-center shrink-0">
              <FileSpreadsheet className="w-7 h-7" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm px-2.5 py-0.5 rounded bg-slate-900 text-white font-bold tracking-wider">
                  {instrument.reference_number}
                </span>
                {/* Administrative Status */}
                <Badge variant={instrument.status === 'REGISTERED' ? 'info' : 'default'}>
                  {instrument.status}
                </Badge>
                {/* Trust Level */}
                <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-200">
                  <Shield className="w-3 h-3 text-purple-700" />
                  <span>{instrument.trust_level.replace('_', ' — ')}</span>
                </span>
              </div>
              <h1 className="text-xl font-bold text-[#0D2538] mt-1.5">
                {instrument.bank_name} {instrument.branch ? `— ${instrument.branch}` : ''}
              </h1>
              <p className="text-[#5D6A75] text-xs">
                Pledged on behalf of{' '}
                <span className="font-semibold text-[#253746]">
                  {instrument.institution_name || instrument.institution_id}
                </span>{' '}
                {instrument.institution_code && `(${instrument.institution_code})`}
              </p>
            </div>
          </div>

          <div className="text-left sm:text-right space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold block">
              Statutory Deposit Principal
            </span>
            <div className="text-2xl font-black text-[#0D2538] font-mono">
              {formatINR(Number(instrument.amount))}
            </div>
            <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-medium inline-block">
              100% Precise Decimal Storage
            </span>
          </div>
        </div>

        {/* Multi-Dimensional Status Clarity Notice */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3 rounded-[10px] bg-[#F5F4EF] border border-[#C9D3DB]">
          <div className="p-2.5 bg-white rounded-lg border border-[#C9D3DB]/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">1. Administrative State</span>
            <span className="text-xs font-bold text-[#253746]">{instrument.status}</span>
            <p className="text-[10px] text-[#5D6A75] mt-0.5">Procedural stage in the regulatory deposit registry.</p>
          </div>
          <div className="p-2.5 bg-white rounded-lg border border-[#C9D3DB]/80">
            <span className="text-[10px] uppercase font-bold text-purple-600 block">2. Evidentiary Trust Level</span>
            <span className="text-xs font-bold text-purple-800">{instrument.trust_level}</span>
            <p className="text-[10px] text-[#5D6A75] mt-0.5">Degree of multi-tier verification (L0 declared to L3 bank confirmed).</p>
          </div>
          <div className="p-2.5 bg-white rounded-lg border border-[#C9D3DB]/80">
            <span className="text-[10px] uppercase font-bold text-amber-600 block">3. Maturity / Term Window</span>
            <span className="text-xs font-bold text-amber-800">{instrument.maturity_indicator || 'ACTIVE'}</span>
            <p className="text-[10px] text-[#5D6A75] mt-0.5">Statutory validity and calendar expiry timeline.</p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[#C9D3DB] overflow-x-auto pb-1">
        <button
          onClick={() => setActiveTab('snapshot')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeTab === 'snapshot'
              ? 'bg-[#0F766E] text-white shadow-xs'
              : 'text-[#5D6A75] hover:bg-slate-100'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Current Snapshot & Registry</span>
        </button>

        <button
          onClick={() => setActiveTab('documents')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeTab === 'documents'
              ? 'bg-[#0F766E] text-white shadow-xs'
              : 'text-[#5D6A75] hover:bg-slate-100'
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          <span>Documents &amp; Hashes ({snapshot?.documents?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('field_history')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeTab === 'field_history'
              ? 'bg-[#0F766E] text-white shadow-xs'
              : 'text-[#5D6A75] hover:bg-slate-100'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Field Provenance ({snapshot?.field_history?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('lineage')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeTab === 'lineage'
              ? 'bg-[#0F766E] text-white shadow-xs'
              : 'text-[#5D6A75] hover:bg-slate-100'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Lifecycle &amp; Lineage ({snapshot?.lifecycle_lineage?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('observations')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeTab === 'observations'
              ? 'bg-[#0F766E] text-white shadow-xs'
              : 'text-[#5D6A75] hover:bg-slate-100'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Scrutiny Observations ({snapshot?.observations?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeTab === 'audit'
              ? 'bg-[#0F766E] text-white shadow-xs'
              : 'text-[#5D6A75] hover:bg-slate-100'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Audit Timeline ({snapshot?.timeline?.length || 0})</span>
        </button>
      </div>

      {/* =====================================================================
          TAB 1: Current Snapshot & Registry Details
          ===================================================================== */}
      {activeTab === 'snapshot' && (
        <div className="space-y-6">
          {/* Active Discrepancies Alert if present */}
          {snapshot?.instrument?.active_findings && snapshot.instrument.active_findings.length > 0 && (
            <div className="bg-rose-50 border border-rose-200 rounded-[10px] p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  <h4 className="font-bold text-rose-900 text-xs">
                    Active Discrepancy Findings ({snapshot.instrument.active_findings.length})
                  </h4>
                </div>
                <Link
                  to="/findings/queue"
                  className="text-[11px] font-semibold text-rose-700 hover:text-rose-900 underline"
                >
                  Open Review Queue
                </Link>
              </div>
              <div className="divide-y divide-rose-100">
                {snapshot.instrument.active_findings.map((f) => (
                  <div key={f.id} className="py-2 flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-[10px] px-1.5 py-0.5 rounded bg-rose-200 text-rose-800">
                          {f.rule_code}
                        </span>
                        <span className="font-semibold text-rose-900">{f.message}</span>
                      </div>
                      {f.field_name && (
                        <span className="text-[10px] text-rose-600">Affected field: {f.field_name}</span>
                      )}
                    </div>
                    <span className="font-mono text-[10px] uppercase font-bold text-rose-700">
                      {f.severity}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Attribute Columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs p-6">
            {/* Term Dates & Derived Maturity */}
            <div className="space-y-3">
              <h3 className="font-bold text-[#0D2538] uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-[#123B5D]" />
                <span>Deposit Term &amp; Dates</span>
              </h3>

              <div className="bg-[#F5F4EF]/70 rounded-[10px] p-4 border border-[#C9D3DB]/80 space-y-2.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-[#5D6A75] font-sans">Issue Date</span>
                  <span className="font-medium text-[#253746]">{formatDate(instrument.issue_date)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#5D6A75] font-sans">Maturity Date</span>
                  <span className="font-bold text-[#0D2538]">{formatDate(instrument.maturity_date)}</span>
                </div>
                <div className="flex justify-between items-center pt-1 border-t border-[#C9D3DB]">
                  <span className="text-[#5D6A75] font-sans">Derived Window</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      instrument.maturity_indicator === 'ACTIVE'
                        ? 'bg-emerald-100 text-emerald-800'
                        : instrument.maturity_indicator === 'EXPIRING_SOON'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {instrument.maturity_indicator || 'ACTIVE'}
                  </span>
                </div>
              </div>
            </div>

            {/* Lien & Pledge Clausing */}
            <div className="space-y-3">
              <h3 className="font-bold text-[#0D2538] uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                <Lock className="w-4 h-4 text-[#123B5D]" />
                <span>Statutory Lien Marking</span>
              </h3>

              <div className="bg-[#F5F4EF]/70 rounded-[10px] p-4 border border-[#C9D3DB]/80 space-y-2.5">
                <div className="flex justify-between">
                  <span className="text-[#5D6A75]">Lien Holder</span>
                  <span className="font-semibold text-[#253746]">{instrument.lien_holder}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#5D6A75]">Joint Holding</span>
                  <span className="text-emerald-700 font-medium">
                    {instrument.joint_with_aicte ? 'Joint with AICTE' : 'Sole Holding'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#5D6A75]">Regional Office</span>
                  <span className="text-[#253746]">
                    {instrument.assigned_office || 'Headquarters / Unassigned'}
                  </span>
                </div>
              </div>
            </div>

            {/* Linked Parent Entity */}
            <div className="space-y-3">
              <h3 className="font-bold text-[#0D2538] uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-[#123B5D]" />
                <span>Parent Institution Entity</span>
              </h3>

              <div className="bg-[#F5F4EF]/70 rounded-[10px] p-4 border border-[#C9D3DB]/80 space-y-2.5">
                <div className="flex justify-between">
                  <span className="text-[#5D6A75]">Permanent Code</span>
                  <span className="font-mono text-[#123B5D] font-bold">
                    {instrument.institution_code || 'ID Recorded'}
                  </span>
                </div>
                <div className="text-[#253746] font-medium truncate">
                  {instrument.institution_name}
                </div>
                <div className="flex justify-between text-[#5D6A75] text-[10px] pt-1 border-t border-[#C9D3DB]">
                  <span>Created: {new Date(instrument.created_at).toLocaleDateString()}</span>
                  <span>Updated: {new Date(instrument.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Module 4 Bank Confirmation & Trust Desk Link */}
          <div className="bg-white rounded-[10px] border border-purple-200 p-5 space-y-3 shadow-2xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-purple-600" />
                <h4 className="font-bold text-[#253746] text-xs">Trust &amp; Bank Verification Desk</h4>
              </div>
              <span className="font-mono text-[9px] uppercase bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded font-semibold border border-purple-200">
                Module 4 Active
              </span>
            </div>

            <div className="p-4 border border-purple-100 rounded-[10px] bg-purple-50/30 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#5D6A75] font-medium">Assessed Trust Level:</span>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white text-purple-800 border border-purple-200 shadow-2xs">
                  {instrument.trust_level}
                </span>
              </div>
              <p className="text-[11px] text-[#5D6A75]">
                {instrument.trust_level === 'L3_BANK_CONFIRMED'
                  ? 'Authoritative host-to-host bank confirmation verified. Statutory deposit guaranteed.'
                  : instrument.trust_level === 'L2_OFFICER_VERIFIED'
                  ? 'Scrutiny officer reviewed and attested. Ready for direct electronic bank confirmation.'
                  : instrument.trust_level === 'L1_DOCUMENT_CONSISTENT'
                  ? 'Document OCR validation passed. Pending officer attestation and bank reconciliation.'
                  : 'Declared FDR record. Electronic bank confirmation and provenance tracking available.'}
              </p>
              <div className="pt-2">
                <Link
                  to={`/verification/${instrument.id}`}
                  className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 text-xs font-semibold rounded-lg bg-purple-700 text-white hover:bg-purple-800 transition-colors shadow-2xs"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Open Trust &amp; Verification Desk</span>
                </Link>
              </div>
            </div>
          </div>

          {/* Renewal Lineage Section */}
          <RenewalLineageSection
            instrumentId={instrument.id}
            predecessorRecord={{
              id: instrument.id,
              reference_number: instrument.reference_number,
              bank_name: instrument.bank_name,
              branch: instrument.branch,
              amount: instrument.amount,
              currency: instrument.currency,
              issue_date: instrument.issue_date,
              maturity_date: instrument.maturity_date,
              status: instrument.status,
              trust_level: instrument.trust_level,
              institution_id: instrument.institution_id,
            }}
            canInitiateRenewal={isSystemAdmin || isScrutinyOfficer || (isInstitutionUser && isOwnRecord)}
            isOfficerOrAdmin={isSystemAdmin || isScrutinyOfficer}
            onRefreshParent={loadData}
          />

          {/* Notification History */}
          <LifecycleNotificationHistory
            instrumentId={instrument.id}
            isOfficerOrAdmin={isSystemAdmin || isScrutinyOfficer}
          />
        </div>
      )}

      {/* =====================================================================
          TAB 2: Document History & SHA-256 Hashes
          ===================================================================== */}
      {activeTab === 'documents' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-[#0D2538] text-sm">Versioned Document Certificates &amp; Scans</h3>
              <p className="text-[#5D6A75] text-xs mt-0.5">
                Every file upload is permanently versioned with cryptographic SHA-256 byte verification.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] bg-slate-100 text-[#5D6A75] px-2.5 py-1 rounded-lg font-semibold">
                Protected Object Storage
              </span>
            </div>
          </div>

          {!snapshot?.documents || snapshot.documents.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <FileCode className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No documents registered for this instrument</p>
              <p className="text-slate-400 text-[11px] max-w-sm mx-auto mt-1">
                Upload fixed deposit scans, bank confirmation letters, or renewal notices.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] tracking-wider font-semibold border-b border-[#C9D3DB]">
                    <th className="px-6 py-3">Version</th>
                    <th className="px-6 py-3">Category</th>
                    <th className="px-6 py-3">Filename</th>
                    <th className="px-6 py-3">Uploaded By</th>
                    <th className="px-6 py-3">Upload Time</th>
                    <th className="px-6 py-3">SHA-256 Hash</th>
                    <th className="px-6 py-3 text-right">Protected Access</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {snapshot.documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-[#F5F4EF]/70 transition-colors">
                      <td className="px-6 py-3.5">
                        <span className="font-bold text-[#123B5D] bg-[#EEF6FA] border border-[#C4DEED] px-2 py-0.5 rounded text-xs">
                          v{doc.version_number}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 font-sans font-medium text-[#253746]">
                        {doc.category}
                      </td>
                      <td className="px-6 py-3.5 font-sans text-[#253746]">
                        {doc.file_name || 'certificate.pdf'}
                        {doc.file_size_bytes && (
                          <span className="block text-[10px] text-slate-400">
                            {(doc.file_size_bytes / 1024).toFixed(1)} KB
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 font-sans text-[#5D6A75]">
                        {doc.uploader_name || doc.uploader_user_id || 'Uploader'}
                      </td>
                      <td className="px-6 py-3.5 text-[#5D6A75] text-[11px]">
                        {formatDate(doc.uploaded_at)}
                      </td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-1.5">
                          <code className="text-[10px] bg-slate-100 text-[#253746] px-1.5 py-0.5 rounded font-mono border border-[#C9D3DB]">
                            {doc.sha256_hash.slice(0, 16)}...
                          </code>
                          <button
                            onClick={() => handleCopyHash(doc.sha256_hash)}
                            title="Copy full SHA-256 hash"
                            className="p-1 text-slate-400 hover:text-[#253746] transition-colors"
                          >
                            {copiedHash === doc.sha256_hash ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-right font-sans">
                        <a
                          href={doc.download_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-[#253746] font-semibold text-xs transition-colors"
                        >
                          <Download className="w-3 h-3" />
                          <span>Download</span>
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 3: Field Provenance History
          ===================================================================== */}
      {activeTab === 'field_history' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <h3 className="font-bold text-[#0D2538] text-sm">Audited Field Modification History</h3>
            <p className="text-[#5D6A75] text-xs mt-0.5">
              Tracks field mutations, previous vs new values, source actors, and policy-governed data masking.
            </p>
          </div>

          {!snapshot?.field_history || snapshot.field_history.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <History className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No field history records found</p>
              <p className="text-slate-400 text-[11px] max-w-sm mx-auto mt-1">
                Field changes will be logged here with source provenance when registry attributes are updated.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] tracking-wider font-semibold border-b border-[#C9D3DB]">
                    <th className="px-6 py-3">Field Name</th>
                    <th className="px-6 py-3">Recorded Value</th>
                    <th className="px-6 py-3">Previous Value</th>
                    <th className="px-6 py-3">Source &amp; Actor</th>
                    <th className="px-6 py-3">Change Reason / Evidence</th>
                    <th className="px-6 py-3 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {snapshot.field_history.map((fh) => (
                    <tr key={fh.id} className="hover:bg-[#F5F4EF]/70 transition-colors">
                      <td className="px-6 py-3.5 font-bold text-[#0D2538]">
                        {fh.field_name}
                      </td>
                      <td className="px-6 py-3.5 text-[#253746]">
                        <span className="bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
                          {fh.recorded_value}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-[#5D6A75]">
                        {fh.previous_value ? (
                          <span className="line-through bg-slate-100 text-[#5D6A75] px-2 py-0.5 rounded">
                            {fh.previous_value}
                          </span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 font-sans">
                        <span className="font-semibold text-[#253746]">{fh.actor_name || fh.source_actor_id || 'System'}</span>
                        <span className="block text-[10px] text-slate-400">{fh.source_type}</span>
                      </td>
                      <td className="px-6 py-3.5 font-sans text-[#5D6A75] max-w-xs">
                        {fh.reason || fh.evidence_reference || <span className="text-slate-300">—</span>}
                      </td>
                      <td className="px-6 py-3.5 text-right text-[#5D6A75] text-[11px]">
                        {formatDate(fh.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 4: Lifecycle & Lineage History (with SIMULATED highlighting)
          ===================================================================== */}
      {activeTab === 'lineage' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs p-6 space-y-4">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-[#0D2538] text-sm">Lifecycle Lineage &amp; Verification Chain</h3>
            <p className="text-[#5D6A75] text-xs mt-0.5">
              Distinguishes production host-to-host verifications from simulated bank responses, renewal lineage, and automated maturity evaluations.
            </p>
          </div>

          {!snapshot?.lifecycle_lineage || snapshot.lifecycle_lineage.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <Activity className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No lifecycle events recorded</p>
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              {snapshot.lifecycle_lineage.map((ev, idx) => (
                <div key={idx} className="relative group">
                  <div
                    className={`absolute -left-6 top-1 w-4 h-4 rounded-full border-2 bg-white ${
                      ev.is_simulated
                        ? 'border-amber-500 ring-2 ring-amber-200'
                        : 'border-sentinel-600'
                    }`}
                  />
                  <div className="bg-[#F5F4EF]/70 border border-[#C9D3DB] rounded-[10px] p-4 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-slate-200 text-[#253746]">
                          {ev.event_type}
                        </span>
                        {ev.is_simulated && (
                          <span className="font-mono text-[10px] font-black px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 uppercase">
                            SIMULATED ADAPTER
                          </span>
                        )}
                        <span className="text-[#5D6A75] text-[11px]">Actor: {ev.actor_id || 'System'}</span>
                      </div>
                      <span className="font-mono text-[11px] text-[#5D6A75]">{formatDate(ev.timestamp)}</span>
                    </div>

                    <p className="font-medium text-[#253746] text-xs">{ev.summary}</p>

                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <div className="pt-2 text-[11px] font-mono text-[#5D6A75] bg-white p-2.5 rounded-lg border border-[#C9D3DB]/80">
                        {Object.entries(ev.details).map(([k, v]) => (
                          <div key={k} className="flex justify-between py-0.5">
                            <span className="text-slate-400">{k}:</span>
                            <span className="font-bold text-[#253746]">{String(v)}</span>
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

      {/* =====================================================================
          TAB 5: Append-Only Scrutiny Observations
          ===================================================================== */}
      {activeTab === 'observations' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-[#0D2538] text-sm">Append-Only Regulatory Scrutiny Observations</h3>
              <p className="text-[#5D6A75] text-xs mt-0.5">
                Observations retain immutable authorship. Revisions and amendments create explicit superseding chains without erasing history.
              </p>
            </div>

            {canManageObservations && (
              <button
                onClick={() => setIsCreateObsModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-[10px] bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold text-xs transition-colors shadow-2xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Record Scrutiny Note</span>
              </button>
            )}
          </div>

          {!snapshot?.observations || snapshot.observations.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <MessageSquare className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No scrutiny observations recorded</p>
              <p className="text-slate-400 text-[11px] max-w-sm mx-auto mt-1">
                Authorized scrutiny officers and system administrators can log regulatory notes and compliance findings here.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {snapshot.observations.map((obs) => (
                <div
                  key={obs.id}
                  className={`rounded-[10px] border p-5 space-y-3 transition-colors ${
                    obs.status === 'SUPERSEDED'
                      ? 'bg-[#F5F4EF]/60 border-[#C9D3DB] opacity-75'
                      : obs.status === 'RESOLVED'
                      ? 'bg-emerald-50/40 border-emerald-200'
                      : 'bg-white border-[#C9D3DB] shadow-2xs'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-900 text-white">
                        {obs.observation_category}
                      </span>
                      <Badge
                        variant={
                          obs.status === 'RECORDED'
                            ? 'info'
                            : obs.status === 'AMENDED'
                            ? 'purple'
                            : obs.status === 'RESOLVED'
                            ? 'success'
                            : 'default'
                        }
                      >
                        {obs.status}
                      </Badge>
                      {obs.is_internal_only && (
                        <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-200">
                          INTERNAL ONLY
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                      <span>{formatDate(obs.created_at)}</span>
                    </div>
                  </div>

                  {/* Note Body */}
                  <div className="text-xs text-[#253746] leading-relaxed font-sans bg-[#F5F4EF]/50 p-3 rounded-[10px] border border-slate-100">
                    {obs.observation_text}
                  </div>

                  {/* Author provenance */}
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#5D6A75] pt-1">
                    <div>
                      <span>Logged by: </span>
                      <strong className="text-[#253746]">{obs.author_name || obs.author_user_id}</strong>
                      <span className="ml-1 text-slate-400 font-mono">({obs.author_role})</span>
                    </div>

                    {/* Superseded or Resolution lineage */}
                    {obs.supersedes_id && (
                      <div className="flex items-center gap-1 text-purple-700 font-semibold font-mono text-[10px]">
                        <CornerDownRight className="w-3.5 h-3.5" />
                        <span>Supersedes Note #{obs.supersedes_id.slice(0, 8)}</span>
                      </div>
                    )}
                    {obs.superseded_by_id && (
                      <div className="text-amber-800 font-semibold font-mono text-[10px]">
                        Amended by Note #{obs.superseded_by_id.slice(0, 8)}
                      </div>
                    )}
                    {obs.resolved_at && (
                      <div className="text-emerald-700 font-semibold text-[11px]">
                        Resolved on {formatDate(obs.resolved_at)} ({obs.resolution_reason})
                      </div>
                    )}
                  </div>

                  {/* Actions for active notes */}
                  {canManageObservations && !isAuditor && obs.status !== 'SUPERSEDED' && obs.status !== 'RESOLVED' && (
                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                      <button
                        onClick={() => {
                          setAmendingObs(obs);
                          setAmendText(obs.observation_text);
                          setAmendReason('');
                        }}
                        className="px-3 py-1.5 rounded-lg border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] font-semibold text-[11px] transition-colors"
                      >
                        Amend / Supersede Note
                      </button>
                      <button
                        onClick={() => {
                          setResolvingObs(obs);
                          setResolveReason('');
                        }}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] transition-colors"
                      >
                        Resolve Note
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 6: Chronological Audit Timeline
          ===================================================================== */}
      {activeTab === 'audit' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs p-6 space-y-4">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-[#0D2538] text-sm">Material Regulatory Audit Trail</h3>
            <p className="text-[#5D6A75] text-xs mt-0.5">
              Historical ledger of administrative actions, status transitions, and user events for this deposit instrument.
            </p>
          </div>

          {!snapshot?.timeline || snapshot.timeline.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <Clock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No audit events recorded</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {snapshot.timeline.map((item, idx) => (
                <div key={idx} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-[#0D2538]">{item.event_type}</span>
                      <span className="text-slate-400">•</span>
                      <span className="text-[#5D6A75]">{item.summary}</span>
                    </div>
                    <span className="text-[10px] text-slate-400">Actor: {item.actor_id || 'SYSTEM'}</span>
                  </div>
                  <span className="font-mono text-[#5D6A75] text-[11px] whitespace-nowrap">
                    {formatDate(item.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          MODALS
          ===================================================================== */}

      {/* Create Observation Modal */}
      {isCreateObsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] max-w-lg w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[#0D2538]">Record Scrutiny Observation</h3>
            <form onSubmit={handleCreateObservation} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Observation Category
                </label>
                <select
                  value={obsCategory}
                  onChange={(e) => setObsCategory(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#8799A9] bg-white text-xs text-[#253746]"
                >
                  <option value="GENERAL">GENERAL — General Observation</option>
                  <option value="DISCREPANCY">DISCREPANCY — Discrepancy Note</option>
                  <option value="DOCUMENT">DOCUMENT — Document Evidence Issue</option>
                  <option value="MANDATE">MANDATE — Statutory Lien / Mandate</option>
                  <option value="COMPLIANCE">COMPLIANCE — AICTE Norms Compliance</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Observation Content (Immutable)
                </label>
                <textarea
                  required
                  rows={4}
                  value={obsText}
                  onChange={(e) => setObsText(e.target.value)}
                  placeholder="Enter detailed scrutiny observation findings..."
                  className="w-full px-3 py-2 rounded-lg border border-[#8799A9] text-xs text-[#253746] focus:ring-1 focus:ring-sentinel-500"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={obsInternalOnly}
                  onChange={(e) => setObsInternalOnly(e.target.checked)}
                  className="rounded border-[#8799A9] text-[#123B5D] w-4 h-4"
                />
                <span className="text-[#253746] font-medium text-[11px]">
                  Internal Bureau Use Only (Hidden from Institution)
                </span>
              </label>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCreateObsModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold text-xs"
                >
                  Record Observation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Amend Observation Modal */}
      {amendingObs && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] max-w-lg w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[#0D2538]">Amend Scrutiny Note (Append-Only)</h3>
            <p className="text-[11px] text-[#5D6A75]">
              The existing note will be preserved and linked as superseded. A new revision note will be authored under your credentials.
            </p>

            <div className="p-3 bg-[#F5F4EF] rounded-[10px] border border-[#C9D3DB] text-[#5D6A75] text-[11px]">
              <span className="font-semibold block text-[#253746]">Original Note:</span>
              {amendingObs.observation_text}
            </div>

            <form onSubmit={handleAmendObservation} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Amended Observation Text
                </label>
                <textarea
                  required
                  rows={4}
                  value={amendText}
                  onChange={(e) => setAmendText(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[#8799A9] text-xs text-[#253746]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Mandatory Amendment Rationale
                </label>
                <input
                  type="text"
                  required
                  value={amendReason}
                  onChange={(e) => setAmendReason(e.target.value)}
                  placeholder="e.g. Corrected deposit branch IFSC code following bank attestation"
                  className="w-full px-3 py-2 rounded-lg border border-[#8799A9] text-xs text-[#253746]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setAmendingObs(null)}
                  className="px-3.5 py-2 rounded-lg border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold text-xs"
                >
                  Commit Amendment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resolve Observation Modal */}
      {resolvingObs && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-[#0D2538]">Resolve Scrutiny Note</h3>
            <p className="text-[11px] text-[#5D6A75]">
              Provide an authoritative justification for marking this regulatory observation as resolved.
            </p>

            <form onSubmit={handleResolveObservation} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Resolution Justification
                </label>
                <textarea
                  required
                  rows={3}
                  value={resolveReason}
                  onChange={(e) => setResolveReason(e.target.value)}
                  placeholder="e.g. Verified original FDR deposit slip matching AICTE statutory amount."
                  className="w-full px-3 py-2 rounded-lg border border-[#8799A9] text-xs text-[#253746]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setResolvingObs(null)}
                  className="px-3.5 py-2 rounded-lg border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs"
                >
                  Mark Resolved
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Registry Information Modal */}
      <InstrumentModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={loadData}
        instrumentToEdit={instrument}
      />
    </div>
  );
};
