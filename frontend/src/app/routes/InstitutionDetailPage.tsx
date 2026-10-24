import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { institutionsApi } from '@/api/endpoints';
import type { Institution } from '@/types';
import { Badge } from '@/components/common/Badge';
import { InstitutionModal } from '@/features/institutions/InstitutionModal';
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
} from 'lucide-react';

export const InstitutionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';

  const [institution, setInstitution] = useState<Institution | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Status toggle confirmation
  const [showStatusConfirm, setShowStatusConfirm] = useState(false);
  const [statusReason, setStatusReason] = useState('');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  const loadInstitution = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await institutionsApi.get(id);
      setInstitution(data);
    } catch (err: any) {
      setError(
        err?.response?.data?.message || err?.message || 'Failed to retrieve institution record.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadInstitution();
  }, [loadInstitution]);

  const handleToggleStatus = async () => {
    if (!institution || isUpdatingStatus) return;
    setIsUpdatingStatus(true);
    try {
      const newStatus = !institution.is_active;
      await institutionsApi.setStatus(institution.id, newStatus, statusReason || undefined);
      setShowStatusConfirm(false);
      await loadInstitution();
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

      {/* Linked Instruments Section (Placeholder for Prompt 4) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-sentinel-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Linked Statutory FDR Instruments
            </h2>
          </div>
          <span className="text-[11px] font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
            Module 2 Lifecycle Integration
          </span>
        </div>

        <div className="p-8 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
          <FileSpreadsheet className="w-10 h-10 text-slate-300 mx-auto mb-2" />
          <h3 className="text-xs font-semibold text-slate-700">
            No Security Deposit Instruments Linked
          </h3>
          <p className="text-[11px] text-slate-500 max-w-sm mx-auto mt-1">
            Statutory FDR instruments, multi-party bank verification levels, and automated lien
            checks for this institution will be managed through Module 2 (Prompt 4).
          </p>
        </div>
      </div>

      {/* Edit Modal */}
      <InstitutionModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={loadInstitution}
        institutionToEdit={institution}
        isInstitutionUser={isInstitutionUser}
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
