import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Filter, AlertCircle, Clock } from 'lucide-react';
import { releaseApi, ReleaseRequest, ReleaseWorkflowStatus } from '@/api/release';
import { useAuth } from '@/features/auth/AuthContext';
import { Badge } from '@/components/common/Badge';

const getStatusBadgeVariant = (status: ReleaseWorkflowStatus): 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'teal' => {
  switch (status) {
    case 'APPROVED':
    case 'COMPLETED':
      return 'success';
    case 'UNDER_REVIEW':
    case 'BANK_SIDE_ACTION_PENDING':
    case 'READY_FOR_AUTHORITY':
      return 'warning';
    case 'REJECTED':
    case 'CANCELLED':
      return 'danger';
    case 'SUBMITTED':
      return 'info';
    case 'RELEASE_ORDER_RECORDED':
      return 'purple';
    default:
      return 'default';
  }
};

export const ReleaseCasesPage: React.FC = () => {
  const { user } = useAuth();
  const [requests, setRequests] = useState<ReleaseRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ReleaseWorkflowStatus | 'ALL'>('ALL');

  useEffect(() => {
    const fetchRequests = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const params: any = { limit: 20 };
        if (statusFilter !== 'ALL') params.status = statusFilter;
        if (search) params.search = search;
        const response = await releaseApi.list(params);
        setRequests(response);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load cases';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRequests();
  }, [statusFilter, search]);

  const canCreateRequest = ['INSTITUTION_USER'].includes(user?.role || '');

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#C9D3DB] pb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-[#0D2538] tracking-tight">Release & Refund Cases</h1>
          <p className="text-xs text-[#5D6A75] mt-1 font-medium">
            Manage and track statutory FDR release, discharge, and refund requests with maker-checker governance.
          </p>
        </div>
        {canCreateRequest && (
          <Link
            to="/release/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#123B5D] text-white rounded-[8px] hover:bg-[#0D2538] text-xs font-semibold shadow-xs transition"
          >
            <Plus className="w-4 h-4" />
            New Request
          </Link>
        )}
      </div>

      {/* Filters - Structured Brutalism */}
      <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 space-y-4 shadow-[0_1px_3px_rgba(13,37,56,0.04)]">
        <div className="flex gap-4 flex-wrap">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-[#5D6A75]" />
              <input
                type="text"
                placeholder="Search by case number, instrument..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-[#C9D3DB] rounded-[6px] text-xs text-[#253746] focus:ring-2 focus:ring-[#145DA0] focus:border-transparent font-mono bg-[#F5F4EF]"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#5D6A75]" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-3 py-2 border border-[#C9D3DB] rounded-[6px] text-xs text-[#253746] focus:ring-2 focus:ring-[#145DA0] focus:border-transparent bg-[#F5F4EF] font-mono"
            >
              <option value="ALL">All Status</option>
              <option value="DRAFT">Draft</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="RETURNED_FOR_CORRECTION">Returned for Correction</option>
              <option value="READY_FOR_AUTHORITY">Ready for Authority</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="COMPLETED">Completed</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-[#FDF2F1] border border-[#FECDCA] rounded-[8px] p-4 flex gap-3 text-xs">
          <AlertCircle className="w-5 h-5 text-[#B42318] shrink-0" />
          <div>
            <h3 className="font-semibold text-[#B42318]">Error Loading Cases</h3>
            <p className="text-[#B42318]/90 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-8 text-center">
          <Clock className="w-8 h-8 text-[#5D6A75] mx-auto mb-3 animate-spin" />
          <p className="text-xs text-[#5D6A75]">Loading release cases...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && requests.length === 0 && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-8 text-center">
          <AlertCircle className="w-8 h-8 text-[#8799A9] mx-auto mb-3" />
          <p className="text-sm font-semibold text-[#0D2538] mb-1">No release cases found</p>
          <p className="text-xs text-[#5D6A75] mb-4">No records matched your search criteria or tenant scope.</p>
          {canCreateRequest && (
            <Link
              to="/release/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#123B5D] text-white rounded-[8px] hover:bg-[#0D2538] text-xs font-semibold transition"
            >
              <Plus className="w-4 h-4" />
              Create First Request
            </Link>
          )}
        </div>
      )}

      {/* Cases Table - Structured Brutalism */}
      {!isLoading && requests.length > 0 && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] overflow-hidden shadow-[0_1px_3px_rgba(13,37,56,0.04)]">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#F5F4EF] border-b border-[#C9D3DB] uppercase tracking-wider font-semibold text-[#5D6A75]">
              <tr>
                <th className="px-6 py-3 font-semibold">Case Number</th>
                <th className="px-6 py-3 font-semibold">Instrument</th>
                <th className="px-6 py-3 font-semibold">Type</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold">Created</th>
                <th className="px-6 py-3 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#C9D3DB] font-mono">
              {requests.map((request) => (
                <tr key={request.id} className="hover:bg-[#F5F4EF]/70 transition-colors">
                  <td className="px-6 py-3.5 font-bold text-[#123B5D]">
                    <Link
                      to={`/release/${request.id}`}
                      className="hover:underline flex items-center gap-1"
                    >
                      {request.case_number}
                    </Link>
                  </td>
                  <td className="px-6 py-3.5 text-[#253746] font-mono">{request.instrument_id}</td>
                  <td className="px-6 py-3.5 text-[#5D6A75] font-sans font-medium">{request.request_type}</td>
                  <td className="px-6 py-3.5">
                    <Badge variant={getStatusBadgeVariant(request.workflow_status)}>
                      {request.workflow_status.replace(/_/g, ' ')}
                    </Badge>
                  </td>
                  <td className="px-6 py-3.5 text-[#5D6A75]">
                    {new Date(request.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-3.5 text-right font-sans">
                    <Link
                      to={`/release/${request.id}`}
                      className="text-[#0F766E] hover:text-[#09544E] font-semibold text-xs inline-flex items-center gap-1"
                    >
                      View Details →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

