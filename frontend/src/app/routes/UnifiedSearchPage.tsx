import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { commandCenterApi } from '@/api/commandCenter';
import type {
  InstrumentSearchItem,
  ReleaseCaseSearchItem,
} from '@/types/commandCenter';
import { formatINR, formatDate } from '@/lib/utils';
import { Badge } from '@/components/common/Badge';
import {
  Search,
  RotateCcw,
  AlertTriangle,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Shield,
  FileSpreadsheet,
  FileCheck2,
  ExternalLink,
  SlidersHorizontal,
  X,
  AlertCircle,
} from 'lucide-react';

export const UnifiedSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Search domain tab: 'instruments' or 'cases'
  const domain = (searchParams.get('domain') as 'instruments' | 'cases') || 'instruments';

  // Search input state derived from URL
  const query = searchParams.get('q') || '';
  const institution = searchParams.get('institution') || '';
  const bank = searchParams.get('bank') || '';
  const reference = searchParams.get('ref') || '';
  const status = searchParams.get('status') || '';
  const trustLevel = searchParams.get('trust') || '';
  const assignedOffice = searchParams.get('office') || '';
  const issueFrom = searchParams.get('issue_from') || '';
  const issueTo = searchParams.get('issue_to') || '';
  const maturityFrom = searchParams.get('mat_from') || '';
  const maturityTo = searchParams.get('mat_to') || '';
  const hasDiscrepancies = searchParams.get('discrepancies') === 'true';
  const priorityCategory = searchParams.get('priority') || '';

  // Sort and pagination
  const sortBy = searchParams.get('sort_by') || 'created_at';
  const sortOrder = (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc';
  const page = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = 15;

  // Local state
  const [instruments, setInstruments] = useState<InstrumentSearchItem[]>([]);
  const [releaseCases, setReleaseCases] = useState<ReleaseCaseSearchItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Local draft inputs for header search input
  const [searchInput, setSearchInput] = useState(query);

  useEffect(() => {
    setSearchInput(query);
  }, [query]);

  // Update query params helper
  const updateParams = useCallback(
    (updates: Record<string, string | null>) => {
      const newParams = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([k, v]) => {
        if (v === null || v === '' || v === 'ALL') {
          newParams.delete(k);
        } else {
          newParams.set(k, v);
        }
      });
      // Reset page to 1 when changing search criteria (except when page itself is updated)
      if (!('page' in updates)) {
        newParams.set('page', '1');
      }
      setSearchParams(newParams);
    },
    [searchParams, setSearchParams]
  );

  // Execute Search
  const fetchSearchResults = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const skip = (page - 1) * pageSize;

      if (domain === 'instruments') {
        const res = await commandCenterApi.searchInstruments({
          q: query || undefined,
          institution: institution || undefined,
          bank: bank || undefined,
          reference: reference || undefined,
          status: status || undefined,
          trust_level: trustLevel || undefined,
          assigned_office: assignedOffice || undefined,
          issue_date_from: issueFrom || undefined,
          issue_date_to: issueTo || undefined,
          maturity_date_from: maturityFrom || undefined,
          maturity_date_to: maturityTo || undefined,
          has_discrepancies: hasDiscrepancies ? 'true' : undefined,
          priority_category: priorityCategory || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          skip,
          limit: pageSize,
        });
        setInstruments(res.records || []);
        setTotalCount(res.total_count || 0);
      } else {
        const res = await commandCenterApi.searchReleaseCases({
          q: query || undefined,
          institution: institution || undefined,
          workflow_status: status || undefined,
          assigned_office: assignedOffice || undefined,
          created_after: issueFrom || undefined,
          created_before: issueTo || undefined,
          sort_by: sortBy === 'amount' ? 'created_at' : sortBy,
          sort_order: sortOrder,
          skip,
          limit: pageSize,
        });
        setReleaseCases(res.records || []);
        setTotalCount(res.total_count || 0);
      }
    } catch (err: any) {
      console.error('Search error:', err);
      setError(
        err?.response?.data?.message ||
          err?.message ||
          'Failed to retrieve records. Please refine search parameters.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [
    domain,
    query,
    institution,
    bank,
    reference,
    status,
    trustLevel,
    assignedOffice,
    issueFrom,
    issueTo,
    maturityFrom,
    maturityTo,
    hasDiscrepancies,
    priorityCategory,
    sortBy,
    sortOrder,
    page,
  ]);

  useEffect(() => {
    fetchSearchResults();
  }, [fetchSearchResults]);

  // Count active filter pills
  const activeFilters = useMemo(() => {
    const filters: { key: string; label: string; value: string }[] = [];
    if (query) filters.push({ key: 'q', label: 'Keyword', value: query });
    if (institution) filters.push({ key: 'institution', label: 'Institution', value: institution });
    if (bank) filters.push({ key: 'bank', label: 'Bank', value: bank });
    if (reference) filters.push({ key: 'ref', label: 'Reference', value: reference });
    if (status) filters.push({ key: 'status', label: 'Status', value: status });
    if (trustLevel) filters.push({ key: 'trust', label: 'Trust', value: trustLevel });
    if (assignedOffice) filters.push({ key: 'office', label: 'Office', value: assignedOffice });
    if (issueFrom) filters.push({ key: 'issue_from', label: 'Issued After', value: issueFrom });
    if (maturityTo) filters.push({ key: 'mat_to', label: 'Matures Before', value: maturityTo });
    if (hasDiscrepancies) filters.push({ key: 'discrepancies', label: 'Flag', value: 'Has Discrepancies' });
    if (priorityCategory) filters.push({ key: 'priority', label: 'Priority', value: priorityCategory });
    return filters;
  }, [
    query,
    institution,
    bank,
    reference,
    status,
    trustLevel,
    assignedOffice,
    issueFrom,
    maturityTo,
    hasDiscrepancies,
    priorityCategory,
  ]);

  const handleResetFilters = () => {
    const newParams = new URLSearchParams();
    newParams.set('domain', domain);
    setSearchParams(newParams);
    setSearchInput('');
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      updateParams({ sort_order: sortOrder === 'asc' ? 'desc' : 'asc' });
    } else {
      updateParams({ sort_by: field, sort_order: 'desc' });
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="space-y-6 max-w-7xl mx-auto text-xs pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#C9D3DB] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-[#EEF6FA] text-[#0D2538]">
              Module 7 Search Desk
            </span>
            <span className="text-slate-400">•</span>
            <span className="text-[#5D6A75] font-medium">Server-Backed Query Engine</span>
          </div>
          <h1 className="text-2xl font-bold text-[#0D2538] mt-1">Unified Record Search & History Drill-Down</h1>
          <p className="text-[#5D6A75] text-xs mt-0.5">
            Locate FDR deposit instruments and release cases across authorized scopes with parameterized multi-attribute filtering.
          </p>
        </div>

        {/* Domain Switcher */}
        <div className="inline-flex items-center p-1 bg-slate-100 rounded-[8px] border border-[#C9D3DB]">
          <button
            onClick={() => updateParams({ domain: 'instruments', page: '1' })}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-semibold transition-all ${
              domain === 'instruments'
                ? 'bg-white text-[#0D2538] shadow-xs'
                : 'text-[#5D6A75] hover:text-[#0D2538]'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-[#0F766E]" />
            <span>FDR Instruments</span>
          </button>
          <button
            onClick={() => updateParams({ domain: 'cases', page: '1' })}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-semibold transition-all ${
              domain === 'cases'
                ? 'bg-white text-[#0D2538] shadow-xs'
                : 'text-[#5D6A75] hover:text-[#0D2538]'
            }`}
          >
            <FileCheck2 className="w-3.5 h-3.5 text-purple-600" />
            <span>Release & Refund Cases</span>
          </button>
        </div>
      </div>

      {/* Main Search Bar & Quick Filters */}
      <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs p-4 space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateParams({ q: searchInput });
          }}
          className="flex flex-col sm:flex-row items-center gap-2"
        >
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={
                domain === 'instruments'
                  ? 'Search by instrument reference, institution name, or issuing bank...'
                  : 'Search by case reference number, institution, or instrument ID...'
              }
              className="w-full pl-10 pr-4 py-2.5 rounded-[8px] border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sentinel-500 focus:border-sentinel-500 text-xs text-[#253746] placeholder-slate-400"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              type="submit"
              className="w-full sm:w-auto px-4 py-2.5 rounded-[8px] bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold transition-colors flex items-center justify-center gap-1.5"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search</span>
            </button>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`px-3 py-2.5 rounded-[8px] border font-semibold flex items-center gap-1.5 transition-colors ${
                showAdvanced || activeFilters.length > 0
                  ? 'bg-[#EEF6FA] border-sentinel-300 text-[#123B5D]'
                  : 'bg-white border-slate-300 text-[#253746] hover:bg-[#F5F4EF]'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Filters {activeFilters.length > 0 && `(${activeFilters.length})`}</span>
            </button>
            {activeFilters.length > 0 && (
              <button
                type="button"
                onClick={handleResetFilters}
                title="Reset all filters"
                className="p-2.5 rounded-[8px] border border-slate-300 hover:bg-slate-100 text-[#5D6A75] hover:text-[#253746] transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </form>

        {/* Collapsible Advanced Filters Drawer */}
        {showAdvanced && (
          <div className="pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {domain === 'instruments' && (
              <>
                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Administrative Status
                  </label>
                  <select
                    value={status}
                    onChange={(e) => updateParams({ status: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746] focus:ring-1 focus:ring-sentinel-500"
                  >
                    <option value="">All Statuses</option>
                    <option value="REGISTERED">REGISTERED</option>
                    <option value="DRAFT">DRAFT</option>
                    <option value="LODGED">LODGED</option>
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="EXPIRED">EXPIRED</option>
                    <option value="MATURED">MATURED</option>
                    <option value="RELEASED">RELEASED</option>
                    <option value="INVOKED">INVOKED</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Trust Provenance Level
                  </label>
                  <select
                    value={trustLevel}
                    onChange={(e) => updateParams({ trust: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746] focus:ring-1 focus:ring-sentinel-500"
                  >
                    <option value="">All Trust Levels</option>
                    <option value="L0_DECLARED">L0 — Declared</option>
                    <option value="L1_DOCUMENT_CONSISTENT">L1 — Document Consistent</option>
                    <option value="L2_OFFICER_VERIFIED">L2 — Officer Verified</option>
                    <option value="L3_BANK_CONFIRMED">L3 — Bank Confirmed</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Priority Queue Category
                  </label>
                  <select
                    value={priorityCategory}
                    onChange={(e) => updateParams({ priority: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746] focus:ring-1 focus:ring-sentinel-500"
                  >
                    <option value="">All Categories</option>
                    <option value="CRITICAL_OVERDUE">Critical Overdue (&gt;30d)</option>
                    <option value="EXPIRING_30D">Expiring Soon (&lt;=30d)</option>
                    <option value="DISCREPANCY_FLAGGED">Discrepancy Flagged</option>
                    <option value="UNVERIFIED">Unverified / L0</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Discrepancy Flag
                  </label>
                  <label className="flex items-center gap-2 mt-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={hasDiscrepancies}
                      onChange={(e) =>
                        updateParams({ discrepancies: e.target.checked ? 'true' : null })
                      }
                      className="rounded border-slate-300 text-[#0F766E] focus:ring-sentinel-500 w-4 h-4"
                    />
                    <span className="text-[#253746] font-medium">Active Discrepancies Only</span>
                  </label>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Issuing Bank Name
                  </label>
                  <input
                    type="text"
                    value={bank}
                    onChange={(e) => updateParams({ bank: e.target.value })}
                    placeholder="e.g. State Bank of India"
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Assigned Office / Region
                  </label>
                  <input
                    type="text"
                    value={assignedOffice}
                    onChange={(e) => updateParams({ office: e.target.value })}
                    placeholder="e.g. Northern Regional Office"
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Matures Before
                  </label>
                  <input
                    type="date"
                    value={maturityTo}
                    onChange={(e) => updateParams({ mat_to: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Issued After
                  </label>
                  <input
                    type="date"
                    value={issueFrom}
                    onChange={(e) => updateParams({ issue_from: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  />
                </div>
              </>
            )}

            {domain === 'cases' && (
              <>
                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Workflow Status
                  </label>
                  <select
                    value={status}
                    onChange={(e) => updateParams({ status: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  >
                    <option value="">All Statuses</option>
                    <option value="DRAFT">DRAFT</option>
                    <option value="SUBMITTED">SUBMITTED</option>
                    <option value="UNDER_SCRUTINY">UNDER_SCRUTINY</option>
                    <option value="COMMITTEE_REVIEW">COMMITTEE_REVIEW</option>
                    <option value="APPROVED">APPROVED</option>
                    <option value="ORDER_ISSUED">ORDER_ISSUED</option>
                    <option value="CLOSED">CLOSED</option>
                    <option value="REJECTED">REJECTED</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Assigned Office
                  </label>
                  <input
                    type="text"
                    value={assignedOffice}
                    onChange={(e) => updateParams({ office: e.target.value })}
                    placeholder="e.g. Headquarters"
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                    Created After
                  </label>
                  <input
                    type="date"
                    value={issueFrom}
                    onChange={(e) => updateParams({ issue_from: e.target.value })}
                    className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-[#253746]"
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Active Filter Badges */}
        {activeFilters.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100">
            <span className="text-[11px] font-semibold text-[#5D6A75] mr-1">Active Filters:</span>
            {activeFilters.map((f) => (
              <span
                key={f.key}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 text-[#253746] border border-[#C9D3DB] text-[11px] font-medium"
              >
                <span>
                  {f.label}: <strong className="text-[#0D2538]">{f.value}</strong>
                </span>
                <button
                  type="button"
                  onClick={() => updateParams({ [f.key]: null })}
                  className="hover:text-rose-600 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-[11px] text-[#0F766E] hover:text-[#0D2538] font-semibold underline ml-2"
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-[8px] bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-xs">Search Request Failed</h4>
            <p className="text-[11px] text-rose-700 mt-0.5">{error}</p>
          </div>
          <button
            onClick={fetchSearchResults}
            className="px-3 py-1 rounded bg-rose-100 hover:bg-rose-200 text-rose-800 text-[11px] font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Results Section */}
      <div className="bg-white rounded-[10px] border border-[#C9D3DB] shadow-xs overflow-hidden">
        {/* Results Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="font-bold text-[#253746] text-sm">
              {domain === 'instruments' ? 'FDR Instrument Records' : 'Release & Refund Case Records'}
            </h2>
            <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-slate-100 text-[#253746] font-semibold">
              {totalCount.toLocaleString()} {totalCount === 1 ? 'result' : 'results'}
            </span>
          </div>
          <span className="text-[11px] text-slate-400">
            Page {page} of {totalPages}
          </span>
        </div>

        {/* Loading Spinner */}
        {isLoading ? (
          <div className="py-20 text-center text-[#5D6A75]">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#C9D3DB] border-t-sentinel-600 mb-3" />
            <p className="font-medium text-xs">Querying database with authorized filters...</p>
          </div>
        ) : domain === 'instruments' ? (
          /* Instruments Table */
          instruments.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <FileSpreadsheet className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No FDR instruments match criteria</p>
              <p className="text-slate-400 text-[11px] max-w-sm mx-auto mt-1">
                Try widening date ranges, clearing specific bank filters, or resetting search keywords.
              </p>
              {activeFilters.length > 0 && (
                <button
                  onClick={handleResetFilters}
                  className="mt-4 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-[#253746] rounded-lg font-semibold text-xs transition-colors"
                >
                  Reset Active Filters
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] tracking-wider font-semibold border-b border-[#C9D3DB]">
                    <th
                      onClick={() => handleSort('reference_number')}
                      className="px-6 py-3 cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>Reference</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-6 py-3">Institution</th>
                    <th
                      onClick={() => handleSort('bank_name')}
                      className="px-6 py-3 cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>Issuing Bank</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('amount')}
                      className="px-6 py-3 text-right cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Amount</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('maturity_date')}
                      className="px-6 py-3 cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>Maturity Date</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-6 py-3">Admin Status</th>
                    <th className="px-6 py-3">Trust Level</th>
                    <th className="px-6 py-3 text-center">Flags</th>
                    <th className="px-6 py-3 text-right">Drill-Down</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {instruments.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-[#F5F4EF]/70 transition-colors group cursor-pointer"
                      onClick={() => navigate(`/instruments/${item.id}`)}
                    >
                      <td className="px-6 py-3.5">
                        <span className="font-mono font-bold text-[#0D2538] group-hover:text-[#123B5D] transition-colors">
                          {item.reference_number}
                        </span>
                        {item.assigned_office && (
                          <span className="block text-[10px] text-slate-400 mt-0.5">
                            {item.assigned_office}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 max-w-xs">
                        <span className="font-medium text-[#253746] line-clamp-1">
                          {item.institution_name || item.institution_id}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="text-[#253746] font-medium">{item.bank_name}</span>
                        {item.branch && (
                          <span className="block text-[10px] text-slate-400">{item.branch}</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-right font-mono font-bold text-[#0D2538]">
                        {formatINR(Number(item.amount))}
                      </td>
                      <td className="px-6 py-3.5 font-mono text-[#253746]">
                        {formatDate(item.maturity_date)}
                      </td>
                      <td className="px-6 py-3.5">
                        <Badge
                          variant={
                            item.status === 'ACTIVE'
                              ? 'success'
                              : item.status === 'EXPIRED' || item.status === 'MATURED'
                              ? 'warning'
                              : 'default'
                          }
                        >
                          {item.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-200">
                          <Shield className="w-3 h-3 text-purple-700" />
                          <span>{item.trust_level}</span>
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-center">
                        {item.has_active_discrepancies ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                            <AlertTriangle className="w-3 h-3 text-rose-700" />
                            <span>Flagged</span>
                          </span>
                        ) : (
                          <span className="text-slate-300 font-mono text-[11px]">—</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <Link
                          to={`/instruments/${item.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-[#0F766E] hover:text-[#0D2538] font-semibold group-hover:underline"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          /* Release Cases Table */
          releaseCases.length === 0 ? (
            <div className="py-16 text-center text-[#5D6A75]">
              <FileCheck2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No release/refund cases match criteria</p>
              <p className="text-slate-400 text-[11px] max-w-sm mx-auto mt-1">
                Verify case status, assigned office, or search keywords.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] tracking-wider font-semibold border-b border-[#C9D3DB]">
                    <th
                      onClick={() => handleSort('case_number')}
                      className="px-6 py-3 cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>Case Number</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-6 py-3">Linked FDR Instrument</th>
                    <th className="px-6 py-3">Institution</th>
                    <th className="px-6 py-3">Case Type</th>
                    <th className="px-6 py-3">Workflow Status</th>
                    <th className="px-6 py-3">Readiness Outcome</th>
                    <th className="px-6 py-3 text-center">Blockers</th>
                    <th
                      onClick={() => handleSort('created_at')}
                      className="px-6 py-3 cursor-pointer hover:bg-slate-100 transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>Created Date</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-6 py-3 text-right">Drill-Down</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {releaseCases.map((c) => (
                    <tr
                      key={c.id}
                      className="hover:bg-[#F5F4EF]/70 transition-colors group cursor-pointer"
                      onClick={() => navigate(`/release/${c.id}`)}
                    >
                      <td className="px-6 py-3.5">
                        <span className="font-mono font-bold text-[#0D2538] group-hover:text-purple-700 transition-colors">
                          {c.case_number}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="font-mono text-[#253746]">
                          {c.instrument_reference || c.instrument_id}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 max-w-xs">
                        <span className="font-medium text-[#253746] line-clamp-1">
                          {c.institution_name || c.institution_id}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="text-[#253746] font-medium">{c.case_type}</span>
                        <span className="block text-[10px] text-slate-400">{c.request_type}</span>
                      </td>
                      <td className="px-6 py-3.5">
                        <Badge
                          variant={
                            c.workflow_status === 'APPROVED' || c.workflow_status === 'ORDER_ISSUED'
                              ? 'success'
                              : c.workflow_status === 'CLOSED'
                              ? 'default'
                              : 'info'
                          }
                        >
                          {c.workflow_status}
                        </Badge>
                      </td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                            c.readiness_outcome === 'READY'
                              ? 'bg-emerald-100 text-emerald-800'
                              : c.readiness_outcome === 'BLOCKED'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-slate-100 text-[#5D6A75]'
                          }`}
                        >
                          {c.readiness_outcome || 'UNASSESSED'}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-center font-mono">
                        {c.blockers_count > 0 ? (
                          <span className="text-rose-600 font-bold">{c.blockers_count}</span>
                        ) : (
                          <span className="text-emerald-600 font-bold">0</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 font-mono text-[#253746]">
                        {formatDate(c.created_at)}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <Link
                          to={`/release/${c.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-purple-700 hover:text-purple-900 font-semibold group-hover:underline"
                        >
                          <span>Case File</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* Pagination Bar */}
        {totalCount > pageSize && (
          <div className="px-6 py-3 bg-[#F5F4EF]/70 border-t border-[#C9D3DB] flex items-center justify-between">
            <span className="text-[#5D6A75] text-[11px]">
              Showing {(page - 1) * pageSize + 1} to{' '}
              {Math.min(page * pageSize, totalCount)} of {totalCount} records
            </span>
            <div className="flex items-center gap-1.5">
              <button
                disabled={page <= 1 || isLoading}
                onClick={() => updateParams({ page: (page - 1).toString() })}
                className="p-1.5 rounded-lg border border-slate-300 bg-white hover:bg-[#F5F4EF] disabled:opacity-40 disabled:cursor-not-allowed text-[#253746] transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 font-mono text-[#253746] font-semibold">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages || isLoading}
                onClick={() => updateParams({ page: (page + 1).toString() })}
                className="p-1.5 rounded-lg border border-slate-300 bg-white hover:bg-[#F5F4EF] disabled:opacity-40 disabled:cursor-not-allowed text-[#253746] transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
