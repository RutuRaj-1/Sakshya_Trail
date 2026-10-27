import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Search,
  ExternalLink,
  Layers,
  Calendar,
  GitBranch,
  AlertOctagon,
  SlidersHorizontal,
  Send,
  FileSpreadsheet,
  ArrowRight,
  ShieldAlert,
  ChevronRight,
  Info,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { instrumentsApi, lifecycleApi } from '@/api/endpoints';
import { commandCenterApi } from '@/api/commandCenter';
import type { Instrument } from '@/types';
import type { StatusCountsResponse, MaturityWindowRecordItem } from '@/types/commandCenter';
import type { LifecycleNotification } from '@/types/lifecycle';
import { useAuth } from '@/features/auth/AuthContext';
import { Badge } from '@/components/common/Badge';
import { formatINR, formatDate } from '@/lib/utils';
import { RenewalLineageSection } from '@/features/lifecycle/RenewalLineageSection';
import { LifecycleNotificationHistory } from '@/features/lifecycle/LifecycleNotificationHistory';

export type MonitoringTab =
  | 'overview'
  | 'calendar'
  | 'maturities'
  | 'renewals'
  | 'lineage'
  | 'exceptions'
  | 'scheduler';

export const MonitoringRenewalsPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const isOfficerOrAdmin = [
    'SYSTEM_ADMIN',
    'SCRUTINY_OFFICER',
    'BRANCH_HEAD',
    'COMPETENT_AUTHORITY',
  ].includes(user?.role || '');
  const canAccessScheduler = ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER'].includes(user?.role || '');

  // Tab State
  const rawTab = searchParams.get('tab') as MonitoringTab;
  const currentTab: MonitoringTab = [
    'overview',
    'calendar',
    'maturities',
    'renewals',
    'lineage',
    'exceptions',
    'scheduler',
  ].includes(rawTab)
    ? rawTab
    : 'overview';

  const initialWindowDays = Number(searchParams.get('window_days')) || 90;
  const [windowDays, setWindowDays] = useState<number>(initialWindowDays);
  const [searchQuery, setSearchQuery] = useState('');

  // Data states
  const [statusCounts, setStatusCounts] = useState<StatusCountsResponse | null>(null);
  const [maturingItems, setMaturingItems] = useState<MaturityWindowRecordItem[]>([]);
  const [selectedInstrument, setSelectedInstrument] = useState<Instrument | null>(null);
  const [failedNotifications, setFailedNotifications] = useState<LifecycleNotification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState<string | null>(null);
  const [schedulerActionMessage, setSchedulerActionMessage] = useState<string | null>(null);
  const [isDispatching, setIsDispatching] = useState(false);

  const setTab = (tab: MonitoringTab) => {
    const next = new URLSearchParams(searchParams);
    if (tab === 'overview') {
      next.delete('tab');
    } else {
      next.set('tab', tab);
    }
    setSearchParams(next, { replace: true });
  };

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [countsRes, windowRes] = await Promise.all([
        commandCenterApi.getStatusCounts({ window_days: windowDays }),
        commandCenterApi.getMaturityWindow({ window_days: windowDays, page_size: 50 }),
      ]);
      setStatusCounts(countsRes);
      setMaturingItems(windowRes.records);

      if (!selectedInstrument && windowRes.records.length > 0) {
        const inst = await instrumentsApi.get(windowRes.records[0].id);
        setSelectedInstrument(inst);
      }

      // Load failed notifications if exceptions or scheduler tab is selected
      if (['exceptions', 'scheduler'].includes(currentTab)) {
        try {
          const res = await lifecycleApi.listFailedNotifications(1, 50);
          setFailedNotifications(res.items || res.notifications || []);
        } catch {
          setFailedNotifications([]);
        }
      }
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [windowDays, selectedInstrument, currentTab]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectMaturityItem = async (instrumentId: string) => {
    try {
      const inst = await instrumentsApi.get(instrumentId);
      setSelectedInstrument(inst);
    } catch (err) {
      console.error('Failed to retrieve instrument details:', err);
    }
  };

  const handleTriggerEvaluation = async () => {
    if (!selectedInstrument) return;
    setIsEvaluating(true);
    setEvalMessage(null);
    try {
      const res = await lifecycleApi.evaluateInstrument(selectedInstrument.id, true);
      setEvalMessage(
        `Evaluation recorded: Stage ${res.maturity_stage}, Status: ${res.validity_status}`
      );
      const updatedInst = await instrumentsApi.get(selectedInstrument.id);
      setSelectedInstrument(updatedInst);
      loadData();
    } catch (err: any) {
      setEvalMessage(err?.response?.data?.message || err?.message || 'Failed to trigger evaluation.');
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleDispatchDue = async () => {
    setIsDispatching(true);
    setSchedulerActionMessage(null);
    try {
      const res = await lifecycleApi.dispatchDueReminders();
      setSchedulerActionMessage(
        `Dispatched ${res.dispatched_count} statutory notification reminder(s).`
      );
      loadData();
    } catch (err: any) {
      setSchedulerActionMessage(
        err?.response?.data?.message || err?.message || 'Failed to dispatch due reminders.'
      );
    } finally {
      setIsDispatching(false);
    }
  };

  const handleRetryFailedNotification = async (notifId: string) => {
    try {
      await lifecycleApi.retryNotification(notifId, 'Admin manual retry');
      setSchedulerActionMessage('Notification retry scheduled.');
      loadData();
    } catch (err: any) {
      setSchedulerActionMessage(
        err?.response?.data?.message || err?.message || 'Retry failed.'
      );
    }
  };

  const filteredItems = maturingItems.filter(
    (item) =>
      !searchQuery ||
      item.reference_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.bank_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans text-xs pb-12">
      {/* Top Banner */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 text-white shadow-[0_1px_3px_rgba(13,37,56,0.08)] border border-[#1e3c54] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2.5 py-0.5 rounded-[4px] uppercase tracking-wider font-mono">
              Experience B: Lifecycle &amp; Monitoring
            </span>
            <span className="text-[#8799A9] text-xs font-mono">Portfolio Surveillance &amp; Lineage</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            Lifecycle &amp; Monitoring Surveillance
          </h1>
          <p className="text-xs text-[#C9D3DB] leading-relaxed">
            Portfolio-wide maturity surveillance, statutory multi-tier reminder intervals (30/60/90 days), and unbroken predecessor-successor lineage governance.
          </p>
        </div>

        {/* Window Selector */}
        <div className="flex items-center gap-2 bg-[#123B5D] p-1.5 rounded-[8px] border border-[#8799A9]/50 shrink-0">
          <span className="text-[11px] text-[#C9D3DB] px-2 font-medium">Surveillance Window:</span>
          {[30, 60, 90, 180, 365].map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => {
                setWindowDays(days);
                const next = new URLSearchParams(searchParams);
                next.set('window_days', String(days));
                setSearchParams(next, { replace: true });
              }}
              className={`px-2.5 py-1 rounded-[6px] text-xs font-mono font-semibold transition cursor-pointer ${
                windowDays === days
                  ? 'bg-[#0F766E] text-white shadow-2xs'
                  : 'text-[#C9D3DB] hover:text-white hover:bg-white/10'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-[10px] border border-[#C9D3DB] shadow-2xs">
          <span className="text-[#5D6A75] text-[11px] uppercase font-semibold">Active In-Term Deposits</span>
          <div className="text-2xl font-bold font-mono text-[#0D2538] mt-1">
            {isLoading ? '...' : statusCounts?.active_count ?? 0}
          </div>
          <p className="text-[10px] text-[#5D6A75] mt-0.5">Valid beyond {windowDays} days</p>
        </div>

        <div className="bg-white p-4 rounded-[10px] border border-amber-200 bg-amber-50/10 shadow-2xs">
          <span className="text-amber-800 text-[11px] uppercase font-semibold flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            <span>Maturing Within {windowDays} Days</span>
          </span>
          <div className="text-2xl font-bold font-mono text-amber-900 mt-1">
            {isLoading ? '...' : statusCounts?.expiring_soon_count ?? 0}
          </div>
          <p className="text-[10px] text-amber-700 mt-0.5">Action due for renewal or release</p>
        </div>

        <div className="bg-white p-4 rounded-[10px] border border-rose-200 bg-rose-50/10 shadow-2xs">
          <span className="text-rose-800 text-[11px] uppercase font-semibold flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            <span>Matured / Past Due</span>
          </span>
          <div className="text-2xl font-bold font-mono text-rose-900 mt-1">
            {isLoading ? '...' : statusCounts?.matured_count ?? 0}
          </div>
          <p className="text-[10px] text-rose-700 mt-0.5">Term elapsed; awaiting action</p>
        </div>

        <div className="bg-white p-4 rounded-[10px] border border-blue-200 bg-blue-50/10 shadow-2xs">
          <span className="text-blue-800 text-[11px] uppercase font-semibold flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5 text-blue-600" />
            <span>Renewed / Rolled Over</span>
          </span>
          <div className="text-2xl font-bold font-mono text-blue-900 mt-1">
            {isLoading ? '...' : statusCounts?.renewed_count ?? 0}
          </div>
          <p className="text-[10px] text-blue-700 mt-0.5">Linked successor active in lineage</p>
        </div>
      </div>

      {/* Lifecycle & Monitoring Tab Bar */}
      <div className="border-b border-[#C9D3DB] flex items-center gap-2 overflow-x-auto pb-px">
        <button
          type="button"
          onClick={() => setTab('overview')}
          className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            currentTab === 'overview'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Portfolio Overview</span>
        </button>

        <button
          type="button"
          onClick={() => setTab('calendar')}
          className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            currentTab === 'calendar'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>Maturity Calendar</span>
        </button>

        <button
          type="button"
          onClick={() => setTab('maturities')}
          className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            currentTab === 'maturities'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Approaching &amp; Overdue</span>
        </button>

        <button
          type="button"
          onClick={() => setTab('renewals')}
          className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            currentTab === 'renewals'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
          }`}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Renewal Queue</span>
        </button>

        <button
          type="button"
          onClick={() => setTab('lineage')}
          className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            currentTab === 'lineage'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
          }`}
        >
          <GitBranch className="w-3.5 h-3.5" />
          <span>Predecessor–Successor Lineage</span>
        </button>

        <button
          type="button"
          onClick={() => setTab('exceptions')}
          className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
            currentTab === 'exceptions'
              ? 'border-[#0F766E] text-[#0F766E]'
              : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
          }`}
        >
          <AlertOctagon className="w-3.5 h-3.5" />
          <span>Lifecycle Exceptions &amp; Alerts</span>
          {failedNotifications.length > 0 && (
            <span className="bg-rose-100 text-rose-800 px-1.5 py-0.2 rounded-full font-mono text-[9px] font-bold">
              {failedNotifications.length}
            </span>
          )}
        </button>

        {canAccessScheduler && (
          <button
            type="button"
            onClick={() => setTab('scheduler')}
            className={`flex items-center gap-2 px-3.5 py-2 font-semibold text-xs border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
              currentTab === 'scheduler'
                ? 'border-[#0F766E] text-[#0F766E]'
                : 'border-transparent text-[#5D6A75] hover:text-[#0D2538]'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Policies &amp; Scheduler</span>
          </button>
        )}
      </div>

      {/* TAB CONTENT: Overview or Specific View */}
      {currentTab === 'calendar' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-6 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#0F766E]" />
                <span>Statutory Maturity Calendar Horizon</span>
              </h2>
              <p className="text-xs text-[#5D6A75] mt-0.5">
                Surveillance of certificate maturities distributed across current window ({windowDays} days).
              </p>
            </div>
            <span className="font-mono text-xs font-semibold text-[#253746]">
              {maturingItems.length} instrument(s) in timeline
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#C9D3DB] bg-[#F5F4EF] text-[#5D6A75]">
                  <th className="py-2.5 px-3 font-semibold">Reference</th>
                  <th className="py-2.5 px-3 font-semibold">Bank &amp; Branch</th>
                  <th className="py-2.5 px-3 font-semibold">Deposit Value</th>
                  <th className="py-2.5 px-3 font-semibold">Maturity Date</th>
                  <th className="py-2.5 px-3 font-semibold">Days Remaining</th>
                  <th className="py-2.5 px-3 font-semibold">Workflow Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {maturingItems.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2 px-3 font-bold text-[#0D2538]">{item.reference_number}</td>
                    <td className="py-2 px-3 font-sans text-[#253746]">{item.bank_name}</td>
                    <td className="py-2 px-3 text-[#0D2538]">{formatINR(Number(item.amount))}</td>
                    <td className="py-2 px-3 text-[#5D6A75]">{formatDate(item.maturity_date)}</td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          item.days_to_maturity <= 0
                            ? 'bg-rose-100 text-rose-800'
                            : item.days_to_maturity <= 30
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {item.days_to_maturity <= 0 ? 'MATURED' : `${item.days_to_maturity} days`}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-sans">
                      <Link
                        to={`/instruments/${item.id}`}
                        className="text-[#0F766E] hover:underline font-semibold flex items-center gap-1"
                      >
                        <span>Open FDR</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {currentTab === 'maturities' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-6 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-600" />
                <span>Approaching Maturity &amp; Overdue Instruments</span>
              </h2>
              <p className="text-xs text-[#5D6A75] mt-0.5">
                Authoritative backend maturity indicators. Prioritizes expired and ≤ 90-day certificates.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {maturingItems.map((item) => (
              <div
                key={item.id}
                className="p-3.5 rounded-[8px] border border-[#C9D3DB] bg-[#F5F4EF]/30 flex flex-col justify-between space-y-2"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-mono font-bold text-xs text-[#0D2538]">
                      {item.reference_number}
                    </span>
                    <p className="text-[11px] text-[#5D6A75] mt-0.5">{item.bank_name}</p>
                  </div>
                  <span
                    className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold ${
                      item.days_to_maturity <= 0
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {item.days_to_maturity <= 0
                      ? 'EXPIRED / OVERDUE'
                      : `${item.days_to_maturity}d left`}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-200">
                  <span className="font-mono text-xs font-bold text-[#0D2538]">
                    {formatINR(Number(item.amount))}
                  </span>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/instruments/${item.id}`}
                      className="px-2 py-1 rounded bg-white border border-[#C9D3DB] hover:bg-slate-50 text-[11px] font-semibold text-[#253746]"
                    >
                      Inspect FDR
                    </Link>
                    <Link
                      to="/release"
                      className="px-2 py-1 rounded bg-[#123B5D] hover:bg-[#0D2538] text-[11px] font-semibold text-white"
                    >
                      Release Petition
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {currentTab === 'exceptions' && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-6 shadow-2xs space-y-4">
          <div>
            <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-600" />
              <span>Lifecycle Exceptions, Overdue Escalations &amp; Delivery Failures</span>
            </h2>
            <p className="text-xs text-[#5D6A75] mt-0.5">
              Automated audit of failed statutory notification dispatches and overdue SLA escalations.
            </p>
          </div>

          {failedNotifications.length === 0 ? (
            <div className="py-8 text-center bg-emerald-50/40 rounded-[8px] border border-emerald-200 text-emerald-800">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <p className="font-bold text-xs">No Active Delivery Failures</p>
              <p className="text-[10px] text-emerald-700 mt-0.5">
                All statutory multi-tier reminder notifications dispatched successfully without exceptions.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {failedNotifications.map((notif) => (
                <div
                  key={notif.id}
                  className="p-3 rounded-[8px] border border-rose-200 bg-rose-50/20 flex items-center justify-between"
                >
                  <div>
                    <span className="font-mono font-bold text-xs text-rose-900">
                      Notification ID: {notif.id.slice(0, 8)}
                    </span>
                    <p className="text-[11px] text-[#5D6A75] mt-0.5">
                      Type: <strong>{notif.notification_type || notif.event_type}</strong> | Channel: {notif.channel}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRetryFailedNotification(notif.id)}
                    className="px-3 py-1.5 rounded-[6px] bg-rose-600 text-white font-semibold hover:bg-rose-700 text-xs flex items-center gap-1 cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry Dispatch</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {currentTab === 'scheduler' && canAccessScheduler && (
        <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-6 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-[#0F766E]" />
                <span>Lifecycle Policies &amp; Automated Scheduler Console</span>
              </h2>
              <p className="text-xs text-[#5D6A75] mt-0.5">
                Trigger periodic statutory compliance evaluations and dispatch due reminder batches.
              </p>
            </div>
          </div>

          {schedulerActionMessage && (
            <div className="p-3 rounded-[6px] bg-teal-50 border border-teal-200 text-[#0F766E] font-medium text-xs">
              {schedulerActionMessage}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-[8px] border border-[#C9D3DB] space-y-3 bg-[#F5F4EF]/30">
              <h3 className="font-bold text-xs text-[#0D2538]">Statutory Reminder Dispatcher</h3>
              <p className="text-[11px] text-[#5D6A75]">
                Scans all registered in-term instruments and dispatches 90d, 60d, and 30d maturity alerts to designated institutional officers.
              </p>
              <button
                type="button"
                onClick={handleDispatchDue}
                disabled={isDispatching}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-[6px] bg-[#0F766E] text-white font-semibold hover:bg-[#09544E] disabled:opacity-50 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isDispatching ? 'Dispatching...' : 'Dispatch Due Reminders'}</span>
              </button>
            </div>

            <div className="p-4 rounded-[8px] border border-[#C9D3DB] space-y-3 bg-[#F5F4EF]/30">
              <h3 className="font-bold text-xs text-[#0D2538]">Automated Evaluation Policy</h3>
              <p className="text-[11px] text-[#5D6A75]">
                Configured intervals: Daily evaluation at 00:00 UTC. Strict non-competing authoritative status calculated by backend Module 5.
              </p>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono bg-white px-2 py-1 rounded border border-[#C9D3DB]">
                  Status: <strong>ACTIVE</strong>
                </span>
                <span className="text-[10px] font-mono bg-white px-2 py-1 rounded border border-[#C9D3DB]">
                  Mode: <strong>AUTHORITATIVE</strong>
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DEFAULT OVERVIEW / LINEAGE GRID */}
      {(currentTab === 'overview' || currentTab === 'renewals' || currentTab === 'lineage') && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Maturing Queue */}
          <div className="lg:col-span-5 space-y-3">
            <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-[#0F766E]" />
                  <span>
                    {currentTab === 'renewals' ? 'Renewal & Lineage Queue' : 'Maturity Window Queue'} (
                    {filteredItems.length})
                  </span>
                </h2>
                <span className="text-[10px] font-mono text-[#5D6A75]">≤ {windowDays} Days</span>
              </div>

              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter queue by ref or bank..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded-[6px] border border-[#C9D3DB] focus:outline-none focus:border-[#0F766E]"
                />
              </div>

              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {filteredItems.length === 0 ? (
                  <div className="py-8 text-center text-[#5D6A75]">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                    <p className="font-semibold text-[#253746]">
                      No instruments maturing within {windowDays} days
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      All deposits are compliant and in-term.
                    </p>
                  </div>
                ) : (
                  filteredItems.map((item) => {
                    const isSelected = selectedInstrument?.id === item.id;
                    const days = item.days_to_maturity;
                    const isMatured = days <= 0;

                    return (
                      <div
                        key={item.id}
                        onClick={() => handleSelectMaturityItem(item.id)}
                        className={`p-3 rounded-[8px] border cursor-pointer transition-all select-none ${
                          isSelected
                            ? 'bg-[#123B5D] text-white border-[#0F766E] shadow-2xs'
                            : 'bg-[#F5F4EF]/40 hover:bg-[#F5F4EF] text-[#253746] border-slate-200'
                        }`}
                      >
                        <div className="flex items-center justify-between font-mono">
                          <span className="font-bold text-xs">{item.reference_number}</span>
                          <span
                            className={`text-[9px] px-2 py-0.5 rounded font-bold ${
                              isMatured
                                ? 'bg-rose-100 text-rose-800'
                                : days <= 30
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {isMatured ? 'MATURED' : `${days}d`}
                          </span>
                        </div>
                        <div className="text-[11px] opacity-80 mt-1 flex items-center justify-between">
                          <span>{item.bank_name}</span>
                          <span className="font-mono font-semibold">
                            {formatINR(Number(item.amount))}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Selected Instrument Details, Lineage & History */}
          <div className="lg:col-span-7 space-y-4">
            {selectedInstrument ? (
              <div className="space-y-4">
                {/* Header Card for Selected Instrument */}
                <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-[#0D2538]">
                          {selectedInstrument.reference_number}
                        </span>
                        <Badge variant="teal">{selectedInstrument.status}</Badge>
                        <Badge variant="info">{selectedInstrument.trust_level}</Badge>
                      </div>
                      <p className="text-[11px] text-[#5D6A75] mt-1">
                        Bank: <strong>{selectedInstrument.bank_name}</strong> | Branch: {selectedInstrument.branch}
                      </p>
                    </div>

                    <div className="text-right">
                      <span className="text-[11px] text-[#5D6A75]">Deposit Value</span>
                      <div className="text-base font-bold font-mono text-[#0D2538]">
                        {formatINR(Number(selectedInstrument.amount))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/instruments/${selectedInstrument.id}`}
                        className="text-[#0F766E] hover:underline font-semibold flex items-center gap-1 text-xs"
                      >
                        <span>View Full 9-Stage Workflow</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </div>

                    {isOfficerOrAdmin && (
                      <button
                        type="button"
                        onClick={handleTriggerEvaluation}
                        disabled={isEvaluating}
                        className="px-2.5 py-1 rounded-[6px] bg-[#123B5D] hover:bg-[#0D2538] text-white text-[11px] font-semibold flex items-center gap-1 cursor-pointer disabled:opacity-50"
                      >
                        <RefreshCw className={`w-3 h-3 ${isEvaluating ? 'animate-spin' : ''}`} />
                        <span>{isEvaluating ? 'Evaluating...' : 'Re-Evaluate Lifecycle'}</span>
                      </button>
                    )}
                  </div>

                  {evalMessage && (
                    <div className="p-2 rounded bg-teal-50 border border-teal-200 text-[#0F766E] text-[11px] font-mono">
                      {evalMessage}
                    </div>
                  )}
                </div>

                {/* Lineage Section */}
                <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs">
                  <RenewalLineageSection
                    instrumentId={selectedInstrument.id}
                    currentStatus={selectedInstrument.status}
                    institutionId={selectedInstrument.institution_id}
                    onRenewalSuccess={loadData}
                  />
                </div>

                {/* Notification History */}
                <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs">
                  <LifecycleNotificationHistory instrumentId={selectedInstrument.id} />
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-12 text-center text-[#5D6A75] shadow-2xs">
                <Layers className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="font-semibold text-xs text-[#253746]">Select an Instrument</p>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  Choose a certificate from the left queue to inspect its longitudinal maturity and renewal lineage.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
