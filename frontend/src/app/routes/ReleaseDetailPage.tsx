import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  AlertCircle,
  Clock,
  CheckCircle,
  XCircle,
  ShieldAlert,
  Play,
  RotateCcw,
  CheckSquare,
  FileCheck2,
  FileText,
  Building,
  CheckCircle2,
} from 'lucide-react';
import { releaseApi, ReleaseRequestDetailResponse } from '@/api/release';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/components/common/Button';
import { cn } from '@/lib/utils';

const statusColors: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-[#253746]',
  SUBMITTED: 'bg-blue-100 text-blue-800',
  UNDER_REVIEW: 'bg-amber-100 text-amber-800',
  RETURNED_FOR_CORRECTION: 'bg-orange-100 text-orange-800',
  READY_FOR_AUTHORITY: 'bg-cyan-100 text-cyan-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  RELEASE_ORDER_RECORDED: 'bg-purple-100 text-purple-800',
  BANK_SIDE_ACTION_PENDING: 'bg-indigo-100 text-indigo-800',
  COMPLETED: 'bg-emerald-100 text-emerald-800',
  CLOSED: 'bg-slate-200 text-[#0D2538]',
};

export const ReleaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [details, setDetails] = useState<ReleaseRequestDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isActing, setIsActing] = useState(false);

  // Action dialog states
  const [activeModal, setActiveModal] = useState<
    'startReview' | 'evaluate' | 'recommend' | 'returnCorrection' | 'approve' | 'reject' | 'recordOrder' | 'confirmBank' | 'closeCase' | null
  >(null);
  const [modalReason, setModalReason] = useState('');
  const [orderRefNumber, setOrderRefNumber] = useState('');
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);

  const fetchDetails = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await releaseApi.getDetail(id);
      setDetails(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load case details';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const clearModal = () => {
    setActiveModal(null);
    setModalReason('');
    setOrderRefNumber('');
  };

  const handleAction = async (actionFn: () => Promise<any>, successMsg: string) => {
    if (!id) return;
    setIsActing(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      await actionFn();
      setActionSuccess(successMsg);
      clearModal();
      await fetchDetails();
    } catch (err: any) {
      setActionError(err?.message || 'Operation failed. Please check permissions and state.');
    } finally {
      setIsActing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Clock className="w-8 h-8 text-slate-400 mx-auto mb-3 animate-spin" />
          <p className="text-[#5D6A75]">Loading case details...</p>
        </div>
      </div>
    );
  }

  if (error || !details) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
        <div>
          <h3 className="font-semibold text-red-900">Error Loading Case</h3>
          <p className="text-red-700">{error || 'Case not found'}</p>
        </div>
      </div>
    );
  }

  const role = user?.role;
  const status = details.workflow_status;

  const isScrutinyOfficer = role === 'SCRUTINY_OFFICER' || role === 'BRANCH_HEAD';
  const isCompetentAuthority = role === 'COMPETENT_AUTHORITY';
  const isFinanceOfficer = role === 'FINANCE_OFFICER';
  const isBranchHead = role === 'BRANCH_HEAD';
  const isAuditor = role === 'AUDITOR';

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Notifications */}
      {actionSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-emerald-800 text-sm font-medium">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>{actionSuccess}</span>
          </div>
          <button type="button" onClick={() => setActionSuccess(null)} className="text-emerald-700 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {actionError && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-rose-800 text-sm font-medium">
            <AlertCircle className="w-5 h-5 text-rose-600" />
            <span>{actionError}</span>
          </div>
          <button type="button" onClick={() => setActionError(null)} className="text-rose-700 text-xs font-semibold">
            Dismiss
          </button>
        </div>
      )}

      {/* Auditor Read-Only Notice */}
      {isAuditor && (
        <div className="bg-[#EEF6FA] border border-[#C4DEED] rounded-lg p-3 flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 text-[#245B7A] shrink-0" />
          <p className="text-xs text-[#245B7A] font-medium">
            <strong>Auditor Mode (PRD-FR-095):</strong> You have read-only inspection access. All workflow state-mutation actions are disabled.
          </p>
        </div>
      )}

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-[#C9D3DB]">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0D2538] font-mono">{details.case_number}</h1>
              <span className={cn('text-xs font-bold font-mono px-3 py-1 rounded-[6px]', statusColors[details.workflow_status])}>
                {details.workflow_status.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-xs text-[#5D6A75] mt-1">
              Case opened on {new Date(details.created_at).toLocaleDateString()} &bull; Requesting Tenancy ID:{' '}
              <span className="font-mono">{details.institution_id}</span>
            </p>
          </div>

          {/* Action Center Trigger Bar */}
          {!isAuditor && (
            <div className="flex flex-wrap items-center gap-2">
              {/* Scrutiny Officer Actions */}
              {isScrutinyOfficer && status === 'SUBMITTED' && (
                <Button
                  size="sm"
                  className="bg-[#123B5D] hover:bg-[#0D2538] text-white"
                  onClick={() => handleAction(() => releaseApi.startReview(id!), 'Review started successfully.')}
                  disabled={isActing}
                >
                  <Play className="w-4 h-4 mr-1.5" /> Start Formal Review
                </Button>
              )}

              {isScrutinyOfficer && status === 'UNDER_REVIEW' && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-[#0F766E] text-[#0F766E] hover:bg-teal-50"
                    onClick={() => handleAction(() => releaseApi.evaluateReadiness(id!, true), 'Readiness gate evaluated.')}
                    disabled={isActing}
                  >
                    <FileCheck2 className="w-4 h-4 mr-1.5" /> Evaluate Readiness Gate
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-amber-400 text-amber-800 hover:bg-amber-50"
                    onClick={() => setActiveModal('returnCorrection')}
                    disabled={isActing}
                  >
                    <RotateCcw className="w-4 h-4 mr-1.5" /> Return for Correction
                  </Button>
                  <Button
                    size="sm"
                    className="bg-[#0F766E] hover:bg-[#09544E] text-white"
                    onClick={() => setActiveModal('recommend')}
                    disabled={isActing}
                  >
                    <CheckSquare className="w-4 h-4 mr-1.5" /> Recommend for Authority
                  </Button>
                </>
              )}

              {/* Competent Authority Actions */}
              {isCompetentAuthority && status === 'READY_FOR_AUTHORITY' && (
                <>
                  <Button
                    size="sm"
                    className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold"
                    onClick={() => setActiveModal('approve')}
                    disabled={isActing}
                  >
                    <CheckCircle className="w-4 h-4 mr-1.5" /> Sanction & Approve Release
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-rose-400 text-rose-700 hover:bg-rose-50"
                    onClick={() => setActiveModal('reject')}
                    disabled={isActing}
                  >
                    <XCircle className="w-4 h-4 mr-1.5" /> Reject Release Petition
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-amber-400 text-amber-800 hover:bg-amber-50"
                    onClick={() => setActiveModal('returnCorrection')}
                    disabled={isActing}
                  >
                    <RotateCcw className="w-4 h-4 mr-1.5" /> Return for Correction
                  </Button>
                </>
              )}

              {/* Finance Officer Actions */}
              {isFinanceOfficer && status === 'APPROVED' && (
                <Button
                  size="sm"
                  className="bg-purple-700 hover:bg-purple-800 text-white"
                  onClick={() => setActiveModal('recordOrder')}
                  disabled={isActing}
                >
                  <FileText className="w-4 h-4 mr-1.5" /> Record Official Release Order
                </Button>
              )}

              {(isFinanceOfficer || isBranchHead) && (status === 'RELEASE_ORDER_RECORDED' || status === 'BANK_SIDE_ACTION_PENDING') && (
                <>
                  <Button
                    size="sm"
                    className="bg-indigo-700 hover:bg-indigo-800 text-white"
                    onClick={() => setActiveModal('confirmBank')}
                    disabled={isActing}
                  >
                    <Building className="w-4 h-4 mr-1.5" /> Confirm Bank Action Execution
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-slate-500 text-slate-800 hover:bg-slate-100"
                    onClick={() => setActiveModal('closeCase')}
                    disabled={isActing}
                  >
                    <CheckCircle2 className="w-4 h-4 mr-1.5" /> Close Release Case
                  </Button>
                </>
              )}
            </div>
          )}
        </div>

        {details.policy_profile?.is_demo && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex gap-2 mb-4">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <p className="text-xs text-amber-800">
              <strong>Demo Policy:</strong> {details.policy_profile.demo_disclaimer}
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-3 border-t border-slate-100">
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Request Type</p>
            <p className="text-[#0D2538] font-medium">{details.request_type}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Case Type</p>
            <p className="text-[#0D2538] font-medium">{details.case_type.replace(/_/g, ' ')}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Target FDR ID</p>
            <p className="text-[#0D2538] font-medium font-mono text-xs">{details.instrument_id}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Policy Profile</p>
            <p className="text-[#0D2538] font-medium text-xs">
              {details.policy_profile?.name || `Version ${details.policy_version || '1'}`}
            </p>
          </div>
        </div>
      </div>

      {/* Action Dialog Modal */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-lg font-bold text-[#0D2538]">
              {activeModal === 'recommend' && 'Recommend Case for Competent Authority Sanction'}
              {activeModal === 'returnCorrection' && 'Return Case for Institutional Correction'}
              {activeModal === 'approve' && 'Statutory Release Approval (Competent Authority)'}
              {activeModal === 'reject' && 'Reject Release Petition (Competent Authority)'}
              {activeModal === 'recordOrder' && 'Record Official Release Letter / Order'}
              {activeModal === 'confirmBank' && 'Confirm Bank-Side Execution of Release Order'}
              {activeModal === 'closeCase' && 'Finalize Case Closure'}
            </h3>

            {activeModal === 'recordOrder' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-[#5D6A75] uppercase mb-1">
                    Release Order Reference Number *
                  </label>
                  <input
                    type="text"
                    value={orderRefNumber}
                    onChange={(e) => setOrderRefNumber(e.target.value)}
                    placeholder="e.g. AICTE/FIN/2026/REL-9482"
                    className="w-full px-3 py-2 border rounded-md text-sm font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#5D6A75] uppercase mb-1">
                    Order Date *
                  </label>
                  <input
                    type="date"
                    value={orderDate}
                    onChange={(e) => setOrderDate(e.target.value)}
                    className="w-full px-3 py-2 border rounded-md text-sm font-mono"
                    required
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-[#5D6A75] uppercase mb-1">
                {activeModal === 'approve'
                  ? 'Mandatory Regulatory Approval Justification *'
                  : activeModal === 'reject'
                  ? 'Rejection Rationale *'
                  : activeModal === 'returnCorrection'
                  ? 'Deficiency Explanation & Correction Instructions *'
                  : 'Operational Remarks & Justification *'}
              </label>
              <textarea
                value={modalReason}
                onChange={(e) => setModalReason(e.target.value)}
                placeholder="Enter justification..."
                className="w-full h-24 p-2.5 border rounded-md text-sm"
                required
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="outline" onClick={clearModal} disabled={isActing}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-[#123B5D] text-white"
                disabled={isActing || (activeModal === 'recordOrder' && !orderRefNumber.trim()) || !modalReason.trim()}
                onClick={() => {
                  if (activeModal === 'recommend') {
                    handleAction(() => releaseApi.recommendForAuthority(id!, modalReason), 'Case recommended for authority.');
                  } else if (activeModal === 'returnCorrection') {
                    handleAction(() => releaseApi.returnForCorrection(id!, modalReason), 'Case returned for correction.');
                  } else if (activeModal === 'approve') {
                    handleAction(() => releaseApi.approve(id!, modalReason), 'Case approved by Competent Authority.');
                  } else if (activeModal === 'reject') {
                    handleAction(() => releaseApi.reject(id!, modalReason), 'Case rejected by Competent Authority.');
                  } else if (activeModal === 'recordOrder') {
                    handleAction(
                      () =>
                        releaseApi.recordOrder(id!, {
                          order_reference_number: orderRefNumber,
                          order_date: orderDate,
                          notes: modalReason,
                        }),
                      'Official release order recorded.'
                    );
                  } else if (activeModal === 'confirmBank') {
                    handleAction(() => releaseApi.confirmBankAction(id!, modalReason), 'Bank execution confirmed.');
                  } else if (activeModal === 'closeCase') {
                    handleAction(() => releaseApi.closeCase(id!, modalReason), 'Release case closed.');
                  }
                }}
              >
                {isActing ? 'Executing...' : 'Confirm Action'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Request Details */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-[#C9D3DB]">
        <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider mb-2">Institutional Petition Justification</h2>
        <div className="bg-[#F5F4EF] rounded-md p-4 border border-[#C9D3DB]">
          <p className="text-xs text-[#253746] whitespace-pre-wrap leading-relaxed">{details.request_reason}</p>
        </div>
      </div>

      {/* Readiness Summary */}
      {details.assessments && details.assessments.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm p-6 border border-[#C9D3DB]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">Release Readiness Gate Assessment</h2>
            <span className="text-xs text-[#5D6A75] font-mono">Stage 7 Compliance Gate</span>
          </div>
          {(() => {
            const latestAssessment = details.assessments[0];
            const hasBlockers = latestAssessment.blockers_count > 0;
            return (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <p className="text-xs font-semibold text-[#5D6A75] uppercase">Total Rules</p>
                    <p className="text-2xl font-bold text-[#0D2538] font-mono">{latestAssessment.total_items_count}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
                    <p className="text-xs font-semibold text-emerald-800 uppercase">Satisfied</p>
                    <p className="text-2xl font-bold text-emerald-700 font-mono">{latestAssessment.satisfied_count}</p>
                  </div>
                  <div className={cn('p-3 rounded-lg border', hasBlockers ? 'bg-rose-50 border-rose-200' : 'bg-slate-50 border-slate-200')}>
                    <p className={cn('text-xs font-semibold uppercase', hasBlockers ? 'text-rose-800' : 'text-[#5D6A75]')}>
                      Blockers
                    </p>
                    <p className={cn('text-2xl font-bold font-mono', hasBlockers ? 'text-rose-700' : 'text-[#5D6A75]')}>
                      {latestAssessment.blockers_count}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                    <p className="text-xs font-semibold text-amber-800 uppercase">Pending Review</p>
                    <p className="text-2xl font-bold text-amber-700 font-mono">{latestAssessment.pending_count}</p>
                  </div>
                </div>

                <div
                  className={cn(
                    'rounded-lg p-4 border',
                    latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL'
                      ? 'bg-emerald-50 border-emerald-200'
                      : 'bg-amber-50 border-amber-200'
                  )}
                >
                  <div className="flex gap-2">
                    {latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? (
                      <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    )}
                    <div>
                      <p
                        className={cn(
                          'font-bold text-sm',
                          latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? 'text-emerald-900' : 'text-amber-900'
                        )}
                      >
                        {latestAssessment.assessment_outcome.replace(/_/g, ' ')}
                      </p>
                      {latestAssessment.summary_notes && (
                        <p
                          className={cn(
                            'text-xs mt-1',
                            latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? 'text-emerald-800' : 'text-amber-800'
                          )}
                        >
                          {latestAssessment.summary_notes}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {latestAssessment.results.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-xs text-[#0D2538] uppercase tracking-wider mb-2">Checklist Verification Rules</h3>
                    <div className="space-y-2">
                      {latestAssessment.results.map((item) => (
                        <div key={item.id} className="border border-[#C9D3DB] rounded-lg p-3 flex gap-3 bg-white">
                          <div className="flex-shrink-0 pt-0.5">
                            {item.status === 'SATISFIED' ? (
                              <CheckCircle className="w-4 h-4 text-emerald-600" />
                            ) : item.is_mandatory_blocker ? (
                              <XCircle className="w-4 h-4 text-rose-600" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-amber-600" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="font-bold text-xs text-[#0D2538] font-mono">{item.item_code}</p>
                                <p className="text-xs text-[#5D6A75] mt-0.5">{item.explanation}</p>
                              </div>
                              {item.is_mandatory_blocker && (
                                <span className="text-[10px] font-bold uppercase bg-rose-100 text-rose-800 px-2 py-0.5 rounded font-mono">
                                  Mandatory Blocker
                                </span>
                              )}
                            </div>
                            <p className="text-[10px] text-[#8799A9] mt-1 font-mono">
                              Status: <span className="font-semibold text-[#253746]">{item.status}</span> &bull; Source:{' '}
                              {item.source_module}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* Decisions History */}
      {details.decisions && details.decisions.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm p-6 border border-[#C9D3DB]">
          <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider mb-4">Immutable Decision Audit Log</h2>
          <div className="space-y-3">
            {details.decisions.map((decision) => (
              <div key={decision.id} className="border border-[#C9D3DB] rounded-lg p-3.5 bg-[#F5F4EF]/50">
                <div className="flex items-start justify-between mb-1.5">
                  <div>
                    <span className="font-bold text-xs text-[#0D2538] font-mono mr-2">
                      {decision.decision_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[11px] text-[#5D6A75] font-mono">
                      by <strong className="text-[#123B5D]">{decision.actor_role}</strong> ({decision.actor_user_id})
                    </span>
                  </div>
                  <span className="text-[10px] text-[#8799A9] font-mono">
                    {new Date(decision.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-[#253746] bg-white p-2 rounded border border-slate-200 mt-1">{decision.reason}</p>
                <div className="flex items-center gap-2 text-[10px] text-[#5D6A75] font-mono mt-2">
                  <span>{decision.previous_status}</span>
                  <span>&rarr;</span>
                  <span className="font-bold text-[#0D2538]">{decision.new_status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
