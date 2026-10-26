import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Building,
  Coins,
  CheckCircle2,
  FileSpreadsheet,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
} from 'lucide-react';
import { releaseApi, ReleaseRequest } from '@/api/release';
import { dashboardApi } from '@/api/endpoints';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { formatINR } from '@/lib/utils';
import type { DashboardSummary } from '@/types';

export const FinanceOfficerWorkspace: React.FC = () => {
  const [approvedCases, setApprovedCases] = useState<ReleaseRequest[]>([]);
  const [recordedOrders, setRecordedOrders] = useState<ReleaseRequest[]>([]);
  const [bankPendingCases, setBankPendingCases] = useState<ReleaseRequest[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [appRes, recRes, bankRes, sumRes] = await Promise.allSettled([
        releaseApi.list({ status: 'APPROVED', limit: 10 }),
        releaseApi.list({ status: 'RELEASE_ORDER_RECORDED', limit: 10 }),
        releaseApi.list({ status: 'BANK_SIDE_ACTION_PENDING', limit: 10 }),
        dashboardApi.getSummary(),
      ]);

      if (appRes.status === 'fulfilled') setApprovedCases(appRes.value);
      if (recRes.status === 'fulfilled') setRecordedOrders(recRes.value);
      if (bankRes.status === 'fulfilled') setBankPendingCases(bankRes.value);
      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
    } catch {
      setError('Unable to load financial operations queue.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const allActionable = [...approvedCases, ...recordedOrders, ...bankPendingCases];

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — Finance Officer */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 text-white shadow-xs border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded font-mono uppercase">
                Financial Operations
              </span>
              <span className="text-[#8799A9] text-xs font-mono">Discharge Orders & Bank Execution</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Financial Operations & Release Order Execution Desk
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Record official release letters for approved cases, confirm downstream bank disbursement execution, perform payee reconciliation, and close completed deposit cases.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link to="/reports">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold">
                <FileSpreadsheet className="w-4 h-4 mr-1.5" /> Financial Reports
              </Button>
            </Link>
            <Link to="/release">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D]">
                <FileText className="w-4 h-4 mr-1.5" /> All Release Cases
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData}>
              <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
            </Button>
          </div>
        </div>
      </div>

      {/* Statutory Notice */}
      <div className="bg-[#EEF6FA] border border-[#C4DEED] rounded-lg p-3.5 flex items-start gap-2.5 text-xs text-[#245B7A]">
        <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Accounting Invariant:</strong> An unverified bank action cannot be marked as completed. Official release letters must be recorded before confirming bank disbursement, and discharge closure requires confirmed bank acknowledgement.
        </p>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center justify-between text-xs text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
          <Button size="sm" variant="outline" onClick={loadData}>Retry</Button>
        </div>
      )}

      {/* KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#E6F4F2] text-[#0F766E] border border-[#99D5CE]">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Awaiting Order Letter</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : approvedCases.length}
              </h3>
              <p className="text-[10px] text-[#0F766E] font-medium mt-0.5">Status: APPROVED</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#FEF7E8] text-[#8A5A00] border border-[#F8DEAE]">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#8A5A00] uppercase tracking-wider">Pending Bank Action</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : recordedOrders.length + bankPendingCases.length}
              </h3>
              <p className="text-[10px] text-[#8A5A00] font-medium mt-0.5">Awaiting Bank Execution</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <Coins className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Total Value Monitored</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : formatINR(summary?.total_deposit_value || '0')}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">{summary?.total_instruments || 0} Registered FDRs</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Matured Deposits</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : summary?.instruments_approaching_maturity ?? 0}
              </h3>
              <p className="text-[10px] text-[#18794E] mt-0.5">Approaching / Due for Action</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Actionable Release Orders Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
              Financial Actions Queue ({allActionable.length})
            </h2>
            <p className="text-xs text-[#5D6A75]">Cases approved by authority requiring release letters or bank execution confirmation</p>
          </div>
          <Link to="/release" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="bg-white rounded-[10px] border border-[#C9D3DB] overflow-hidden shadow-2xs">
          {allActionable.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#5D6A75]">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p>No release cases currently awaiting financial execution.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                  <tr>
                    <th className="py-2.5 px-4 font-semibold">Case Number</th>
                    <th className="py-2.5 px-4 font-semibold">Target FDR</th>
                    <th className="py-2.5 px-4 font-semibold">Tenancy</th>
                    <th className="py-2.5 px-4 font-semibold">Workflow Status</th>
                    <th className="py-2.5 px-4 font-semibold">Required Finance Action</th>
                    <th className="py-2.5 px-4 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {allActionable.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-[#0D2538]">
                        <Link to={`/release/${c.id}`} className="hover:text-[#0F766E] hover:underline">
                          {c.case_number}
                        </Link>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-[#5D6A75]">{c.instrument_id.substring(0, 16)}...</td>
                      <td className="py-3 px-4 font-mono text-xs text-[#5D6A75]">{c.institution_id}</td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            c.workflow_status === 'APPROVED'
                              ? 'success'
                              : c.workflow_status === 'RELEASE_ORDER_RECORDED'
                              ? 'purple'
                              : 'warning'
                          }
                        >
                          {c.workflow_status.replace(/_/g, ' ')}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-xs font-semibold text-[#123B5D]">
                        {c.workflow_status === 'APPROVED'
                          ? 'Generate Official Release Letter'
                          : c.workflow_status === 'RELEASE_ORDER_RECORDED'
                          ? 'Confirm Bank Disbursement'
                          : 'Close Case'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link to={`/release/${c.id}`}>
                          <Button size="sm" className="bg-[#123B5D] text-white">
                            Execute &rarr;
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
