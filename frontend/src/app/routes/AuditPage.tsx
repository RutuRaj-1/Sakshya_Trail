import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  auditApi,
  AuditEventItem,
  AuditChainVerificationResponse,
} from '@/api/endpoints';
import { useAuth } from '@/features/auth/AuthContext';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { formatDate } from '@/lib/utils';
import {
  History,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Search,
  RefreshCw,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  Copy,
  Check,
  AlertTriangle,
  Lock,
  Database,
  FileText,
} from 'lucide-react';

export const AuditPage: React.FC = () => {
  const { user } = useAuth();

  // Audit Events state
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [search, setSearch] = useState<string>('');
  const [actionFilter, setActionFilter] = useState<string>('');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const pageSize = 20;

  // Verification state
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] =
    useState<AuditChainVerificationResponse | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  // Detail Modal state
  const [selectedEvent, setSelectedEvent] = useState<AuditEventItem | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Check role authorization for verification
  const canVerify =
    user?.role === 'SYSTEM_ADMIN' ||
    user?.role === 'AUDITOR' ||
    user?.role === 'BRANCH_HEAD' ||
    user?.role === 'COMPETENT_AUTHORITY';

  const loadEvents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await auditApi.list({
        search: search.trim() || undefined,
        action: actionFilter || undefined,
        outcome: outcomeFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        skip: page * pageSize,
        limit: pageSize,
      });
      setEvents(res.items || []);
      setTotalCount(res.total || 0);
    } catch (err: any) {
      setError(err?.message || 'Failed to retrieve audit events from secure ledger.');
      setEvents([]);
    } finally {
      setIsLoading(false);
    }
  }, [search, actionFilter, outcomeFilter, dateFrom, dateTo, page]);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  const handleVerifyChain = async () => {
    setIsVerifying(true);
    setVerificationError(null);
    try {
      const res = await auditApi.verifyChain();
      setVerificationResult(res);
      // Refresh event list to capture the verification audit event
      loadEvents();
    } catch (err: any) {
      setVerificationError(
        err?.response?.data?.detail || err?.message || 'Integrity verification request failed.'
      );
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(label);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleResetFilters = () => {
    setSearch('');
    setActionFilter('');
    setOutcomeFilter('');
    setDateFrom('');
    setDateTo('');
    setPage(0);
  };

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case 'SUCCESS':
        return <Badge variant="success">SUCCESS</Badge>;
      case 'DENIED':
        return <Badge variant="warning">DENIED</Badge>;
      case 'FAILURE':
        return <Badge variant="danger">FAILURE</Badge>;
      default:
        return <Badge variant="default">{outcome}</Badge>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-sentinel-600" /> Tamper-Evident Audit Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographically chained SHA-256 regulatory ledger enforcing append-only immutability (PRD-FR-091, FR-092, FR-093).
          </p>
        </div>

        {canVerify && (
          <div className="flex items-center gap-2">
            <Button
              id="verify-chain-button"
              variant="primary"
              size="sm"
              disabled={isVerifying}
              onClick={handleVerifyChain}
              className="gap-2 shadow-xs bg-sentinel-700 hover:bg-sentinel-800"
            >
              <ShieldCheck className={`w-4 h-4 ${isVerifying ? 'animate-spin' : ''}`} />
              {isVerifying ? 'Replaying Cryptographic Chain...' : 'Verify Audit Chain'}
            </Button>
          </div>
        )}
      </div>

      {/* Verification Status Banner */}
      {verificationResult && (
        <div
          data-testid="verification-status-banner"
          className={`p-4 rounded-xl border transition-all ${
            verificationResult.is_chain_intact
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
              : 'bg-rose-50/90 border-rose-300 text-rose-900 shadow-sm'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              {verificationResult.is_chain_intact ? (
                <ShieldCheck className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <ShieldAlert className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">
                    {verificationResult.is_chain_intact
                      ? 'Audit Ledger Integrity Verified (PASS)'
                      : 'Cryptographic Chain Integrity Inconsistency Detected (TAMPER_DETECTED)'}
                  </span>
                  <Badge variant={verificationResult.is_chain_intact ? 'success' : 'danger'}>
                    {verificationResult.status}
                  </Badge>
                </div>
                <p className="text-xs mt-1 text-slate-600">
                  {verificationResult.verification_scope_description}
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 pt-3 border-t border-slate-200/60 font-mono text-[11px]">
                  <div>
                    <span className="text-slate-500 block">Verified Count:</span>
                    <span className="font-semibold text-slate-800">
                      {verificationResult.verified_count} / {verificationResult.total_events_in_scope} events
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Latest Sequence:</span>
                    <span className="font-semibold text-slate-800">
                      Block #{verificationResult.latest_sequence_number ?? 'None'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Verification Time:</span>
                    <span className="text-slate-700">
                      {formatDate(verificationResult.verification_timestamp)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Chain Head Digest:</span>
                    <span className="text-slate-700 truncate block max-w-40" title={verificationResult.chain_head_hash || ''}>
                      {verificationResult.chain_head_hash ? `${verificationResult.chain_head_hash.slice(0, 12)}...` : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* If Inconsistency detected, show forensic diagnosis */}
                {verificationResult.first_inconsistency && (
                  <div className="mt-4 p-3 bg-white/80 rounded-lg border border-rose-300 font-mono text-xs text-rose-950 space-y-1">
                    <div className="font-bold text-rose-700 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" /> Earliest Detected Inconsistency at Sequence #{verificationResult.first_inconsistency.sequence_number}:
                    </div>
                    <div><strong>Failure Mode:</strong> {verificationResult.first_inconsistency.failure_type}</div>
                    <div><strong>Event UUID:</strong> {verificationResult.first_inconsistency.event_id}</div>
                    <div><strong>Expected Digest:</strong> {verificationResult.first_inconsistency.expected_hash || 'None'}</div>
                    <div><strong>Stored Digest:</strong> {verificationResult.first_inconsistency.actual_hash || 'None'}</div>
                    <p className="font-sans text-rose-900 mt-2 text-[11px] bg-rose-100/60 p-2 rounded">
                      <strong>Security Advisory:</strong> {verificationResult.first_inconsistency.safe_explanation}. This ledger inconsistency has been formally logged to the compliance registry. Database tampering or unauthorized sequence manipulation must be escalated to the Competent Authority.
                    </p>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={() => setVerificationResult(null)}
              className="text-slate-400 hover:text-slate-600 p-1"
              title="Dismiss banner"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {verificationError && (
        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>Verification Request Failed: {verificationError}</span>
          </div>
          <button onClick={() => setVerificationError(null)} className="text-rose-500 hover:text-rose-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter and Query Desk */}
      <Card className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Keyword Search */}
          <div className="lg:col-span-2 relative">
            <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Search Event / Entity ID / Actor
            </label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search UUID, action, or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && setPage(0)}
                className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sentinel-500 focus:bg-white transition-all font-mono"
              />
            </div>
          </div>

          {/* Action Filter */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Action Family
            </label>
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(0);
              }}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono"
            >
              <option value="">All Action Types</option>
              <option value="AUTH_LOGIN_SUCCESS">AUTH_LOGIN_SUCCESS</option>
              <option value="AUTH_LOGIN_FAILED">AUTH_LOGIN_FAILED</option>
              <option value="UNAUTHORIZED_CROSS_TENANT_DASHBOARD_ACCESS">UNAUTHORIZED_ACCESS_DENIED</option>
              <option value="INSTRUMENT_CREATED">INSTRUMENT_CREATED</option>
              <option value="INSTRUMENT_SCRUTINY_OBSERVATION_RECORDED">SCRUTINY_OBSERVATION</option>
              <option value="VERIFICATION_STATUS_CHANGED">VERIFICATION_STATUS</option>
              <option value="TRUST_ASSESSMENT_COMPLETED">TRUST_ASSESSMENT</option>
              <option value="RELEASE_REQUEST_SUBMITTED">RELEASE_REQUEST</option>
              <option value="RELEASE_APPROVAL_RECORDED">RELEASE_APPROVED</option>
              <option value="RELEASE_REJECTION_RECORDED">RELEASE_REJECTED</option>
              <option value="POLICY_UPDATED">POLICY_UPDATED</option>
              <option value="REPORT_EXPORT_CSV_PENDING_VERIFICATION">REPORT_EXPORT_CSV</option>
              <option value="REPORT_EXPORT_PDF_UPCOMING_MATURITIES">REPORT_EXPORT_PDF</option>
              <option value="AUDIT_CHAIN_INTEGRITY_VERIFICATION">CHAIN_VERIFICATION</option>
            </select>
          </div>

          {/* Outcome Filter */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Outcome
            </label>
            <select
              value={outcomeFilter}
              onChange={(e) => {
                setOutcomeFilter(e.target.value);
                setPage(0);
              }}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono"
            >
              <option value="">All Outcomes</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="DENIED">DENIED (Unauthorized)</option>
              <option value="FAILURE">FAILURE (System Error)</option>
            </select>
          </div>

          {/* Date Range & Controls */}
          <div>
            <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Date Filter
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(0);
                }}
                className="w-full text-[11px] bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-sentinel-500"
                title="Date From"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="p-1.5 shrink-0 text-slate-500 hover:text-slate-800"
                title="Reset Filters"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Events Table Container */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-500">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
            <p className="text-sm font-medium">Replaying audit sequence...</p>
            <p className="text-xs text-slate-400 mt-1">Reading cryptographic hash chains from append-only storage</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center text-rose-600">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="text-sm font-semibold">{error}</p>
            <Button variant="outline" size="sm" onClick={loadEvents} className="mt-3">
              Retry Query
            </Button>
          </div>
        ) : events.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <Shield className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">No Matching Audit Records</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
              No audit events matched your filter criteria or tenant authorization scope.
            </p>
            {(search || actionFilter || outcomeFilter || dateFrom) && (
              <Button variant="ghost" size="sm" onClick={handleResetFilters} className="mt-3 text-xs">
                Clear Filters
              </Button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 border-b border-slate-200 uppercase font-semibold text-slate-500 tracking-wider">
                <tr>
                  <th className="py-3 px-4 w-16">Seq #</th>
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Entity</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4 text-center">Outcome</th>
                  <th className="py-3 px-4">Digest (SHA-256)</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {events.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50/70 transition-colors">
                    {/* Sequence */}
                    <td className="py-3 px-4">
                      {e.sequence_number !== null && e.sequence_number !== undefined ? (
                        <span className="font-bold text-sentinel-800 bg-sentinel-50 border border-sentinel-200 px-1.5 py-0.5 rounded text-[11px]">
                          #{e.sequence_number}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[10px] italic">Legacy</span>
                      )}
                    </td>

                    {/* Timestamp */}
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap text-[11px]">
                      {formatDate(e.created_at)}
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      <span className="text-sentinel-700 truncate block max-w-44" title={e.action}>
                        {e.action}
                      </span>
                    </td>

                    {/* Entity */}
                    <td className="py-3 px-4 text-slate-700">
                      <div className="flex items-center gap-1">
                        <span className="text-[10px] text-slate-400 uppercase">{e.entity_type}</span>
                        {e.entity_type === 'INSTRUMENT' && e.entity_id ? (
                          <Link
                            to={`/instruments/${e.entity_id}`}
                            className="text-sentinel-600 hover:text-sentinel-800 underline flex items-center gap-0.5"
                            title={`Inspect Instrument ${e.entity_id}`}
                          >
                            <span>{e.entity_id.slice(0, 8)}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        ) : (
                          <span className="text-slate-600 truncate max-w-28" title={e.entity_id}>
                            {e.entity_id.slice(0, 10)}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Actor */}
                    <td className="py-3 px-4 text-slate-600">
                      <div className="truncate max-w-36" title={e.actor_email || 'SYSTEM'}>
                        {e.actor_email || 'SYSTEM'}
                      </div>
                      {e.actor_role && (
                        <span className="text-[10px] text-slate-400 block font-sans">
                          {e.actor_role}
                        </span>
                      )}
                    </td>

                    {/* Outcome */}
                    <td className="py-3 px-4 text-center">
                      {getOutcomeBadge(e.outcome)}
                    </td>

                    {/* Hash Digest */}
                    <td className="py-3 px-4 text-[11px] text-slate-500">
                      {e.current_hash ? (
                        <button
                          onClick={() => handleCopy(e.current_hash!, `hash-${e.id}`)}
                          className="hover:text-sentinel-700 flex items-center gap-1 group text-left"
                          title="Click to copy full SHA-256 hash"
                        >
                          <span className="font-mono text-slate-600 group-hover:underline">
                            {e.current_hash.slice(0, 10)}...{e.current_hash.slice(-4)}
                          </span>
                          {copiedHash === `hash-${e.id}` ? (
                            <Check className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                          )}
                        </button>
                      ) : (
                        <span className="text-slate-400 text-[10px] italic">Unchained</span>
                      )}
                    </td>

                    {/* Inspect button */}
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedEvent(e)}
                        className="py-1 px-2 text-[11px] gap-1 text-slate-700 hover:text-slate-900"
                        title="View Full Cryptographic Event Payload"
                      >
                        <Eye className="w-3 h-3 text-slate-500" /> Inspect
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="bg-slate-50 px-4 py-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <div>
            Showing <span className="font-semibold">{events.length > 0 ? page * pageSize + 1 : 0}</span> to{' '}
            <span className="font-semibold">{Math.min((page + 1) * pageSize, totalCount)}</span> of{' '}
            <span className="font-semibold">{totalCount}</span> events
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0 || isLoading}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="p-1.5"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="font-mono font-medium px-2">Page {page + 1}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={(page + 1) * pageSize >= totalCount || isLoading}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Forensic Event Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-sentinel-700" />
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">
                    Audit Event Payload #{selectedEvent.sequence_number ?? 'Legacy'}
                  </h3>
                  <span className="text-[11px] text-slate-500 font-mono">
                    UUID: {selectedEvent.id}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 font-mono text-xs">
              {/* Cryptographic Linkage Card */}
              <div className="bg-slate-900 text-slate-100 p-4 rounded-xl space-y-2 border border-slate-800">
                <div className="flex items-center justify-between text-slate-400 text-[11px] uppercase tracking-wider font-sans font-semibold">
                  <span>Cryptographic Proof & SHA-256 Linkage</span>
                  <Lock className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Previous Hash Pointer (Parent):</span>
                  <div className="flex items-center justify-between gap-2 mt-0.5">
                    <span className="text-slate-300 text-[11px] truncate block">
                      {selectedEvent.previous_hash || '0000000000000000000000000000000000000000000000000000000000000000 (GENESIS)'}
                    </span>
                    {selectedEvent.previous_hash && (
                      <button
                        onClick={() => handleCopy(selectedEvent.previous_hash!, 'prev')}
                        className="text-slate-400 hover:text-white p-1"
                        title="Copy Previous Hash"
                      >
                        {copiedHash === 'prev' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Current Canonical Payload Hash (SHA-256):</span>
                  <div className="flex items-center justify-between gap-2 mt-0.5">
                    <span className="text-emerald-400 text-[11px] truncate block font-bold">
                      {selectedEvent.current_hash || 'Unchained (Legacy Migration)'}
                    </span>
                    {selectedEvent.current_hash && (
                      <button
                        onClick={() => handleCopy(selectedEvent.current_hash!, 'curr')}
                        className="text-slate-400 hover:text-white p-1"
                        title="Copy Current Hash"
                      >
                        {copiedHash === 'curr' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Event Attributes Grid */}
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span className="text-slate-500 text-[10px] block font-sans">Action Code:</span>
                  <span className="font-bold text-sentinel-800">{selectedEvent.action}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-sans">Execution Outcome:</span>
                  <div>{getOutcomeBadge(selectedEvent.outcome)}</div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-sans">Target Entity:</span>
                  <span className="text-slate-800">
                    {selectedEvent.entity_type} ({selectedEvent.entity_id})
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-sans">Actor Identity:</span>
                  <span className="text-slate-800">
                    {selectedEvent.actor_email || 'SYSTEM'} [{selectedEvent.actor_role || 'N/A'}]
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-sans">Recorded Timestamp (UTC):</span>
                  <span className="text-slate-700">{selectedEvent.created_at}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block font-sans">Policy Version:</span>
                  <span className="text-slate-700">{selectedEvent.policy_version || 'N/A'}</span>
                </div>
                {selectedEvent.request_id && (
                  <div className="col-span-2">
                    <span className="text-slate-500 text-[10px] block font-sans">Request Correlation ID:</span>
                    <span className="text-slate-700">{selectedEvent.request_id}</span>
                  </div>
                )}
              </div>

              {/* Recorded Metadata / State Transitions */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-700 font-semibold font-sans text-xs flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5 text-slate-500" /> Canonical Metadata & State Diffs:
                  </span>
                  {selectedEvent.metadata && (
                    <button
                      onClick={() => handleCopy(JSON.stringify(selectedEvent.metadata, null, 2), 'json')}
                      className="text-[11px] text-sentinel-600 hover:text-sentinel-800 flex items-center gap-1"
                    >
                      {copiedHash === 'json' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      Copy JSON
                    </button>
                  )}
                </div>
                <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg overflow-x-auto text-[11px] leading-relaxed max-h-56">
                  {selectedEvent.metadata && Object.keys(selectedEvent.metadata).length > 0
                    ? JSON.stringify(selectedEvent.metadata, null, 2)
                    : '// No additional payload metadata recorded for this entry.'}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              {selectedEvent.entity_type === 'INSTRUMENT' && selectedEvent.entity_id ? (
                <Link
                  to={`/instruments/${selectedEvent.entity_id}`}
                  className="text-xs text-sentinel-700 hover:text-sentinel-900 font-semibold flex items-center gap-1"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Navigate to Instrument Record
                </Link>
              ) : (
                <span className="text-xs text-slate-400">Append-only immutable record</span>
              )}
              <Button variant="secondary" size="sm" onClick={() => setSelectedEvent(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
