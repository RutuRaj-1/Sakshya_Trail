import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertCircle, Clock, CheckCircle, XCircle } from 'lucide-react';
import { releaseApi, ReleaseRequestDetailResponse } from '@/api/release';
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
  const [details, setDetails] = useState<ReleaseRequestDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDetails = async () => {
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
    };

    fetchDetails();
  }, [id]);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-[#0D2538]">{details.case_number}</h1>
            <p className="text-[#5D6A75] mt-1">Created on {new Date(details.created_at).toLocaleDateString()}</p>
          </div>
          <span className={cn('text-sm font-semibold px-4 py-2 rounded-lg', statusColors[details.workflow_status])}>
            {details.workflow_status.replace(/_/g, ' ')}
          </span>
        </div>

        {details.policy_profile?.is_demo && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex gap-2 mb-4">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <p className="text-sm text-amber-800">
              <strong>Demo Policy:</strong> {details.policy_profile.demo_disclaimer}
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Request Type</p>
            <p className="text-[#0D2538] font-medium">{details.request_type}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Case Type</p>
            <p className="text-[#0D2538] font-medium">{details.case_type.replace(/_/g, ' ')}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Instrument</p>
            <p className="text-[#0D2538] font-medium font-mono text-sm">{details.instrument_id}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#5D6A75] uppercase">Policy Version</p>
            <p className="text-[#0D2538] font-medium">{details.policy_version || 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Request Details */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-bold text-[#0D2538] mb-4">Request Details</h2>
        <div className="prose prose-sm max-w-none">
          <p className="text-[#253746] whitespace-pre-wrap">{details.request_reason}</p>
        </div>
      </div>

      {/* Readiness Summary */}
      {details.assessments && details.assessments.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-bold text-[#0D2538] mb-4">Readiness Assessment</h2>
          {(() => {
            const latestAssessment = details.assessments[0];
            const hasBlockers = latestAssessment.blockers_count > 0;
            return (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-[#5D6A75] uppercase">Total Items</p>
                    <p className="text-2xl font-bold text-[#0D2538]">{latestAssessment.total_items_count}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[#5D6A75] uppercase">Satisfied</p>
                    <p className="text-2xl font-bold text-green-600">{latestAssessment.satisfied_count}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[#5D6A75] uppercase">Blockers</p>
                    <p className={cn('text-2xl font-bold', hasBlockers ? 'text-red-600' : 'text-[#5D6A75]')}>
                      {latestAssessment.blockers_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[#5D6A75] uppercase">Pending</p>
                    <p className="text-2xl font-bold text-amber-600">{latestAssessment.pending_count}</p>
                  </div>
                </div>

                <div className={cn(
                  'rounded-lg p-4',
                  latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'
                )}>
                  <div className="flex gap-2">
                    {latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    )}
                    <div>
                      <p className={cn(
                        'font-semibold',
                        latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? 'text-green-900' : 'text-amber-900'
                      )}>
                        {latestAssessment.assessment_outcome.replace(/_/g, ' ')}
                      </p>
                      {latestAssessment.summary_notes && (
                        <p className={cn(
                          'text-sm mt-1',
                          latestAssessment.assessment_outcome === 'READY_FOR_APPROVAL' ? 'text-green-800' : 'text-amber-800'
                        )}>
                          {latestAssessment.summary_notes}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {latestAssessment.results.length > 0 && (
                  <div>
                    <h3 className="font-semibold text-[#0D2538] mb-3">Checklist Items</h3>
                    <div className="space-y-2">
                      {latestAssessment.results.map((item) => (
                        <div key={item.id} className="border border-[#C9D3DB] rounded-lg p-3 flex gap-3">
                          <div className="flex-shrink-0 pt-0.5">
                            {item.status === 'SATISFIED' ? (
                              <CheckCircle className="w-5 h-5 text-green-600" />
                            ) : item.is_mandatory_blocker ? (
                              <XCircle className="w-5 h-5 text-red-600" />
                            ) : (
                              <AlertCircle className="w-5 h-5 text-amber-600" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="font-medium text-[#0D2538]">{item.item_code}</p>
                                <p className="text-sm text-[#5D6A75]">{item.explanation}</p>
                              </div>
                              {item.is_mandatory_blocker && (
                                <span className="text-xs font-semibold bg-red-100 text-red-800 px-2 py-1 rounded-full flex-shrink-0">
                                  Blocker
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-[#5D6A75] mt-2">
                              Status: <span className="font-semibold">{item.status}</span> | Source: {item.source_module}
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
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-bold text-[#0D2538] mb-4">Decision History</h2>
          <div className="space-y-4">
            {details.decisions.map((decision) => (
              <div key={decision.id} className="border border-[#C9D3DB] rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="font-semibold text-[#0D2538]">{decision.decision_type.replace(/_/g, ' ')}</p>
                    <p className="text-sm text-[#5D6A75]">by {decision.actor_role}</p>
                  </div>
                  <span className="text-xs text-[#5D6A75]">
                    {new Date(decision.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm text-[#253746] mb-2">{decision.reason}</p>
                <div className="flex gap-2 text-xs text-[#5D6A75]">
                  <span>{decision.previous_status}</span>
                  <span>→</span>
                  <span>{decision.new_status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
