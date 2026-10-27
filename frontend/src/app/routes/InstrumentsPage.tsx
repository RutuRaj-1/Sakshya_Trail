import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { InstrumentsList } from '@/features/instruments/InstrumentsList';
import { InstrumentModal } from '@/features/instruments/InstrumentModal';
import { instrumentsApi, institutionsApi } from '@/api/endpoints';
import type { Instrument, InstrumentSummary, Institution } from '@/types';
import { formatINR } from '@/lib/utils';
import {
  Search,
  Plus,
  Filter,
  FileSpreadsheet,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { canCreateInstrument } from '@/features/auth/authUtils';

export const InstrumentsPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const canRecord = canCreateInstrument(user?.role);

  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState<InstrumentSummary | null>(null);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters initialized from searchParams
  const paramStatus = searchParams.get('status') || searchParams.get('maturity_indicator') || 'ALL';
  const paramTrust = searchParams.get('trust_level') || 'ALL';
  const paramInst = searchParams.get('institution_id') || '';

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(paramStatus);
  const [trustFilter, setTrustFilter] = useState(paramTrust);
  const [selectedInstFilter, setSelectedInstFilter] = useState(paramInst);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Sync state if URL changes externally
  useEffect(() => {
    const nextStatus = searchParams.get('status') || searchParams.get('maturity_indicator') || 'ALL';
    const nextTrust = searchParams.get('trust_level') || 'ALL';
    const nextInst = searchParams.get('institution_id') || '';
    setStatusFilter(nextStatus);
    setTrustFilter(nextTrust);
    setSelectedInstFilter(nextInst);
    setPage(1);
  }, [searchParams]);

  const updateUrlParam = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([k, v]) => {
      if (!v || v === 'ALL') {
        next.delete(k);
      } else {
        next.set(k, v);
      }
    });
    setSearchParams(next, { replace: true });
  };

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Load institutions list for filter dropdown if internal user
  useEffect(() => {
    async function fetchInstitutions() {
      try {
        const res = await institutionsApi.list({ is_active: true, limit: 100 });
        setInstitutions(res.items);
      } catch (e) {
        console.error('Failed to load institutions filter list', e);
      }
    }
    if (!isInstitutionUser) {
      fetchInstitutions();
    }
  }, [isInstitutionUser]);

  const loadInstruments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const statusParam = statusFilter !== 'ALL' ? statusFilter : undefined;
      const trustParam = trustFilter !== 'ALL' ? trustFilter : undefined;
      const instParam = selectedInstFilter || undefined;

      const [listRes, summaryRes] = await Promise.all([
        instrumentsApi.list({
          search: search.trim() || undefined,
          status: statusParam,
          trust_level: trustParam,
          institution_id: instParam,
          skip: (page - 1) * pageSize,
          limit: pageSize,
        }),
        instrumentsApi.getSummary(),
      ]);

      setInstruments(listRes.items);
      setTotal(listRes.total);
      setSummary(summaryRes);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Failed to retrieve instruments.');
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter, trustFilter, selectedInstFilter, page]);

  useEffect(() => {
    loadInstruments();
  }, [loadInstruments]);

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto text-xs">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#0D2538] tracking-tight flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-[#123B5D]" />
            <span>Statutory FDR / Instrument Registry</span>
          </h1>
          <p className="text-xs text-[#5D6A75]">
            {isInstitutionUser
              ? 'Institutional security deposit FDR certificates pledged under AICTE regulatory terms'
              : 'Regulatory bureau registry of all pledged bank fixed deposit receipts and guarantees'}
          </p>
        </div>

        {canRecord && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold shadow-xs transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Record FDR Instrument</span>
          </button>
        )}
      </div>

      {/* KPI Overview Strip */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-white p-3.5 rounded-[10px] border border-[#C9D3DB] shadow-2xs">
            <span className="text-[#5D6A75] text-[11px]">Total Deposit Portfolio</span>
            <div className="text-base font-bold text-[#0D2538] font-mono mt-0.5">
              {formatINR(Number(summary.total_deposit_value))}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-[#123B5D]" />
              <span>{summary.total_instruments} registered certificates</span>
            </div>
          </div>

          <div className="bg-white p-3.5 rounded-[10px] border border-[#C9D3DB] shadow-2xs">
            <span className="text-[#5D6A75] text-[11px]">Active Compliance</span>
            <div className="text-base font-bold text-emerald-700 font-mono mt-0.5">
              {summary.active_count}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-600" />
              <span>Valid lien-marked deposits</span>
            </div>
          </div>

          <div className="bg-white p-3.5 rounded-[10px] border border-[#C9D3DB] shadow-2xs">
            <span className="text-[#5D6A75] text-[11px]">Expiring Within 90 Days</span>
            <div className="text-base font-bold text-amber-600 font-mono mt-0.5">
              {summary.expiring_soon_count}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
              <Clock className="w-3 h-3 text-amber-500" />
              <span>Maturity review required</span>
            </div>
          </div>

          <div className="bg-white p-3.5 rounded-[10px] border border-[#C9D3DB] shadow-2xs">
            <span className="text-[#5D6A75] text-[11px]">Under Initial Scrutiny</span>
            <div className="text-base font-bold text-blue-700 font-mono mt-0.5">
              {summary.under_scrutiny_count}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
              <FileSpreadsheet className="w-3 h-3 text-blue-600" />
              <span>Awaiting bureau review</span>
            </div>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-[10px] border border-[#C9D3DB] shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by FDR reference, bank, or institute name/code..."
              className="w-full pl-9 pr-3 py-2 border border-[#8799A9] rounded-lg text-[#253746] placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => {
                const val = e.target.value;
                setStatusFilter(val);
                setPage(1);
                updateUrlParam({ status: val });
              }}
              className="border border-[#8799A9] rounded-lg px-2.5 py-2 bg-white text-[#253746] focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono text-xs"
            >
              <option value="ALL">All Statuses &amp; Lifecycles</option>
              <optgroup label="Maturity Windows">
                <option value="ACTIVE">ACTIVE (In-Term)</option>
                <option value="EXPIRING_SOON">EXPIRING_SOON (≤ 90d)</option>
                <option value="MATURED">MATURED / EXPIRED</option>
              </optgroup>
              <optgroup label="Administrative Status">
                <option value="REGISTERED">REGISTERED</option>
                <option value="DRAFT">DRAFT</option>
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="UNDER_SCRUTINY">PENDING SCRUTINY</option>
                <option value="RETURNED_FOR_CORRECTION">RETURNED FOR CORRECTION</option>
              </optgroup>
              <optgroup label="Lineage &amp; Discharge">
                <option value="RENEWED">RENEWED</option>
                <option value="RELEASED">RELEASED</option>
              </optgroup>
            </select>
          </div>

          {/* Trust Level Filter */}
          <select
            value={trustFilter}
            onChange={(e) => {
              const val = e.target.value;
              setTrustFilter(val);
              setPage(1);
              updateUrlParam({ trust_level: val });
            }}
            className="border border-[#8799A9] rounded-lg px-2.5 py-2 bg-white text-[#253746] focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono text-xs"
          >
            <option value="ALL">All Trust Levels</option>
            <option value="L0_DECLARED">L0 — DECLARED</option>
            <option value="L1_DOCUMENT_CONSISTENT">L1 — DOC CONSISTENT</option>
            <option value="L2_OFFICER_VERIFIED">L2 — OFFICER VERIFIED</option>
            <option value="L3_BANK_CONFIRMED">L3 — BANK CONFIRMED</option>
          </select>

          {/* Institution Filter for internal bureau officers */}
          {!isInstitutionUser && institutions.length > 0 && (
            <select
              value={selectedInstFilter}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedInstFilter(val);
                setPage(1);
                updateUrlParam({ institution_id: val });
              }}
              className="border border-[#8799A9] rounded-lg px-2.5 py-2 bg-white text-[#253746] focus:outline-none focus:ring-2 focus:ring-sentinel-500 max-w-[200px] truncate"
            >
              <option value="">All Institutions</option>
              {institutions.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.code} — {i.legal_name || i.name}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="text-right text-[11px] text-[#5D6A75] self-center">
          Showing <span className="font-semibold text-[#253746]">{instruments.length}</span> of{' '}
          <span className="font-semibold text-[#253746]">{total}</span> records
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-[10px] bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Instruments Table */}
      <InstrumentsList instruments={instruments} isLoading={isLoading} />

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 rounded-[10px] border border-[#C9D3DB] text-xs">
          <div className="text-[#5D6A75]">
            Page <span className="font-semibold text-[#253746]">{page}</span> of{' '}
            <span className="font-semibold text-[#253746]">{totalPages}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-[#8799A9] hover:bg-[#F5F4EF] disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg border border-[#8799A9] hover:bg-[#F5F4EF] disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Registration Modal */}
      <InstrumentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={loadInstruments}
      />
    </div>
  );
};
