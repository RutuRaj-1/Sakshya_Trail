import React, { useState, useEffect, useCallback } from 'react';
import { lifecycleApi } from '@/api/endpoints';
import type {
  LifecycleNotification,
  LifecycleEvaluation,
  NotificationDeliveryStatus,
} from '@/types/lifecycle';
import {
  Bell,
  Mail,
  Smartphone,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Send,
  Clock,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  Info,
} from 'lucide-react';

interface Props {
  instrumentId: string;
  isOfficerOrAdmin?: boolean;
}

export const LifecycleNotificationHistory: React.FC<Props> = ({
  instrumentId,
  isOfficerOrAdmin = false,
}) => {
  const [notifications, setNotifications] = useState<LifecycleNotification[]>([]);
  const [evaluation, setEvaluation] = useState<LifecycleEvaluation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDispatching, setIsDispatching] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [notifRes, evalRes] = await Promise.allSettled([
        lifecycleApi.listNotifications(instrumentId),
        lifecycleApi.getEvaluation(instrumentId),
      ]);

      if (notifRes.status === 'fulfilled') {
        setNotifications(notifRes.value.notifications || []);
      }
      if (evalRes.status === 'fulfilled') {
        setEvaluation(evalRes.value);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to fetch lifecycle notifications.');
    } finally {
      setIsLoading(false);
    }
  }, [instrumentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRetry = async (notificationId: string) => {
    setRetryingId(notificationId);
    setActionSuccessMsg(null);
    setErrorMsg(null);
    try {
      await lifecycleApi.retryNotification(
        notificationId,
        'Manual retry initiated from administrative console'
      );
      setActionSuccessMsg('Delivery retry dispatched successfully.');
      await loadData();
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.message || err?.message || 'Failed to retry notification delivery.'
      );
    } finally {
      setRetryingId(null);
    }
  };

  const handleDispatchDue = async () => {
    setIsDispatching(true);
    setActionSuccessMsg(null);
    setErrorMsg(null);
    try {
      const res = await lifecycleApi.dispatchDueReminders(instrumentId);
      setActionSuccessMsg(res.message || 'Due reminder dispatch evaluated.');
      await loadData();
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.message || err?.message || 'Failed to dispatch due reminders.'
      );
    } finally {
      setIsDispatching(false);
    }
  };

  const renderChannelIcon = (channel: string) => {
    switch (channel) {
      case 'IN_APP':
        return <Bell className="w-3.5 h-3.5 text-blue-600" />;
      case 'EMAIL':
        return <Mail className="w-3.5 h-3.5 text-indigo-600" />;
      case 'MOCK_SMS':
        return <Smartphone className="w-3.5 h-3.5 text-amber-600" />;
      default:
        return <Send className="w-3.5 h-3.5 text-[#5D6A75]" />;
    }
  };

  const renderStatusBadge = (status: NotificationDeliveryStatus | string, isMock: boolean) => {
    if (isMock || status === 'MOCKED') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200">
          <Info className="w-3 h-3 text-amber-600" />
          <span>MOCKED</span>
        </span>
      );
    }

    switch (status) {
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>CONFIRMED DELIVERED</span>
          </span>
        );
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-200">
            <CheckCircle2 className="w-3 h-3 text-blue-600" />
            <span>PROVIDER ACCEPTED</span>
          </span>
        );
      case 'ATTEMPTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-mono font-bold bg-sky-50 text-sky-800 border border-sky-200">
            <Clock className="w-3 h-3 text-sky-600" />
            <span>ATTEMPTED</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-mono font-bold bg-rose-50 text-rose-800 border border-rose-200">
            <AlertTriangle className="w-3 h-3 text-rose-600" />
            <span>DELIVERY FAILED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-none text-[10px] font-mono font-bold bg-slate-100 text-[#253746] border border-[#C9D3DB]">
            <Clock className="w-3 h-3 text-[#5D6A75]" />
            <span>{status}</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-none border border-[#C9D3DB] p-6 space-y-5 shadow-xs">
      {/* Header with Title and Dispatch Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-none bg-[#EEF6FA] border border-sentinel-100 flex items-center justify-center text-[#123B5D]">
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-[#0D2538] text-sm">
                Policy-Driven Reminders & Escalation Delivery
              </h3>
              <span className="font-mono text-[9px] uppercase bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-none font-bold border border-emerald-200">
                Module 5 Active
              </span>
            </div>
            <p className="text-[#5D6A75] text-xs mt-0.5">
              Audited multi-channel reminder timeline with honest delivery receipts and bounded retry recovery.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isOfficerOrAdmin && (
            <button
              onClick={handleDispatchDue}
              disabled={isDispatching}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-none bg-[#123B5D] hover:bg-[#0D2538] text-white font-semibold text-xs shadow-2xs transition-colors disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isDispatching ? 'animate-spin' : ''}`} />
              <span>{isDispatching ? 'Evaluating...' : 'Dispatch Due Reminders'}</span>
            </button>
          )}
          <button
            onClick={loadData}
            disabled={isLoading}
            className="p-1.5 rounded-none border border-[#C9D3DB] hover:bg-[#F5F4EF] text-[#5D6A75] transition-colors"
            title="Refresh Notification History"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Messages */}
      {actionSuccessMsg && (
        <div className="p-3 rounded-none bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 rounded-none bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Lifecycle Health Bar */}
      {evaluation && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-none bg-[#F5F4EF] border border-[#C9D3DB]/80 text-xs font-mono">
          <div>
            <span className="text-[10px] uppercase text-slate-400 font-sans block">Maturity Window</span>
            <span className="font-bold text-[#0D2538]">{evaluation.maturity_stage}</span>
            <span className="text-[10px] text-[#5D6A75] font-sans block mt-0.5">
              {evaluation.days_to_maturity > 0
                ? `${evaluation.days_to_maturity} days remaining`
                : `${Math.abs(evaluation.days_to_maturity)} days post-maturity`}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase text-slate-400 font-sans block">Statutory Validity</span>
            <span
              className={`font-bold ${
                evaluation.validity_status === 'VALID' ? 'text-emerald-700' : 'text-amber-700'
              }`}
            >
              {evaluation.validity_status}
            </span>
            <span className="text-[10px] text-[#5D6A75] font-sans block mt-0.5">
              Policy v{evaluation.applied_policy_version}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase text-slate-400 font-sans block">Action Due Date</span>
            <span className="font-medium text-[#253746]">
              {evaluation.institution_action_due_date || 'N/A'}
            </span>
            <span className="text-[10px] text-[#5D6A75] font-sans block mt-0.5">
              Officer: {evaluation.officer_action_due_date || 'N/A'}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase text-slate-400 font-sans block">Overdue & Escalation</span>
            <span
              className={`font-bold ${
                evaluation.is_escalated
                  ? 'text-rose-700'
                  : evaluation.is_overdue
                  ? 'text-amber-700'
                  : 'text-[#5D6A75]'
              }`}
            >
              {evaluation.is_escalated ? 'ESCALATED' : evaluation.is_overdue ? 'OVERDUE' : 'NOMINAL'}
            </span>
            {evaluation.is_overdue && (
              <span className="text-[10px] text-rose-600 font-sans block mt-0.5">
                {evaluation.overdue_days} days past deadline
              </span>
            )}
          </div>
        </div>
      )}

      {/* Notification Timeline List */}
      <div className="space-y-3">
        {isLoading && notifications.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            <div className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-[#C9D3DB] border-t-sentinel-600 mb-2" />
            <p>Loading reminder history...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="py-8 text-center border-2 border-dashed border-[#C9D3DB] rounded-none bg-[#F5F4EF]/50">
            <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-semibold text-[#253746]">No Reminders Dispatched Yet</p>
            <p className="text-[11px] text-[#5D6A75] max-w-sm mx-auto mt-0.5">
              Notifications are triggered automatically by the daily scheduler when policy milestones
              (e.g. 30, 15 days to maturity) or overdue thresholds are reached.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {notifications.map((notif) => {
              const isExpanded = expandedId === notif.id;
              const hasFailed = notif.status === 'FAILED';
              const canRetry = hasFailed && isOfficerOrAdmin && notif.retry_count < notif.max_retries;

              return (
                <div
                  key={notif.id}
                  className={`rounded-none border transition-all ${
                    hasFailed
                      ? 'border-rose-200 bg-rose-50/20'
                      : notif.is_mock
                      ? 'border-amber-200/80 bg-amber-50/15'
                      : 'border-[#C9D3DB] bg-white hover:border-[#8799A9]'
                  }`}
                >
                  <div className="p-4 space-y-2.5">
                    {/* Top Row: Event, Channel, Status */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-none bg-slate-900 text-white">
                          {notif.event_type.replace(/_/g, ' ')}
                        </span>
                        {notif.milestone_days !== null && notif.milestone_days !== undefined && (
                          <span className="font-mono text-[10px] font-semibold px-2 py-0.5 rounded-none bg-blue-50 text-blue-700 border border-blue-200">
                            T-{notif.milestone_days} Days
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1 font-mono text-[10px] font-semibold px-2 py-0.5 rounded-none bg-slate-100 text-[#253746] border border-[#C9D3DB]">
                          {renderChannelIcon(notif.channel)}
                          <span>{notif.channel}</span>
                        </span>
                        <span className="font-mono text-[10px] text-[#5D6A75]">
                          To: <strong className="text-[#253746]">{notif.recipient_role}</strong>
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {renderStatusBadge(notif.status, notif.is_mock)}
                        {canRetry && (
                          <button
                            onClick={() => handleRetry(notif.id)}
                            disabled={retryingId === notif.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-none bg-rose-600 hover:bg-rose-700 text-white text-[10px] font-bold transition-colors disabled:opacity-50"
                          >
                            <RotateCw
                              className={`w-3 h-3 ${retryingId === notif.id ? 'animate-spin' : ''}`}
                            />
                            <span>Retry</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Notification Title & Body */}
                    <div>
                      <h4 className="text-xs font-bold text-[#0D2538]">{notif.rendered_title}</h4>
                      <p className="text-[11px] text-[#5D6A75] mt-0.5 line-clamp-2">
                        {notif.rendered_message}
                      </p>
                    </div>

                    {/* Mock Disclaimer Notice */}
                    {notif.is_mock && notif.mock_disclaimer && (
                      <div className="p-2 rounded-none bg-amber-50 border border-amber-200 text-amber-900 text-[10px] flex items-center gap-1.5 font-mono">
                        <Info className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                        <span>{notif.mock_disclaimer}</span>
                      </div>
                    )}

                    {/* Failure Explanation */}
                    {hasFailed && notif.failure_details && (
                      <div className="p-2.5 rounded-none bg-rose-50 border border-rose-200 text-rose-900 text-[11px] flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold block">
                            Failure Category: {notif.failure_category || 'DELIVERY_EXCEPTION'}
                          </span>
                          <span className="text-[10px] text-rose-800 font-mono">
                            {notif.failure_details}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Footer Row: Timestamps, Retries, Attempts Expander */}
                    <div className="flex flex-wrap items-center justify-between text-[10px] text-[#5D6A75] pt-2 border-t border-slate-100 font-mono">
                      <div className="flex items-center gap-3">
                        <span>Created: {new Date(notif.created_at).toLocaleString()}</span>
                        <span>
                          Attempts: {notif.retry_count}/{notif.max_retries}
                        </span>
                        {notif.final_delivered_at && (
                          <span className="text-emerald-700 font-semibold">
                            Delivered: {new Date(notif.final_delivered_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>

                      {notif.attempts && notif.attempts.length > 0 && (
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : notif.id)}
                          className="inline-flex items-center gap-1 text-[#253746] hover:text-[#0D2538] font-medium transition-colors"
                        >
                          <span>{notif.attempts.length} Attempt Log(s)</span>
                          {isExpanded ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronRight className="w-3 h-3" />
                          )}
                        </button>
                      )}
                    </div>

                    {/* Expanded Attempt History */}
                    {isExpanded && notif.attempts && notif.attempts.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-100 space-y-1.5">
                        <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">
                          Audited Provider Dispatch Attempts
                        </span>
                        {notif.attempts.map((att) => (
                          <div
                            key={att.id}
                            className="p-2 rounded-none bg-[#F5F4EF] border border-[#C9D3DB] text-[10px] font-mono flex flex-wrap items-center justify-between gap-2"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-[#253746]">
                                #{att.attempt_number}
                              </span>
                              <span>{new Date(att.attempted_at).toLocaleTimeString()}</span>
                              <span className="text-[#5D6A75]">
                                Provider: {att.provider_name || 'System Provider'}
                              </span>
                              {att.provider_reference && (
                                <span className="text-slate-400 truncate max-w-xs">
                                  Ref: {att.provider_reference}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {renderStatusBadge(att.status, att.is_mock)}
                              {att.failure_category && (
                                <span className="text-rose-600 font-semibold">
                                  [{att.failure_category}]
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
