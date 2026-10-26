import React, { useState, useEffect, useCallback } from 'react';
import {
  Clock,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Search,
  ExternalLink,
  Layers,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { instrumentsApi, lifecycleApi } from '@/api/endpoints';
import { commandCenterApi } from '@/api/commandCenter';
import type { Instrument } from '@/types';
import type { StatusCountsResponse, MaturityWindowRecordItem } from '@/types/commandCenter';
import { useAuth } from '@/features/auth/AuthContext';
import { Badge } from '@/components/common/Badge';
import { formatINR } from '@/lib/utils';
import { RenewalLineageSection } from '@/features/lifecycle/RenewalLineageSection';
import { LifecycleNotificationHistory } from '@/features/lifecycle/LifecycleNotificationHistory';

export const MonitoringRenewalsPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const isOfficerOrAdmin = ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY'].includes(
    user?.role || ''
  );

  const initialWindowDays = Number(searchParams.get('window_days')) || 90;

  const [windowDays, setWindowDays] = useState<number>(initialWindowDays);
  const [searchQuery, setSearchQuery] = useState('');

  // Data states
  const [statusCounts, setStatusCounts] = useState<StatusCountsResponse | null>(null);
  const [maturingItems, setMaturingItems] = useState<MaturityWindowRecordItem[]>([]);
  const [selectedInstrument, setSelectedInstrument] = useState<Instrument | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [countsRes, windowRes] = await Promise.all([
        commandCenterApi.getStatusCounts({ window_days: windowDays }),
        commandCenterApi.getMaturityWindow({ window_days: windowDays, page_size: 25 }),
      ]);
      setStatusCounts(countsRes);
      setMaturingItems(windowRes.records);

      if (!selectedInstrument && windowRes.records.length > 0) {
        const inst = await instrumentsApi.get(windowRes.records[0].id);
        setSelectedInstrument(inst);
      }
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [windowDays, selectedInstrument]);

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
      setEvalMessage(`Evaluation recorded: Stage ${res.maturity_stage}, Status: ${res.validity_status}`);
      const updatedInst = await instrumentsApi.get(selectedInstrument.id);
      setSelectedInstrument(updatedInst);
      loadData();
    } catch (err: any) {
      setEvalMessage(err?.response?.data?.message || err?.message || 'Failed to trigger evaluation.');
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans text-xs pb-12">
      {/* Top Banner */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 text-white shadow-[0_1px_3px_rgba(13,37,56,0.08)] border border-[#1e3c54] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2.5 py-0.5 rounded-[4px] uppercase tracking-wider font-mono">
              Module 5 Hub
            </span>
            <span className="text-[#8799A9] text-xs font-mono">Continuous Compliance &amp; Lineage</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            Maturity Monitoring &amp; Renewal Lineage Desk
          </h1>
          <p className="text-xs text-[#C9D3DB] leading-relaxed">
            Statutory calendar maturity surveillance, automated multi-tier reminder intervals (30/60/90 days), and unbroken predecessor-successor lineage trees.
          </p>
        </div>

        {/* Window Selector */}
        <div className="flex items-center gap-2 bg-[#123B5D] p-1.5 rounded-[8px] border border-[#8799A9]/50 shrink-0">
          <span className="text-[11px] text-[#C9D3DB] px-2 font-medium">Window:</span>
          {[30, 60, 90, 180, 365].map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => {
                setWindowDays(days);
                setSearchParams({ window_days: String(days) });
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

      {/* Main Grid: Maturity Window Queue & Lineage Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Maturing Queue */}
        <div className="lg:col-span-5 space-y-3">
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-[#0F766E]" />
                <span>Maturity Window Queue ({maturingItems.length})</span>
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
              {maturingItems.length === 0 ? (
                <div className="py-8 text-center text-[#5D6A75]">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                  <p className="font-semibold text-[#253746]">No instruments maturing within {windowDays} days</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">All deposits are compliant and in-term.</p>
                </div>
              ) : (
                maturingItems
                  .filter(
                    (item) =>
                      !searchQuery ||
                      item.reference_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      item.bank_name.toLowerCase().includes(searchQuery.toLowerCase())
                  )
                  .map((item) => {
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
                                : 'bg-blue-100 text-blue-800'
                            }`}
                          >
                            {isMatured ? 'MATURED' : `${days} DAYS LEFT`}
                          </span>
                        </div>
                        <div className="text-[11px] truncate mt-1 opacity-90">{item.bank_name}</div>
                        <div className="flex items-center justify-between text-[10px] mt-1.5 opacity-75">
                          <span>Amount: {formatINR(Number(item.amount))}</span>
                          <span>Maturity: {item.maturity_date}</span>
                        </div>
                      </div>
                    );
                  })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Selected Instrument Workspace & Lineage Tools */}
        <div className="lg:col-span-7 space-y-4">
          {selectedInstrument ? (
            <>
              {/* Context Strip with Evaluation Trigger */}
              <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[10px] font-mono text-[#8799A9] uppercase">Selected Instrument Context</span>
                  <div className="text-sm font-bold text-[#0D2538] flex items-center gap-2">
                    <span>{selectedInstrument.reference_number}</span>
                    <span className="text-slate-300">|</span>
                    <span className="font-normal text-xs text-[#5D6A75]">{selectedInstrument.bank_name}</span>
                    <Badge variant="teal" className="text-[9px] font-mono">
                      {selectedInstrument.maturity_indicator}
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleTriggerEvaluation}
                    disabled={isEvaluating}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#0F766E] hover:bg-[#09544E] text-white rounded font-semibold text-xs shadow-2xs transition disabled:opacity-50 cursor-pointer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? 'animate-spin' : ''}`} />
                    <span>{isEvaluating ? 'Evaluating...' : 'Evaluate Now'}</span>
                  </button>
                  <Link
                    to={`/instruments/${selectedInstrument.id}`}
                    className="p-1.5 text-slate-500 hover:text-[#0D2538] border border-[#C9D3DB] rounded"
                    title="Open full instrument details"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              {evalMessage && (
                <div className="p-3 rounded bg-teal-50 border border-teal-200 text-teal-900 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#0F766E] shrink-0" />
                  <span>{evalMessage}</span>
                </div>
              )}

              {/* Lineage & Renewal Section */}
              <RenewalLineageSection
                instrumentId={selectedInstrument.id}
                predecessorRecord={{
                  id: selectedInstrument.id,
                  reference_number: selectedInstrument.reference_number,
                  bank_name: selectedInstrument.bank_name,
                  branch: selectedInstrument.branch,
                  amount: selectedInstrument.amount,
                  currency: selectedInstrument.currency,
                  issue_date: selectedInstrument.issue_date,
                  maturity_date: selectedInstrument.maturity_date,
                  status: selectedInstrument.status,
                  trust_level: selectedInstrument.trust_level,
                  institution_id: selectedInstrument.institution_id,
                }}
                canInitiateRenewal={isOfficerOrAdmin || isInstitutionUser}
                isOfficerOrAdmin={isOfficerOrAdmin}
                onRefreshParent={loadData}
              />

              {/* Notification History for this instrument */}
              <LifecycleNotificationHistory
                instrumentId={selectedInstrument.id}
                isOfficerOrAdmin={isOfficerOrAdmin}
              />
            </>
          ) : (
            <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-12 text-center text-[#5D6A75]">
              <Layers className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-[#253746]">No instrument selected</p>
              <p className="text-[11px] text-slate-400 mt-1">
                Select an instrument from the maturity window queue on the left to inspect its lineage and trigger renewal.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
