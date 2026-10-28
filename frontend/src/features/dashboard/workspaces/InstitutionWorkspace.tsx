import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Coins,
  ShieldCheck,
  ClockAlert,
  FileText,
  UploadCloud,
  FilePlus2,
  AlertCircle,
  ArrowRight,
  RotateCcw,
  RefreshCw,
  Bell,
  Building2,
} from 'lucide-react';
import { instrumentsApi, dashboardApi, lifecycleApi } from '@/api/endpoints';
import { releaseApi, ReleaseRequest } from '@/api/release';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { formatINR } from '@/lib/utils';
import type { Instrument, DashboardSummary } from '@/types';
import type { LifecycleNotification } from '@/types/lifecycle';

export const InstitutionWorkspace: React.FC = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [releaseRequests, setReleaseRequests] = useState<ReleaseRequest[]>([]);
  const [notifications, setNotifications] = useState<LifecycleNotification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumRes, instRes, relRes, notifRes] = await Promise.allSettled([
        dashboardApi.getSummary(),
        instrumentsApi.list({ limit: 8 }),
        releaseApi.list({ limit: 5 }),
        lifecycleApi.getUserInbox(true),
      ]);

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (instRes.status === 'fulfilled') setInstruments(instRes.value.items);
      if (relRes.status === 'fulfilled') setReleaseRequests(relRes.value);
      if (notifRes.status === 'fulfilled') setNotifications(notifRes.value.notifications || []);

      if (sumRes.status === 'rejected' && instRes.status === 'rejected') {
        setError('Failed to load institutional records. Please verify connectivity.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const returnedInstruments = instruments.filter((i) => i.status === 'RETURNED_FOR_CORRECTION');
  const draftInstruments = instruments.filter((i) => i.status === 'DRAFT');

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — Institutional Vault */}
      <div className="bg-[#0D2538] rounded-none p-6 text-white shadow-[0_1px_3px_rgba(13,37,56,0.08)] border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded-none font-mono uppercase">
                Institutional Tenancy
              </span>
              <span className="text-[#8799A9] text-xs font-mono">
                Tenancy ID: {user?.institution_id || 'AICTE-NODAL'}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Institutional FDR Portfolio Vault
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Manage your institution&apos;s security deposit receipts, upload authenticated evidence, track regulatory scrutiny findings, and file statutory release petitions.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link to="/instruments">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold">
                <FilePlus2 className="w-4 h-4 mr-1.5" /> Register FDR
              </Button>
            </Link>
            <Link to="/documents">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <UploadCloud className="w-4 h-4 mr-1.5" /> Upload Evidence
              </Button>
            </Link>
            <Link to="/release">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <FileText className="w-4 h-4 mr-1.5" /> Release Petition
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData} title="Refresh Live Data">
              <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-none p-4 flex items-center justify-between text-xs text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
          <Button size="sm" variant="outline" onClick={loadData}>
            Retry
          </Button>
        </div>
      )}

      {/* Attention Callouts */}
      {returnedInstruments.length > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-none p-4 flex items-start gap-3">
          <RotateCcw className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
              {returnedInstruments.length} FDR Submission(s) Returned for Institutional Correction
            </h3>
            <p className="text-xs text-amber-800 mt-0.5">
              The regulatory scrutiny officer found discrepancies requiring correction. Please review observation notes, amend values, and resubmit.
            </p>
            <div className="mt-2 flex gap-2">
              {returnedInstruments.map((inst) => (
                <Link key={inst.id} to={`/instruments/${inst.id}`}>
                  <span className="text-[11px] font-mono font-semibold bg-white px-2 py-0.5 rounded-none border border-amber-300 text-amber-900 hover:underline">
                    {inst.reference_number} &rarr;
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Primary KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <Coins className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Total Deposit Value</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : formatINR(summary?.total_deposit_value || '0')}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">{summary?.total_instruments || 0} Registered Instruments</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Active Lien Status</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : summary?.instruments_by_status?.REGISTERED || 0}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Compliant Statutory Deposits</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#F5F4EF] text-[#5D6A75] border border-[#C9D3DB]">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Pending Evidence</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : draftInstruments.length}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Drafts Awaiting Certified Scan</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#FEF7E8] text-[#8A5A00] border border-[#F8DEAE]">
              <ClockAlert className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#8A5A00] uppercase tracking-wider">Expiring Soon (90d)</p>
              <h3 className="text-xl font-bold text-[#8A5A00] font-mono mt-0.5">
                {isLoading ? '...' : summary?.instruments_approaching_maturity || 0}
              </h3>
              <p className="text-[10px] text-[#8A5A00] mt-0.5">Requires Successor Rollover</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Portfolio & Release Requests Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: My FDR Portfolio */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Active FDR Portfolio
              </h2>
              <p className="text-xs text-[#5D6A75]">Monitored statutory deposits for this institution</p>
            </div>
            <Link to="/instruments" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white rounded-none border border-[#C9D3DB] overflow-hidden shadow-2xs">
            {instruments.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#5D6A75]">
                <Building2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p>No FDR records registered yet for your institution.</p>
                <Link to="/instruments" className="mt-3 inline-block">
                  <Button size="sm" className="bg-[#0F766E] text-white">Record First FDR</Button>
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Reference</th>
                      <th className="py-2.5 px-4 font-semibold">Bank</th>
                      <th className="py-2.5 px-4 font-semibold text-right">Principal</th>
                      <th className="py-2.5 px-4 font-semibold">Maturity</th>
                      <th className="py-2.5 px-4 font-semibold">Trust Tier</th>
                      <th className="py-2.5 px-4 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {instruments.map((inst) => (
                      <tr key={inst.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-[#0D2538]">
                          <Link to={`/instruments/${inst.id}`} className="hover:text-[#0F766E] hover:underline">
                            {inst.reference_number}
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-[#253746] font-medium">{inst.bank_name}</td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-[#0D2538]">
                          {formatINR(inst.amount)}
                        </td>
                        <td className="py-3 px-4 font-mono text-[#5D6A75]">
                          {inst.maturity_date ? new Date(inst.maturity_date).toLocaleDateString() : 'N/A'}
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-none bg-blue-50 text-blue-800 border border-blue-200">
                            {inst.trust_level}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={inst.status === 'REGISTERED' ? 'success' : inst.status === 'DRAFT' ? 'default' : 'warning'}>
                            {inst.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Active Release Petitions & Notifications */}
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                  Release & Refund Cases
                </h2>
                <p className="text-xs text-[#5D6A75]">Discharge requests filed with authority</p>
              </div>
              <Link to="/release" className="text-xs text-[#0F766E] font-semibold hover:underline">
                View All
              </Link>
            </div>

            <div className="bg-white rounded-none border border-[#C9D3DB] p-4 space-y-3 shadow-2xs">
              {releaseRequests.length === 0 ? (
                <div className="text-center py-6 text-xs text-[#5D6A75]">
                  <FileText className="w-6 h-6 text-slate-300 mx-auto mb-1.5" />
                  <p>No active release requests pending.</p>
                </div>
              ) : (
                releaseRequests.map((req) => (
                  <Link
                    key={req.id}
                    to={`/release/${req.id}`}
                    className="block p-3 rounded-none border border-slate-200 hover:border-[#0F766E] transition-all bg-[#F5F4EF]/50"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-[#0D2538]">{req.case_number}</span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-none bg-amber-50 text-amber-800 border border-amber-200">
                        {req.workflow_status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-[#5D6A75] mt-1 line-clamp-1">{req.request_reason}</p>
                    <div className="flex items-center justify-between text-[10px] text-[#8799A9] mt-2 font-mono">
                      <span>Type: {req.request_type}</span>
                      <span>{new Date(req.created_at).toLocaleDateString()}</span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          {/* Actionable Notifications */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Bell className="w-4 h-4 text-[#123B5D]" />
              <h2 className="text-xs font-bold text-[#0D2538] uppercase tracking-wider">
                Actionable Alerts ({notifications.length})
              </h2>
            </div>
            <div className="bg-white rounded-none border border-[#C9D3DB] p-3 space-y-2 shadow-2xs">
              {notifications.length === 0 ? (
                <p className="text-xs text-[#5D6A75] text-center py-3">No pending compliance alerts.</p>
              ) : (
                notifications.slice(0, 3).map((notif) => (
                  <div key={notif.id} className="p-2.5 rounded-none bg-slate-50 border border-slate-200 text-xs">
                    <p className="font-semibold text-[#0D2538]">{notif.rendered_title || notif.event_type.replace(/_/g, ' ')}</p>
                    <p className="text-[11px] text-[#5D6A75] mt-0.5">{notif.channel} notification generated</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
