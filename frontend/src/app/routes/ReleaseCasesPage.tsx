import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Filter, AlertCircle, Clock } from 'lucide-react';
import { releaseApi, ReleaseRequest, ReleaseWorkflowStatus } from '@/api/release';
import { useAuth } from '@/features/auth/AuthContext';
import { cn } from '@/lib/utils';

const statusColors: Record<ReleaseWorkflowStatus, string> = {
  DRAFT: 'bg-slate-100 text-slate-800',
  SUBMITTED: 'bg-blue-100 text-blue-800',
  UNDER_REVIEW: 'bg-amber-100 text-amber-800',
  RETURNED_FOR_CORRECTION: 'bg-orange-100 text-orange-800',
  READY_FOR_AUTHORITY: 'bg-cyan-100 text-cyan-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  RELEASE_ORDER_RECORDED: 'bg-purple-100 text-purple-800',
  BANK_SIDE_ACTION_PENDING: 'bg-indigo-100 text-indigo-800',
  COMPLETED: 'bg-emerald-100 text-emerald-800',
  CLOSED: 'bg-slate-200 text-slate-900',
  CANCELLED: 'bg-slate-300 text-slate-900',
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Release / Refund Cases</h1>
          <p className="text-slate-600 mt-2">Manage and track FDR release, discharge, and refund requests</p>
        </div>
        {canCreateRequest && (
          <Link
            to="/release/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-sentinel-600 text-white rounded-lg hover:bg-sentinel-700 font-medium transition"
          >
            <Plus className="w-4 h-4" />
            New Request
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-4 space-y-4">
        <div className="flex gap-4 flex-wrap">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by case number, instrument..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sentinel-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-600" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sentinel-500 focus:border-transparent"
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
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <div>
            <h3 className="font-semibold text-red-900">Error Loading Cases</h3>
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center">
          <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3 animate-spin" />
          <p className="text-slate-600">Loading release cases...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && requests.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center">
          <AlertCircle className="w-8 h-8 text-slate-400 mx-auto mb-3" />
          <p className="text-slate-600 mb-4">No release cases found</p>
          {canCreateRequest && (
            <Link
              to="/release/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-sentinel-600 text-white rounded-lg hover:bg-sentinel-700 font-medium transition"
            >
              <Plus className="w-4 h-4" />
              Create First Request
            </Link>
          )}
        </div>
      )}

      {/* Cases Table */}
      {!isLoading && requests.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Case Number</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Instrument</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Type</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Status</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Created</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {requests.map((request) => (
                <tr key={request.id} className="hover:bg-slate-50 transition">
                  <td className="px-6 py-4">
                    <Link
                      to={`/release/${request.id}`}
                      className="text-sentinel-600 hover:text-sentinel-700 font-medium"
                    >
                      {request.case_number}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">{request.instrument_id}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{request.request_type}</td>
                  <td className="px-6 py-4">
                    <span className={cn('text-xs font-semibold px-3 py-1 rounded-full', statusColors[request.workflow_status])}>
                      {request.workflow_status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {new Date(request.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/release/${request.id}`}
                      className="text-sentinel-600 hover:text-sentinel-700 text-sm font-medium"
                    >
                      View →
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
