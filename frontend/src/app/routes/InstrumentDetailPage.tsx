import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { instrumentsApi } from '@/api/endpoints';
import type { Instrument } from '@/types';
import { Badge } from '@/components/common/Badge';
import { formatINR, formatDate } from '@/lib/utils';
import { InstrumentModal } from '@/features/instruments/InstrumentModal';
import { LifecycleNotificationHistory } from '@/features/lifecycle/LifecycleNotificationHistory';
import { RenewalLineageSection } from '@/features/lifecycle/RenewalLineageSection';
import { useAuth } from '@/features/auth/AuthContext';
import {
  FileSpreadsheet,
  Building2,
  Calendar,
  ArrowLeft,
  Edit2,
  Shield,
  ShieldCheck,
  FileCheck2,
  FileText,
  AlertTriangle,
  Lock,
  Send,
} from 'lucide-react';

export const InstrumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const isScrutinyOfficer = user?.role === 'SCRUTINY_OFFICER';
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';

  const [instrument, setInstrument] = useState<Instrument | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const loadInstrument = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await instrumentsApi.get(id);
      setInstrument(data);
    } catch (err: any) {
      setError(
        err?.response?.data?.message || err?.message || 'Failed to retrieve instrument record.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadInstrument();
  }, [loadInstrument]);

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
        <p className="text-sm font-medium">Retrieving verified statutory FDR instrument...</p>
      </div>
    );
  }

  if (error || !instrument) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-white rounded-2xl border border-slate-200 text-center shadow-xs">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-slate-800">Instrument Unavailable</h2>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{error || 'Record was not found.'}</p>
        <button
          onClick={() => navigate('/instruments')}
          className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Instrument Registry</span>
        </button>
      </div>
    );
  }

  const isOwnRecord = !isInstitutionUser || user?.institution_id === instrument.institution_id;
  const canEdit = (isSystemAdmin || isScrutinyOfficer || (isInstitutionUser && isOwnRecord)) && ['DRAFT', 'REGISTERED'].includes(instrument.status);

  return (
    <div className="space-y-6 max-w-5xl mx-auto text-xs">
      {/* Top Action Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/instruments')}
          className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to FDR Instruments</span>
        </button>

        {canEdit && (
          <button
            onClick={() => setIsEditModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold shadow-2xs transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
            <span>Edit Registry Information</span>
          </button>
        )}
      </div>

      {/* Main FDR Certificate Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-sentinel-50 border border-sentinel-100 text-sentinel-700 flex items-center justify-center shrink-0">
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
              <h1 className="text-xl font-bold text-slate-900 mt-1.5">
                {instrument.bank_name} {instrument.branch ? `— ${instrument.branch}` : ''}
              </h1>
              <p className="text-slate-500 text-xs">
                Pledged on behalf of{' '}
                <span className="font-semibold text-slate-800">
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
            <div className="text-2xl font-black text-slate-900 font-mono">
              {formatINR(Number(instrument.amount))}
            </div>
            <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-medium inline-block">
              100% Precise Decimal Storage
            </span>
          </div>
        </div>

        {/* Detailed Attribute Columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Term Dates & Derived Maturity */}
          <div className="space-y-3">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-sentinel-600" />
              <span>Deposit Term & Maturity Window</span>
            </h3>

            <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-200/80 space-y-2.5 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Issue Date</span>
                <span className="font-medium text-slate-800">{formatDate(instrument.issue_date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-sans">Maturity Date</span>
                <span className="font-bold text-slate-900">{formatDate(instrument.maturity_date)}</span>
              </div>
              <div className="flex justify-between items-center pt-1 border-t border-slate-200">
                <span className="text-slate-500 font-sans">Derived Window</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  instrument.maturity_indicator === 'ACTIVE'
                    ? 'bg-emerald-100 text-emerald-800'
                    : instrument.maturity_indicator === 'EXPIRING_SOON'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-rose-100 text-rose-800'
                }`}>
                  {instrument.maturity_indicator}
                </span>
              </div>
            </div>
          </div>

          {/* Lien & Pledge Clausing */}
          <div className="space-y-3">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-sentinel-600" />
              <span>Statutory Lien Marking</span>
            </h3>

            <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-200/80 space-y-2.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Lien Holder</span>
                <span className="font-semibold text-slate-800">{instrument.lien_holder}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Joint Holding</span>
                <span className="text-emerald-700 font-medium">
                  {instrument.joint_with_aicte ? 'Joint with AICTE' : 'Sole Holding'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Regional Office</span>
                <span className="text-slate-800">
                  {instrument.assigned_office || 'Headquarters / Unassigned'}
                </span>
              </div>
              {instrument.lien_details && (
                <div className="pt-1 text-[11px] text-slate-500 border-t border-slate-200">
                  {instrument.lien_details}
                </div>
              )}
            </div>
          </div>

          {/* Linked Parent Entity */}
          <div className="space-y-3">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-sentinel-600" />
              <span>Parent Institution Entity</span>
            </h3>

            <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-200/80 space-y-2.5">
              <div className="flex justify-between">
                <span className="text-slate-500">AICTE Permanent Code</span>
                <span className="font-mono text-sentinel-700 font-bold">
                  {instrument.institution_code || 'ID Recorded'}
                </span>
              </div>
              <div className="text-slate-800 font-medium truncate">
                {instrument.institution_name}
              </div>
              <div className="flex justify-between text-slate-500 text-[10px] pt-1 border-t border-slate-200">
                <span>Created: {new Date(instrument.created_at).toLocaleDateString()}</span>
                <span>Updated: {new Date(instrument.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Structured Placeholder Sections for Future Modules */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Module 2 File Pipeline Placeholder */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-500" />
              <h4 className="font-bold text-slate-800 text-xs">Document Evidence & Scans</h4>
            </div>
            <span className="font-mono text-[9px] uppercase bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-semibold">
              Future Module 2
            </span>
          </div>
          <div className="p-5 border-2 border-dashed border-slate-200 rounded-xl text-center bg-slate-50/50">
            <FileText className="w-7 h-7 text-slate-300 mx-auto mb-1.5" />
            <p className="text-[11px] font-semibold text-slate-700">No Physical Certificates Uploaded</p>
            <p className="text-[10px] text-slate-500 max-w-xs mx-auto mt-0.5">
              Document ingestion, PDF/TIFF integrity hashing (SHA-256), and optical character recognition belong to the Module 2 file pipeline.
            </p>
          </div>
        </div>

        {/* Module 3 Scrutiny Verification Pipeline Placeholder */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-4 h-4 text-slate-500" />
              <h4 className="font-bold text-slate-800 text-xs">Bureau Scrutiny & Verification</h4>
            </div>
            <span className="font-mono text-[9px] uppercase bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-semibold">
              Future Module 3
            </span>
          </div>
          <div className="p-5 border-2 border-dashed border-slate-200 rounded-xl text-center bg-slate-50/50">
            <FileCheck2 className="w-7 h-7 text-slate-300 mx-auto mb-1.5" />
            <p className="text-[11px] font-semibold text-slate-700">Verification Pipeline Inactive</p>
            <p className="text-[10px] text-slate-500 max-w-xs mx-auto mt-0.5">
              Multi-tier regulatory scrutiny queues, discrepancy notices, and elevation from L0 to L1/L2 belong to Module 3.
            </p>
          </div>
        </div>

        {/* Module 4 Bank Confirmation & Trust Desk */}
        <div className="bg-white rounded-2xl border border-purple-200 p-5 space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-purple-600" />
              <h4 className="font-bold text-slate-800 text-xs">Trust & Bank Verification Desk</h4>
            </div>
            <span className="font-mono text-[9px] uppercase bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded font-semibold border border-purple-200">
              Module 4 Active
            </span>
          </div>

          <div className="p-4 border border-purple-100 rounded-xl bg-purple-50/30 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 font-medium">Assessed Trust Level:</span>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white text-purple-800 border border-purple-200 shadow-2xs">
                {instrument.trust_level}
              </span>
            </div>
            <p className="text-[11px] text-slate-600">
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
                <span>Open Trust & Verification Desk</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Module 5 Renewal & Release Lifecycle Summary Card */}
        <div className="bg-white rounded-2xl border border-emerald-200 p-5 space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Send className="w-4 h-4 text-emerald-600" />
              <h4 className="font-bold text-slate-800 text-xs">Renewal & Release Lifecycle</h4>
            </div>
            <span className="font-mono text-[9px] uppercase bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-semibold border border-emerald-200">
              Module 5 Active
            </span>
          </div>

          <div className="p-4 border border-emerald-100 rounded-xl bg-emerald-50/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 font-medium">Lifecycle Monitoring:</span>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-white text-emerald-800 border border-emerald-200 shadow-2xs">
                {instrument.maturity_indicator || 'ACTIVE'}
              </span>
            </div>
            <p className="text-[11px] text-slate-600">
              Statutory renewal tracking, policy-governed milestones, escalation triggers, and auditable delivery receipts active.
            </p>
          </div>
        </div>
      </div>

      {/* Module 5 Renewal & Replacement Lineage (Predecessor/Successor Chain & Gap/Overlap) */}
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
        onRefreshParent={loadInstrument}
      />

      {/* Module 5 Policy-Driven Notification History & Escalation View */}
      <LifecycleNotificationHistory
        instrumentId={instrument.id}
        isOfficerOrAdmin={isSystemAdmin || isScrutinyOfficer}
      />

      {/* Edit Modal */}
      <InstrumentModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={loadInstrument}
        instrumentToEdit={instrument}
      />
    </div>
  );
};
