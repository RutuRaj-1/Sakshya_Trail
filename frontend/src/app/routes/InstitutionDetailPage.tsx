import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { institutionsApi, instrumentsApi } from '@/api/endpoints';
import type { Institution, Instrument } from '@/types';
import { Badge } from '@/components/common/Badge';
import { formatINR, formatDate } from '@/lib/utils';
import { InstitutionModal } from '@/features/institutions/InstitutionModal';
import { InstrumentModal } from '@/features/instruments/InstrumentModal';
import { useAuth } from '@/features/auth/AuthContext';
import {
  Building2,
  Mail,
  Calendar,
  Clock,
  ArrowLeft,
  Edit2,
  ShieldCheck,
  ShieldAlert,
  FileSpreadsheet,
  AlertCircle,
  Briefcase,
  Plus,
  Eye,
  Shield,
} from 'lucide-react';

export const InstitutionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';

  const [institution, setInstitution] = useState<Institution | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddInstrumentOpen, setIsAddInstrumentOpen] = useState(false);

  // Status toggle confirmation
  const [showStatusConfirm, setShowStatusConfirm] = useState(false);
  const [statusReason, setStatusReason] = useState('');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  const loadData = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const [instData, instruRes] = await Promise.all([
        institutionsApi.get(id),
        instrumentsApi.list({ institution_id: id, limit: 50 }),
      ]);
      setInstitution(instData);
      setInstruments(instruRes.items);
    } catch (err: any) {
      setError(
        err?.response?.data?.message || err?.message || 'Failed to retrieve institution records.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggleStatus = async () => {
    if (!institution || isUpdatingStatus) return;
    setIsUpdatingStatus(true);
    try {
      const newStatus = !institution.is_active;
      await institutionsApi.setStatus(institution.id, newStatus, statusReason || undefined);
      setShowStatusConfirm(false);
      await loadData();
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Status update failed.');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
        <p className="text-sm font-medium">Retrieving verified institution record...</p>
      </div>
    );
  }

  if (error || !institution) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-white rounded-2xl border border-slate-200 text-center shadow-xs">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-slate-800">Institution Not Available</h2>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{error || 'Record was not found.'}</p>
        <button
          onClick={() => navigate('/institutions')}
          className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Registry</span>
        </button>
      </div>
    );
  }

  const isOwnInstitution = isInstitutionUser && user?.institution_id === institution.id;
  const canEdit = isSystemAdmin || isOwnInstitution;
  const canRecordFDR = ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER'].includes(user?.role || '') || isOwnInstitution;

  return (
    <div className="space-y-6 max-w-5xl mx-auto text-xs">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/institutions')}
          className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Institution Registry</span>
        </button>

        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              onClick={() => setIsEditModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold shadow-2xs transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>{isInstitutionUser ? 'Update Nodal Contact' : 'Edit Institution'}</span>
            </button>
          )}

          {isSystemAdmin && (
            <button
              onClick={() => {
                setStatusReason('');
                setShowStatusConfirm(true);
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold shadow-2xs transition-colors ${
                institution.is_active
                  ? 'border border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
                  : 'border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
              }`}
            >
              {institution.is_active ? (
                <>
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Deactivate Record</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Reactivate Record</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Main Profile Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-6 border-b border-slate-100">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-sentinel-50 border border-sentinel-100 text-sentinel-700 flex items-center justify-center shrink-0">
              <Building2 className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-sentinel-100 text-sentinel-800 font-bold">
                  {institution.code}
                </span>
                <Badge variant={institution.is_active ? 'success' : 'default'}>
                  {institution.is_active ? 'ACTIVE' : 'INACTIVE (HISTORICAL)'}
                </Badge>
              </div>
              <h1 className="text-xl font-bold text-slate-900 mt-1">
                {institution.legal_name}
              </h1>
              {institution.display_name && institution.display_name !== institution.legal_name && (
                <p className="text-slate-500 text-xs">Operating Name: {institution.display_name}</p>
              )}
            </div>
          </div>

          <div className="text-left sm:text-right space-y-1 text-slate-500 font-mono text-[11px]">
            <div className="flex items-center sm:justify-end gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Registered: {new Date(institution.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center sm:justify-end gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>Updated: {new Date(institution.updated_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>

        {/* Profile Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Regulatory Information */}
          <div className="space-y-4">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Briefcase className="w-4 h-4 text-sentinel-600" />
              <span>Regulatory Classification & Jurisdiction</span>
            </h3>

            <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-200/80 space-y-2.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Taxonomy Type</span>
                <span className="font-mono font-medium text-slate-800">
                  {institution.institution_type}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Assigned Regional Office</span>
                <span className="font-medium text-slate-800">
                  {institution.assigned_office || 'Headquarters / All-India Scope'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">AICTE Permanent ID</span>
                <span className="font-mono text-sentinel-700 font-semibold">{institution.code}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Historical Tracking</span>
                <span className="text-slate-800">
                  {institution.is_synthetic ? 'Synthetic Bootstrap' : 'Statutory Registry Entry'}
                </span>
              </div>
            </div>
          </div>

          {/* Nodal Officer & Contact Details */}
          <div className="space-y-4">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Mail className="w-4 h-4 text-sentinel-600" />
              <span>Verified Institutional Contacts</span>
            </h3>

            <div className="bg-slate-50/70 rounded-xl p-4 border border-slate-200/80 space-y-2.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Nodal / Registrar</span>
                <span className="font-medium text-slate-800">{institution.contact_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Official Email</span>
                <a
                  href={`mailto:${institution.contact_email}`}
                  className="font-medium text-sentinel-700 hover:underline"
                >
                  {institution.contact_email}
                </a>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Direct Telephone</span>
                <span className="font-mono text-slate-800">{institution.contact_phone}</span>
              </div>
              <div className="flex justify-between items-start">
                <span className="text-slate-500">Official Address</span>
                <span className="text-right text-slate-800 max-w-[200px]">
                  {institution.address_line1}
                  {institution.address_line2 ? `, ${institution.address_line2}` : ''}
                  <br />
                  {institution.city}, {institution.state} - {institution.postal_code}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Linked Instruments Section (Connected to Real Instrument Registry) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-sentinel-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Linked Statutory FDR Instruments ({instruments.length})
            </h2>
          </div>
          {canRecordFDR && (
            <button
              onClick={() => setIsAddInstrumentOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sentinel-600 hover:bg-sentinel-700 text-white font-semibold text-xs shadow-2xs transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Record FDR for Institution</span>
            </button>
          )}
        </div>

        {instruments.length === 0 ? (
          <div className="p-8 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
            <FileSpreadsheet className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h3 className="text-xs font-semibold text-slate-700">
              No Security Deposit Instruments Linked
            </h3>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto mt-1">
              No security deposit certificates have been recorded for this institution yet. Authorized
              officials may record new instruments using the action above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 uppercase font-semibold text-slate-500">
                <tr>
                  <th className="py-2.5 px-3">Reference / Bank</th>
                  <th className="py-2.5 px-3">Deposit Principal</th>
                  <th className="py-2.5 px-3">Maturity Date</th>
                  <th className="py-2.5 px-3">Maturity Window</th>
                  <th className="py-2.5 px-3">Trust Level</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {instruments.map((instru) => (
                  <tr key={instru.id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3">
                      <div className="font-mono font-bold text-slate-900">{instru.reference_number}</div>
                      <div className="text-[10px] text-slate-500">{instru.bank_name}</div>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                      {formatINR(Number(instru.amount))}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-700">
                      {formatDate(instru.maturity_date)}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        instru.maturity_indicator === 'ACTIVE'
                          ? 'bg-emerald-100 text-emerald-800'
                          : instru.maturity_indicator === 'EXPIRING_SOON'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}>
                        {instru.maturity_indicator}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200">
                        <Shield className="w-2.5 h-2.5 text-purple-600" />
                        <span>{instru.trust_level}</span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant={instru.status === 'REGISTERED' ? 'info' : 'default'}>
                        {instru.status}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => navigate(`/instruments/${instru.id}`)}
                        className="p-1 text-slate-600 hover:text-sentinel-700 rounded transition-colors inline-flex items-center gap-1 font-semibold"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      <InstitutionModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={loadData}
        institutionToEdit={institution}
        isInstitutionUser={isInstitutionUser}
      />

      {/* Record Instrument Modal */}
      <InstrumentModal
        isOpen={isAddInstrumentOpen}
        onClose={() => setIsAddInstrumentOpen(false)}
        onSuccess={loadData}
        defaultInstitutionId={institution.id}
      />

      {/* Status Confirmation Modal */}
      {showStatusConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  institution.is_active
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                {institution.is_active ? (
                  <ShieldAlert className="w-5 h-5" />
                ) : (
                  <ShieldCheck className="w-5 h-5" />
                )}
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  {institution.is_active
                    ? 'Confirm Institution Deactivation'
                    : 'Confirm Institution Reactivation'}
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {institution.is_active
                    ? 'Deactivating this institution will freeze all new security deposit submissions. Existing records remain permanently preserved for statutory audit.'
                    : 'Reactivating this institution allows statutory FDR submissions to resume.'}
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Reason for status change:
              </label>
              <textarea
                rows={2}
                value={statusReason}
                onChange={(e) => setStatusReason(e.target.value)}
                placeholder="Regulatory justification logged to audit trail..."
                className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowStatusConfirm(false)}
                disabled={isUpdatingStatus}
                className="px-4 py-2 text-xs rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleToggleStatus}
                disabled={isUpdatingStatus}
                className={`px-4 py-2 text-xs rounded-lg text-white font-medium shadow-sm flex items-center gap-1.5 ${
                  institution.is_active
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-emerald-600 hover:bg-emerald-700'
                }`}
              >
                {isUpdatingStatus && (
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                )}
                <span>{institution.is_active ? 'Deactivate Record' : 'Reactivate Record'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
