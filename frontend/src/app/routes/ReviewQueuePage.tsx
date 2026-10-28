import React, { useEffect, useState, useCallback } from 'react';
import { findingsApi, institutionsApi, usersApi } from '@/api/endpoints';
import type {
  ValidationFindingItem,
  Institution,
  User,
  PriorityScoreDetails,
} from '@/types';
import {
  Search,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  RefreshCw,
  XCircle,
  Info,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
  MessageSquare,
  AlertOctagon,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { Badge } from '@/components/common/Badge';
import { cn } from '@/lib/utils';

export const ReviewQueuePage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const canPerformActions = ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD'].includes(
    user?.role || ''
  );

  // Queue state
  const [items, setItems] = useState<ValidationFindingItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters initialized from searchParams if present
  const paramStatus = searchParams.get('status') || 'ACTIVE';
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>(paramStatus); // 'ACTIVE' = OPEN + IN_REVIEW, 'OPEN', 'IN_REVIEW', 'RESOLVED', 'DISMISSED', 'ALL'

  // Sync status if searchParams changes
  useEffect(() => {
    const nextStatus = searchParams.get('status') || 'ACTIVE';
    setStatusFilter(nextStatus);
    setPage(1);
  }, [searchParams]);
  const [severityFilter, setSeverityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [selectedInstFilter, setSelectedInstFilter] = useState('');
  const [sortBy, setSortBy] = useState('priority');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Auxiliary data
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [officers, setOfficers] = useState<User[]>([]);

  // Finding Detail & Actions Modal state
  const [activeFinding, setActiveFinding] = useState<ValidationFindingItem | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [activeScoreDetails, setActiveScoreDetails] = useState<PriorityScoreDetails | null>(null);

  // Dialog states
  const [actionType, setActionType] = useState<
    'RESOLVE' | 'DISMISS' | 'ASSIGN' | 'OBSERVE' | 'RETURN_CORRECTION' | null
  >(null);
  const [actionReason, setActionReason] = useState('');
  const [selectedOfficerId, setSelectedOfficerId] = useState('');
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Load institutions & officers for filter dropdowns if officer/admin
  useEffect(() => {
    async function fetchAuxData() {
      try {
        if (!isInstitutionUser) {
          const [instRes, usersRes] = await Promise.all([
            institutionsApi.list({ is_active: true, limit: 100 }),
            usersApi.list({ limit: 100 }),
          ]);
          setInstitutions(instRes.items);
          const eligibleOfficers = usersRes.items.filter((u) =>
            ['SCRUTINY_OFFICER', 'BRANCH_HEAD', 'SYSTEM_ADMIN'].includes(u.role)
          );
          setOfficers(eligibleOfficers);
        }
      } catch (e) {
        console.error('Failed to load filter metadata', e);
      }
    }
    fetchAuxData();
  }, [isInstitutionUser]);

  // Load review queue
  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      let statusParams: string[] | undefined;
      if (statusFilter === 'ACTIVE') {
        statusParams = ['OPEN', 'IN_REVIEW'];
      } else if (statusFilter !== 'ALL') {
        statusParams = [statusFilter];
      }

      const res = await findingsApi.getQueue({
        status: statusParams,
        severity: severityFilter || undefined,
        category: categoryFilter || undefined,
        institution_id: selectedInstFilter || undefined,
        search: search.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        skip: (page - 1) * pageSize,
        limit: pageSize,
      });

      setItems(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(
        err?.response?.data?.message || err?.message || 'Failed to retrieve discrepancy review queue.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter, severityFilter, categoryFilter, selectedInstFilter, sortBy, sortOrder, page]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // Handle status transition (e.g. IN_REVIEW, RESOLVED, DISMISSED)
  const handleStatusTransition = async (targetStatus: string, reason?: string) => {
    if (!activeFinding) return;
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await findingsApi.transitionStatus(activeFinding.id, {
        target_status: targetStatus,
        reason: reason || undefined,
        expected_concurrency_version: activeFinding.concurrency_version,
      });
      setActiveFinding(updated);
      setSuccessMsg(`Discrepancy successfully updated to ${targetStatus}.`);
      setActionType(null);
      setActionReason('');
      await loadQueue();
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || 'Failed to update finding status.';
      setActionError(msg);
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // Handle finding assignment
  const handleAssign = async () => {
    if (!activeFinding || !selectedOfficerId) return;
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await findingsApi.assign(activeFinding.id, {
        assigned_to_user_id: selectedOfficerId,
      });
      setActiveFinding(updated);
      setSuccessMsg('Discrepancy successfully assigned.');
      setActionType(null);
      setSelectedOfficerId('');
      await loadQueue();
    } catch (err: any) {
      setActionError(err?.response?.data?.message || err?.message || 'Failed to assign finding.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // Handle review observation
  const handleObservation = async () => {
    if (!activeFinding || !actionReason.trim()) return;
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await findingsApi.addObservation(activeFinding.id, {
        observation_text: actionReason.trim(),
      });
      setActiveFinding(updated);
      setSuccessMsg('Review observation recorded.');
      setActionType(null);
      setActionReason('');
      await loadQueue();
    } catch (err: any) {
      setActionError(err?.response?.data?.message || err?.message || 'Failed to add observation.');
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // Handle return for correction
  const handleReturnForCorrection = async () => {
    if (!activeFinding || !actionReason.trim()) return;
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      await findingsApi.returnForCorrection(activeFinding.instrument_id, {
        explanation: actionReason.trim(),
      });
      setSuccessMsg('Instrument returned to institution for correction.');
      setActionType(null);
      setActionReason('');
      await loadQueue();
      // Reload active finding
      const refreshed = await findingsApi.get(activeFinding.id);
      setActiveFinding(refreshed);
    } catch (err: any) {
      setActionError(
        err?.response?.data?.message || err?.message || 'Failed to return submission for correction.'
      );
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // Handle re-evaluation
  const handleReevaluate = async () => {
    if (!activeFinding) return;
    setIsLoading(true);
    setError(null);
    try {
      const updated = await findingsApi.reEvaluate(activeFinding.id);
      setActiveFinding(updated);
      setSuccessMsg('Discrepancy re-evaluated against latest instrument data and active policy.');
      await loadQueue();
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Re-evaluation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Helper badge renderers
  const renderSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <Badge variant="danger" className="font-mono text-[10px]">CRITICAL</Badge>;
      case 'HIGH':
        return <Badge variant="warning" className="font-mono text-[10px]">HIGH</Badge>;
      case 'MEDIUM':
        return <Badge variant="warning" className="font-mono text-[10px]">MEDIUM</Badge>;
      case 'LOW':
        return <Badge variant="info" className="font-mono text-[10px]">LOW</Badge>;
      default:
        return <Badge variant="default" className="font-mono text-[10px]">{severity}</Badge>;
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'OPEN':
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-none border border-rose-200"><AlertOctagon className="w-3 h-3" /> OPEN</span>;
      case 'IN_REVIEW':
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-none border border-amber-200"><Clock className="w-3 h-3" /> IN REVIEW</span>;
      case 'RESOLVED':
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-none border border-emerald-200"><CheckCircle2 className="w-3 h-3" /> RESOLVED</span>;
      case 'DISMISSED':
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#5D6A75] bg-slate-100 px-2 py-0.5 rounded-none border border-[#C9D3DB]"><XCircle className="w-3 h-3" /> DISMISSED</span>;
      case 'SUPERSEDED':
        return <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-none border border-indigo-200"><RefreshCw className="w-3 h-3" /> SUPERSEDED</span>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const renderPriorityBadge = (score: number, details: PriorityScoreDetails) => {
    let colorClass = 'bg-slate-100 text-[#253746] border-[#8799A9]';
    if (score >= 70) {
      colorClass = 'bg-rose-100 text-rose-800 border-rose-300 font-bold';
    } else if (score >= 40) {
      colorClass = 'bg-amber-100 text-amber-800 border-amber-300 font-semibold';
    } else {
      colorClass = 'bg-emerald-100 text-emerald-800 border-emerald-300 font-medium';
    }

    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          setActiveScoreDetails(details);
        }}
        className={cn(
          'inline-flex items-center gap-1 px-2.5 py-1 rounded-none text-xs border transition-all hover:scale-105 cursor-pointer shadow-sm',
          colorClass
        )}
        title="Click to view explainable factor score breakdown"
      >
        <ShieldAlert className="w-3.5 h-3.5" />
        <span>{score}</span>
        <span className="text-[9px] opacity-70">/100</span>
      </button>
    );
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto text-xs pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#C9D3DB] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-[#0D2538] tracking-tight">
              Discrepancy Review Queue
            </h1>
            <span className="text-[10px] bg-[#EEF6FA] text-[#0D2538] font-semibold px-2 py-0.5 rounded-none border border-[#C4DEED]">
              Module 3 — Audit & Governance
            </span>
          </div>
          <p className="text-[#5D6A75] mt-1 text-xs">
            {isInstitutionUser
              ? 'Actionable deficiencies and validation findings identified for your institution’s FDR submissions.'
              : 'Deterministic validation findings, cross-source discrepancies, and transparent priority queue for scrutiny officers.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadQueue()}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-none border border-[#8799A9] bg-white hover:bg-[#F5F4EF] text-[#253746] font-medium text-xs transition-colors shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-none flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 font-bold text-sm">
            &times;
          </button>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-none flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-700 font-bold text-sm">
            &times;
          </button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white border border-[#C9D3DB] rounded-none p-4 shadow-sm space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search reference, bank, rule code, title..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-[#F5F4EF] border border-[#C9D3DB] rounded-none text-xs focus:ring-1 focus:ring-sentinel-500 focus:bg-white outline-none transition-all"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <label className="text-[#5D6A75] font-medium shrink-0">Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-[#F5F4EF] border border-[#C9D3DB] rounded-none py-1.5 px-2.5 text-xs focus:ring-1 focus:ring-sentinel-500 outline-none"
            >
              <option value="ACTIVE">Active (Open & In Review)</option>
              <option value="OPEN">Open Only</option>
              <option value="IN_REVIEW">In Review Only</option>
              <option value="RESOLVED">Resolved Only</option>
              <option value="DISMISSED">Dismissed Only</option>
              <option value="ALL">All Statuses</option>
            </select>
          </div>

          {/* Severity Filter */}
          <div className="flex items-center gap-2">
            <label className="text-[#5D6A75] font-medium shrink-0">Severity:</label>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-[#F5F4EF] border border-[#C9D3DB] rounded-none py-1.5 px-2.5 text-xs focus:ring-1 focus:ring-sentinel-500 outline-none"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
              <option value="INFO">Info</option>
            </select>
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <label className="text-[#5D6A75] font-medium shrink-0">Category:</label>
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-[#F5F4EF] border border-[#C9D3DB] rounded-none py-1.5 px-2.5 text-xs focus:ring-1 focus:ring-sentinel-500 outline-none"
            >
              <option value="">All Categories</option>
              <option value="REQUIRED_FIELD">Required Fields</option>
              <option value="DATE_CONSISTENCY">Date Consistency</option>
              <option value="AMOUNT_CONSISTENCY">Amount Consistency</option>
              <option value="INSTITUTION_MATCH">Institution Match</option>
              <option value="DOCUMENT_INTEGRITY">Document Integrity</option>
              <option value="DUPLICATE_SUSPICION">Duplicate Suspicion</option>
              <option value="CROSS_SOURCE_RECONCILIATION">Cross-Source Reconciliation</option>
            </select>
          </div>
        </div>

        {/* Second Row: Institution filter & Sort */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-1 border-t border-slate-100">
          {!isInstitutionUser && (
            <div className="flex items-center gap-2 col-span-2">
              <label className="text-[#5D6A75] font-medium shrink-0">Institution:</label>
              <select
                value={selectedInstFilter}
                onChange={(e) => {
                  setSelectedInstFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-[#F5F4EF] border border-[#C9D3DB] rounded-none py-1.5 px-2.5 text-xs focus:ring-1 focus:ring-sentinel-500 outline-none"
              >
                <option value="">All Institutions</option>
                {institutions.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.code} — {i.display_name || i.legal_name || i.name} ({i.city})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-2">
            <label className="text-[#5D6A75] font-medium shrink-0">Sort By:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full bg-[#F5F4EF] border border-[#C9D3DB] rounded-none py-1.5 px-2.5 text-xs focus:ring-1 focus:ring-sentinel-500 outline-none"
            >
              <option value="priority">Priority Score (0–100)</option>
              <option value="detected_at">First Detected Date</option>
              <option value="severity">Finding Severity</option>
              <option value="status">Finding Status</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-[#5D6A75] font-medium shrink-0">Order:</label>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              className="w-full bg-[#F5F4EF] border border-[#C9D3DB] rounded-none py-1.5 px-2.5 text-xs focus:ring-1 focus:ring-sentinel-500 outline-none"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
        </div>
      </div>

      {/* Review Queue Findings Table */}
      <div className="bg-white border border-[#C9D3DB] rounded-none overflow-hidden shadow-sm">
        <div className="px-4 py-3 border-b border-[#C9D3DB] flex items-center justify-between bg-[#F5F4EF]">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#253746]">Review Queue Discrepancies</span>
            <span className="bg-slate-200 text-[#253746] text-[10px] font-bold px-2 py-0.5 rounded-none">
              {total} items
            </span>
          </div>
          <span className="text-[11px] text-slate-400">
            Page {page} of {totalPages}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-100/70 border-b border-[#C9D3DB] text-[#5D6A75] font-semibold text-[11px]">
                <th className="py-2.5 px-3">Priority</th>
                <th className="py-2.5 px-3">Severity</th>
                <th className="py-2.5 px-3">Instrument / Bank</th>
                <th className="py-2.5 px-3">Discrepancy Title</th>
                <th className="py-2.5 px-3">Rule / Type</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Detected</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#123B5D]" />
                    Loading review queue items...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-emerald-500 opacity-60" />
                    No discrepancies match the active filter criteria.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => {
                      setActiveFinding(item);
                      setIsDetailOpen(true);
                    }}
                    className="hover:bg-[#F5F4EF] transition-colors cursor-pointer group"
                  >
                    {/* Priority Score */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {renderPriorityBadge(item.priority_score, item.priority_score_details)}
                    </td>

                    {/* Severity */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {renderSeverityBadge(item.severity)}
                    </td>

                    {/* Instrument / Bank */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <div className="font-medium text-[#253746]">
                        {item.instrument_summary?.reference_number || item.instrument_id.substring(0, 8)}
                      </div>
                      <div className="text-[10px] text-[#5D6A75]">
                        {item.instrument_summary?.bank_name || 'Bank Unspecified'}
                      </div>
                    </td>

                    {/* Title */}
                    <td className="py-2.5 px-3 max-w-xs">
                      <div className="font-medium text-[#253746] truncate" title={item.title}>
                        {item.title}
                      </div>
                      {item.suggested_action && (
                        <div className="text-[10px] text-[#5D6A75] truncate" title={item.suggested_action}>
                          Action: {item.suggested_action}
                        </div>
                      )}
                    </td>

                    {/* Rule / Type */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <div className="font-mono text-[10px] text-[#253746]">{item.rule_id}</div>
                      <div className="text-[10px] text-[#5D6A75]">
                        {item.rule_type === 'HEURISTIC' ? (
                          <span className="text-amber-600 font-semibold">Advisory Heuristic</span>
                        ) : (
                          <span className="text-[#5D6A75]">Deterministic</span>
                        )}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {renderStatusBadge(item.status)}
                    </td>

                    {/* Detected At */}
                    <td className="py-2.5 px-3 whitespace-nowrap text-[#5D6A75] text-[11px]">
                      {item.first_detected_at ? new Date(item.first_detected_at).toLocaleDateString() : '—'}
                    </td>

                    {/* Detail Link */}
                    <td className="py-2.5 px-3 whitespace-nowrap text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveFinding(item);
                          setIsDetailOpen(true);
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-none bg-slate-100 group-hover:bg-[#EEF6FA] text-[#5D6A75] group-hover:text-[#123B5D] font-medium text-[11px] transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-4 py-3 border-t border-[#C9D3DB] flex items-center justify-between bg-[#F5F4EF]">
          <span className="text-[#5D6A75] text-[11px]">
            Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total} findings
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              disabled={page <= 1}
              className="p-1 rounded-none border border-[#8799A9] bg-white hover:bg-[#F5F4EF] disabled:opacity-40 disabled:cursor-not-allowed text-[#5D6A75]"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 text-[#5D6A75] font-semibold">{page}</span>
            <button
              onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
              disabled={page >= totalPages}
              className="p-1 rounded-none border border-[#8799A9] bg-white hover:bg-[#F5F4EF] disabled:opacity-40 disabled:cursor-not-allowed text-[#5D6A75]"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* Finding Detail & Officer Action Drawer / Modal */}
      {/* ========================================================================= */}
      {isDetailOpen && activeFinding && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex justify-end transition-opacity">
          <div className="bg-white w-full max-w-2xl h-full shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
            {/* Modal Header */}
            <div className="p-4 border-b border-[#C9D3DB] flex items-start justify-between bg-[#F5F4EF]">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  {renderSeverityBadge(activeFinding.severity)}
                  {renderStatusBadge(activeFinding.status)}
                  <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200 px-2 py-0.5 rounded-none">
                    v{activeFinding.concurrency_version}
                  </span>
                </div>
                <h2 className="text-base font-bold text-[#0D2538] leading-snug">
                  {activeFinding.title}
                </h2>
                <div className="flex items-center gap-3 text-[#5D6A75] text-[11px]">
                  <span>Rule: <strong className="font-mono text-[#253746]">{activeFinding.rule_id}</strong> (v{activeFinding.rule_version})</span>
                  <span>Category: <strong className="text-[#253746]">{activeFinding.category}</strong></span>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsDetailOpen(false);
                  setActionType(null);
                  setActionError(null);
                }}
                className="text-slate-400 hover:text-[#5D6A75] p-1 rounded-none hover:bg-slate-100"
              >
                &times;
              </button>
            </div>

            {/* Modal Content Scrollable Area */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Plain-Language Explanation */}
              <div className="bg-[#F5F4EF] border border-[#C9D3DB] rounded-none p-3.5 space-y-2">
                <div className="flex items-center gap-2 text-[#253746] font-semibold text-xs">
                  <Info className="w-4 h-4 text-[#123B5D]" />
                  <span>Explainable Finding Details</span>
                </div>
                <p className="text-[#253746] text-xs leading-relaxed">
                  {activeFinding.explanation || 'No detailed explanation provided for this finding.'}
                </p>

                {/* Values comparison */}
                {(activeFinding.observed_value || activeFinding.expected_value) && (
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#C9D3DB] text-xs">
                    <div className="bg-rose-50 border border-rose-100 rounded-none p-2">
                      <span className="text-[10px] font-semibold text-rose-800 block">Observed Value</span>
                      <span className="font-mono text-[#253746] break-words">
                        {activeFinding.observed_value || 'None'}
                      </span>
                    </div>
                    <div className="bg-emerald-50 border border-emerald-100 rounded-none p-2">
                      <span className="text-[10px] font-semibold text-emerald-800 block">Expected / Baseline</span>
                      <span className="font-mono text-[#253746] break-words">
                        {activeFinding.expected_value || 'None'}
                      </span>
                    </div>
                  </div>
                )}

                {activeFinding.suggested_action && (
                  <div className="text-[11px] text-[#0D2538] bg-[#EEF6FA] border border-sentinel-100 rounded-none p-2">
                    <strong>Recommended Next Action:</strong> {activeFinding.suggested_action}
                  </div>
                )}
              </div>

              {/* Priority Score Breakdown Card */}
              <div className="border border-[#C9D3DB] rounded-none p-3.5 space-y-2 bg-white">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#253746] font-semibold text-xs">
                    <ShieldAlert className="w-4 h-4 text-amber-500" />
                    <span>Review Priority Ordering Score: <strong>{activeFinding.priority_score} / 100</strong></span>
                  </div>
                  <button
                    onClick={() => setActiveScoreDetails(activeFinding.priority_score_details)}
                    className="text-[#123B5D] hover:text-[#0D2538] font-medium text-[11px] underline"
                  >
                    View Formula & Basis
                  </button>
                </div>
                <p className="text-[11px] text-[#5D6A75] leading-normal">
                  {activeFinding.priority_score_details?.summary_explanation}
                </p>
              </div>

              {/* Classification & Evidence References */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="border border-[#C9D3DB] rounded-none p-3 space-y-1">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase">Rule Classification</span>
                  <div className="font-medium text-[#253746]">
                    {activeFinding.rule_type === 'HEURISTIC' ? 'Heuristic Advisory Indicator' : 'Deterministic Rule'}
                  </div>
                  <div className="text-[10px] text-[#5D6A75]">
                    {activeFinding.rule_type === 'HEURISTIC'
                      ? 'Advisory guidance only. Requires officer review; does not block automatically.'
                      : 'Deterministic hard rule enforced by configured policy specification.'}
                  </div>
                </div>

                <div className="border border-[#C9D3DB] rounded-none p-3 space-y-1">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase">Policy Version Ref</span>
                  <div className="font-mono text-[#253746] text-[11px]">
                    {activeFinding.policy_version_ref || 'global-default'}
                  </div>
                  <span className="text-[10px] text-slate-400 font-semibold uppercase block pt-1">Evidence References</span>
                  <div className="text-[10px] text-[#5D6A75] font-mono truncate">
                    {activeFinding.evidence_refs?.length
                      ? activeFinding.evidence_refs.join(', ')
                      : 'Instrument submission metadata'}
                  </div>
                </div>
              </div>

              {/* Review History / Audit Timeline */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[#253746] font-semibold text-xs">
                  <MessageSquare className="w-4 h-4 text-[#5D6A75]" />
                  <span>Review Observations & Action History</span>
                </div>

                <div className="border border-[#C9D3DB] rounded-none divide-y divide-slate-100 bg-white max-h-48 overflow-y-auto">
                  {activeFinding.review_notes && activeFinding.review_notes.length > 0 ? (
                    activeFinding.review_notes.map((note, idx) => (
                      <div key={note.id || idx} className="p-3 text-xs space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-[#5D6A75]">
                          <span className="font-semibold text-[#253746]">
                            {note.actor_email} ({note.actor_role})
                          </span>
                          <span>{new Date(note.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="font-mono text-[11px] font-bold text-[#0D2538]">
                          {note.action}
                        </div>
                        {note.reason && (
                          <div className="text-[#5D6A75] bg-[#F5F4EF] border border-slate-100 rounded-none p-1.5 text-[11px]">
                            <strong>Reason:</strong> {note.reason}
                          </div>
                        )}
                        {note.note && (
                          <div className="text-[#5D6A75] bg-[#F5F4EF] border border-slate-100 rounded-none p-1.5 text-[11px]">
                            {note.note}
                          </div>
                        )}
                        {note.assigned_to && (
                          <div className="text-[11px] text-indigo-700">
                            Assigned to: {note.assigned_to}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="p-4 text-center text-slate-400 text-xs">
                      No review observations or actions recorded yet.
                    </div>
                  )}
                </div>
              </div>

              {/* Officer Action Panel (if authorized) */}
              {canPerformActions && (
                <div className="border-t border-[#C9D3DB] pt-4 space-y-3">
                  <h3 className="font-semibold text-[#253746] text-xs">Officer Workflow Actions</h3>

                  {actionError && (
                    <div className="bg-rose-50 border border-rose-200 text-rose-800 p-2.5 rounded-none text-xs">
                      {actionError}
                    </div>
                  )}

                  {/* Primary Action Buttons */}
                  {!actionType ? (
                    <div className="flex flex-wrap gap-2">
                      {activeFinding.status === 'OPEN' && (
                        <button
                          onClick={() => handleStatusTransition('IN_REVIEW')}
                          disabled={isSubmittingAction}
                          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-none text-xs font-medium transition-colors shadow-sm"
                        >
                          Mark In Review
                        </button>
                      )}

                      {['OPEN', 'IN_REVIEW'].includes(activeFinding.status) && (
                        <>
                          <button
                            onClick={() => {
                              setActionType('RESOLVE');
                              setActionReason('');
                            }}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-none text-xs font-medium transition-colors shadow-sm"
                          >
                            Resolve Discrepancy...
                          </button>

                          <button
                            onClick={() => {
                              setActionType('DISMISS');
                              setActionReason('');
                            }}
                            className="px-3 py-1.5 bg-slate-600 hover:bg-slate-700 text-white rounded-none text-xs font-medium transition-colors shadow-sm"
                          >
                            Dismiss with Reason...
                          </button>
                        </>
                      )}

                      <button
                        onClick={() => {
                          setActionType('OBSERVE');
                          setActionReason('');
                        }}
                        className="px-3 py-1.5 border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] rounded-none text-xs font-medium transition-colors shadow-sm"
                      >
                        Add Observation
                      </button>

                      <button
                        onClick={() => {
                          setActionType('ASSIGN');
                        }}
                        className="px-3 py-1.5 border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] rounded-none text-xs font-medium transition-colors shadow-sm"
                      >
                        Assign Officer...
                      </button>

                      <button
                        onClick={() => {
                          setActionType('RETURN_CORRECTION');
                          setActionReason('');
                        }}
                        className="px-3 py-1.5 bg-rose-50 border border-rose-200 hover:bg-rose-100 text-rose-700 rounded-none text-xs font-medium transition-colors shadow-sm"
                      >
                        Return for Correction...
                      </button>

                      <button
                        onClick={handleReevaluate}
                        disabled={isLoading}
                        className="px-3 py-1.5 border border-[#8799A9] hover:bg-[#F5F4EF] text-[#253746] rounded-none text-xs font-medium transition-colors shadow-sm inline-flex items-center gap-1"
                      >
                        <RefreshCw className={cn('w-3 h-3', isLoading && 'animate-spin')} />
                        Re-evaluate Finding
                      </button>
                    </div>
                  ) : (
                    /* Inline Action Confirmation Form */
                    <div className="bg-[#F5F4EF] border border-[#C9D3DB] rounded-none p-3 space-y-3">
                      <div className="flex items-center justify-between font-semibold text-[#253746] text-xs">
                        <span>
                          {actionType === 'RESOLVE' && 'Resolve Finding (Mandatory Reason Required)'}
                          {actionType === 'DISMISS' && 'Dismiss Finding (Mandatory Reason Required)'}
                          {actionType === 'OBSERVE' && 'Add Officer Review Observation'}
                          {actionType === 'ASSIGN' && 'Assign Finding to Officer'}
                          {actionType === 'RETURN_CORRECTION' && 'Return Submission for Correction (Mandatory Explanation)'}
                        </span>
                        <button
                          onClick={() => {
                            setActionType(null);
                            setActionError(null);
                          }}
                          className="text-slate-400 hover:text-[#5D6A75] text-xs"
                        >
                          Cancel
                        </button>
                      </div>

                      {actionType === 'ASSIGN' ? (
                        <div className="space-y-2">
                          <label className="text-[11px] text-[#5D6A75]">Select Authorized Officer:</label>
                          <select
                            value={selectedOfficerId}
                            onChange={(e) => setSelectedOfficerId(e.target.value)}
                            className="w-full bg-white border border-[#C9D3DB] rounded-none p-2 text-xs outline-none"
                          >
                            <option value="">-- Choose Officer --</option>
                            {officers.map((o) => (
                              <option key={o.id} value={o.id}>
                                {o.full_name} ({o.email}) - {o.role}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={handleAssign}
                            disabled={!selectedOfficerId || isSubmittingAction}
                            className="px-3 py-1.5 bg-[#123B5D] hover:bg-[#0D2538] text-white rounded-none text-xs font-semibold disabled:opacity-50"
                          >
                            Confirm Assignment
                          </button>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <textarea
                            placeholder={
                              actionType === 'RETURN_CORRECTION'
                                ? 'State the explicit deficiency and instructions for the institution...'
                                : 'Enter detailed audit rationale (at least 10 characters, cannot be whitespace-only)...'
                            }
                            value={actionReason}
                            onChange={(e) => setActionReason(e.target.value)}
                            rows={3}
                            className="w-full bg-white border border-[#C9D3DB] rounded-none p-2 text-xs outline-none focus:ring-1 focus:ring-sentinel-500"
                          />
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-slate-400">
                              {actionReason.trim().length} chars (minimum 10 required)
                            </span>
                            <button
                              onClick={() => {
                                if (actionType === 'RESOLVE') handleStatusTransition('RESOLVED', actionReason);
                                else if (actionType === 'DISMISS') handleStatusTransition('DISMISSED', actionReason);
                                else if (actionType === 'OBSERVE') handleObservation();
                                else if (actionType === 'RETURN_CORRECTION') handleReturnForCorrection();
                              }}
                              disabled={
                                actionReason.trim().length < (actionType === 'OBSERVE' ? 3 : 10) ||
                                isSubmittingAction
                              }
                              className="px-3 py-1.5 bg-[#123B5D] hover:bg-[#0D2538] text-white rounded-none text-xs font-semibold disabled:opacity-50"
                            >
                              {isSubmittingAction ? 'Submitting...' : 'Confirm Action'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-3 border-t border-[#C9D3DB] bg-[#F5F4EF] flex items-center justify-between text-[#5D6A75] text-[11px]">
              <span>First detected: {activeFinding.first_detected_at ? new Date(activeFinding.first_detected_at).toLocaleString() : '—'}</span>
              <span>Last evaluated: {activeFinding.last_evaluated_at ? new Date(activeFinding.last_evaluated_at).toLocaleString() : '—'}</span>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Priority Score Transparent Factor Breakdown Modal (USP) */}
      {/* ========================================================================= */}
      {activeScoreDetails && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-none shadow-2xl max-w-xl w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="p-4 border-b border-[#C9D3DB] flex items-center justify-between bg-[#F5F4EF]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-[#0D2538] text-sm">
                  Review Priority Score Breakdown ({activeScoreDetails.total_score} / 100)
                </h3>
              </div>
              <button
                onClick={() => setActiveScoreDetails(null)}
                className="text-slate-400 hover:text-[#5D6A75] font-bold text-lg"
              >
                &times;
              </button>
            </div>

            {/* Content */}
            <div className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
              {/* Disclaimer Banner */}
              <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-none p-3 text-xs leading-relaxed">
                <strong>Transparent Review-Ordering Metric:</strong> {activeScoreDetails.disclaimer}
              </div>

              {/* Factor Contribution Table */}
              <div className="space-y-2">
                <span className="font-semibold text-[#253746] text-xs">Deterministic Factor Breakdown</span>
                <div className="border border-[#C9D3DB] rounded-none divide-y divide-slate-100 overflow-hidden">
                  {activeScoreDetails.factor_breakdown.map((f, i) => (
                    <div key={i} className="p-3 text-xs space-y-1 bg-white">
                      <div className="flex items-center justify-between font-medium">
                        <span className="text-[#253746] capitalize">
                          {f.factor_name.replace(/_/g, ' ')}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {f.is_missing ? (
                            <span className="text-[10px] bg-slate-100 text-[#5D6A75] px-1.5 py-0.5 rounded-none border border-[#C9D3DB]">
                              Unknown/Missing
                            </span>
                          ) : (
                            <span className="font-bold text-[#253746]">
                              {f.points} <span className="text-slate-400 font-normal">/ {f.max_points} pts</span>
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-[11px] text-[#5D6A75] leading-normal">{f.basis}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Missing Fields Note */}
              {activeScoreDetails.missing_fields && activeScoreDetails.missing_fields.length > 0 && (
                <div className="text-[11px] text-[#5D6A75] bg-[#F5F4EF] border border-[#C9D3DB] rounded-none p-2.5">
                  <strong>Missing / Non-penalized Inputs:</strong>{' '}
                  {activeScoreDetails.missing_fields.join(', ')}
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Missing values are explicitly recorded as unknown and assign 0 priority points without penalizing the institution.
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-[#C9D3DB] bg-[#F5F4EF] flex justify-end">
              <button
                onClick={() => setActiveScoreDetails(null)}
                className="px-4 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded-none text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
