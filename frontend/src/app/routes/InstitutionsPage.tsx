import React, { useEffect, useState, useCallback } from 'react';
import { InstitutionsList } from '@/features/institutions/InstitutionsList';
import { InstitutionModal } from '@/features/institutions/InstitutionModal';
import { institutionsApi } from '@/api/endpoints';
import type { Institution } from '@/types';
import { Search, Plus, Filter, AlertTriangle, ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';

const INSTITUTION_TYPES = [
  'ALL',
  'TECHNICAL_INSTITUTE',
  'ENGINEERING_COLLEGE',
  'PHARMACY_INSTITUTE',
  'MANAGEMENT_STUDIES',
  'POLYTECHNIC_COLLEGE',
];

export const InstitutionsPage: React.FC = () => {
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';

  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedInstitution, setSelectedInstitution] = useState<Institution | null>(null);

  // Deactivate confirmation state
  const [statusConfirmTarget, setStatusConfirmTarget] = useState<Institution | null>(null);
  const [isTogglingStatus, setIsTogglingStatus] = useState(false);
  const [statusReason, setStatusReason] = useState('');

  const loadInstitutions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activeParam =
        statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined;
      const typeParam = typeFilter !== 'ALL' ? typeFilter : undefined;

      const res = await institutionsApi.list({
        search: search.trim() || undefined,
        institution_type: typeParam,
        is_active: activeParam,
        skip: (page - 1) * pageSize,
        limit: pageSize,
      });

      setInstitutions(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Failed to load institutions.');
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter, typeFilter, page]);

  useEffect(() => {
    loadInstitutions();
  }, [loadInstitutions]);

  const handleEdit = (inst: Institution) => {
    setSelectedInstitution(inst);
    setIsModalOpen(true);
  };

  const handleOpenCreate = () => {
    setSelectedInstitution(null);
    setIsModalOpen(true);
  };

  const handleStatusToggle = (inst: Institution) => {
    setStatusConfirmTarget(inst);
    setStatusReason('');
  };

  const confirmStatusChange = async () => {
    if (!statusConfirmTarget || isTogglingStatus) return;
    setIsTogglingStatus(true);
    try {
      const newStatus = !statusConfirmTarget.is_active;
      await institutionsApi.setStatus(statusConfirmTarget.id, newStatus, statusReason || undefined);
      setStatusConfirmTarget(null);
      await loadInstitutions();
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Status change failed.');
    } finally {
      setIsTogglingStatus(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Institution Registry
          </h1>
          <p className="text-xs text-slate-500">
            {isInstitutionUser
              ? 'Institutional profile and compliance deposit records maintained with AICTE'
              : 'Statutory registry of technical education institutions under Regulation Bureau oversight'}
          </p>
        </div>

        {isSystemAdmin && (
          <button
            onClick={handleOpenCreate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sentinel-600 hover:bg-sentinel-700 text-white text-xs font-semibold shadow-xs transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Register Institution</span>
          </button>
        )}
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 text-xs">
        <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by permanent code, legal or display name..."
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as any);
                setPage(1);
              }}
              className="border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Only</option>
              <option value="INACTIVE">Inactive (Historical)</option>
            </select>
          </div>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
          >
            {INSTITUTION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t === 'ALL' ? 'All Classifications' : t.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        <div className="text-right text-[11px] text-slate-500 self-center">
          Showing <span className="font-semibold text-slate-800">{institutions.length}</span> of{' '}
          <span className="font-semibold text-slate-800">{total}</span> records
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Institution List Table */}
      <InstitutionsList
        institutions={institutions}
        isLoading={isLoading}
        onEdit={handleEdit}
        onStatusToggle={handleStatusToggle}
      />

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl border border-slate-200 text-xs">
          <div className="text-slate-500">
            Page <span className="font-semibold text-slate-800">{page}</span> of{' '}
            <span className="font-semibold text-slate-800">{totalPages}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Institution Create/Edit Modal */}
      <InstitutionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={loadInstitutions}
        institutionToEdit={selectedInstitution}
        isInstitutionUser={isInstitutionUser}
      />

      {/* Status Toggle Confirmation Modal */}
      {statusConfirmTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  statusConfirmTarget.is_active
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                {statusConfirmTarget.is_active ? (
                  <AlertTriangle className="w-5 h-5" />
                ) : (
                  <ShieldCheck className="w-5 h-5" />
                )}
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  {statusConfirmTarget.is_active
                    ? 'Confirm Institution Deactivation'
                    : 'Confirm Institution Reactivation'}
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {statusConfirmTarget.is_active
                    ? 'Deactivating this institution blocks new FDR registrations while preserving all historical records for statutory audit.'
                    : 'Reactivating this institution restores active regulatory status and permits new security deposit submissions.'}
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <span className="font-semibold text-slate-700">Target Institution:</span>{' '}
              <span className="text-slate-900">{statusConfirmTarget.legal_name}</span> (
              <span className="font-mono text-sentinel-700">{statusConfirmTarget.code}</span>)
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Reason for status change (logged to immutable audit trail):
              </label>
              <textarea
                rows={2}
                value={statusReason}
                onChange={(e) => setStatusReason(e.target.value)}
                placeholder="e.g. Annual renewal lapsed, regulatory deficiency notice, or reactivation approved..."
                className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setStatusConfirmTarget(null)}
                disabled={isTogglingStatus}
                className="px-4 py-2 text-xs rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmStatusChange}
                disabled={isTogglingStatus}
                className={`px-4 py-2 text-xs rounded-lg text-white font-medium shadow-sm transition-all flex items-center gap-1.5 ${
                  statusConfirmTarget.is_active
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-emerald-600 hover:bg-emerald-700'
                }`}
              >
                {isTogglingStatus && (
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                )}
                <span>
                  {statusConfirmTarget.is_active ? 'Deactivate Record' : 'Reactivate Record'}
                </span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
