import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertOctagon,
  TrendingUp,
  ClockAlert,
  ShieldCheck,
  SlidersHorizontal,
  FileSpreadsheet,
  History,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { commandCenterApi } from '@/api/commandCenter';
import { auditApi, AuditChainVerificationResponse } from '@/api/endpoints';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { formatINR } from '@/lib/utils';
import type {
  OverdueEscalatedResponse,
  PriorityQueueResponse,
  MaturityWindowResponse,
} from '@/types/commandCenter';

export const BranchHeadWorkspace: React.FC = () => {
  const [overdue, setOverdue] = useState<OverdueEscalatedResponse | null>(null);
  const [priorityQueue, setPriorityQueue] = useState<PriorityQueueResponse | null>(null);
  const [maturityWindow, setMaturityWindow] = useState<MaturityWindowResponse | null>(null);
  const [chainAudit, setChainAudit] = useState<AuditChainVerificationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [overdueRes, priorityRes, maturityRes, auditRes] = await Promise.allSettled([
        commandCenterApi.getOverdueEscalated({ limit: 6 }),
        commandCenterApi.getPriorityQueue({ min_score: 25, page_size: 6 }),
        commandCenterApi.getMaturityWindow({ window_days: 90, page_size: 5 }),
        auditApi.verifyChain({ sample_size: 15 }),
      ]);

      if (overdueRes.status === 'fulfilled') setOverdue(overdueRes.value);
      if (priorityRes.status === 'fulfilled') setPriorityQueue(priorityRes.value);
      if (maturityRes.status === 'fulfilled') setMaturityWindow(maturityRes.value);
      if (auditRes.status === 'fulfilled') setChainAudit(auditRes.value);
    } catch {
      setError('Unable to load branch oversight metrics.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — Branch Head Cockpit */}
      <div className="bg-[#0D2538] rounded-none p-6 text-white shadow-xs border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded-none font-mono uppercase">
                Regional Oversight
              </span>
              <span className="text-[#8799A9] text-xs font-mono">Branch Head Cockpit</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Branch Executive Portfolio & Escalation Center
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Monitor regional FDR exposure, supervise scrutiny queues, reassign stalled validation cases, and maintain regulatory compliance oversight.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link to="/command-center">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold">
                <SlidersHorizontal className="w-4 h-4 mr-1.5" /> Command Center
              </Button>
            </Link>
            <Link to="/reports">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <FileSpreadsheet className="w-4 h-4 mr-1.5" /> Operational Reports
              </Button>
            </Link>
            <Link to="/audit">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <History className="w-4 h-4 mr-1.5" /> Audit Ledger
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData}>
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
          <Button size="sm" variant="outline" onClick={loadData}>Retry</Button>
        </div>
      )}

      {/* KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#FDF2F1] text-[#B42318] border border-[#FECDCA]">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Overdue & Escalated</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : overdue?.total_overdue ?? 0}
              </h3>
              <p className="text-[10px] text-[#B42318] font-medium mt-0.5">Requires Management Intervention</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#FEF7E8] text-[#8A5A00] border border-[#F8DEAE]">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#8A5A00] uppercase tracking-wider">High Risk Triage</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : priorityQueue?.total_count ?? 0}
              </h3>
              <p className="text-[10px] text-[#8A5A00] mt-0.5">Score &ge; 25 In Queue</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <ClockAlert className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Maturity Load (90d)</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : formatINR(maturityWindow?.total_deposit_value || '0')}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">{maturityWindow?.total_instruments || 0} Instruments Maturing</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Audit Chain Integrity</p>
              <h3 className="text-xl font-bold text-[#18794E] font-mono mt-0.5">
                {isLoading ? '...' : chainAudit?.status || 'VERIFIED'}
              </h3>
              <p className="text-[10px] text-[#18794E] mt-0.5">Cryptographic Hash Intact</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Main Split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Overdue Reviews & Escalated Queue */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Overdue Reviews & Escalations
              </h2>
              <p className="text-xs text-[#5D6A75]">Cases exceeding SLA thresholds requiring reassignment</p>
            </div>
            <Link to="/command-center?tab=escalated" className="text-xs text-[#0F766E] font-semibold hover:underline">
              Inspect All
            </Link>
          </div>

          <div className="bg-white rounded-none border border-[#C9D3DB] p-4 shadow-2xs space-y-3">
            {(!overdue?.records || overdue.records.length === 0) ? (
              <p className="text-xs text-[#5D6A75] text-center py-6">No overdue reviews or escalations currently flagged.</p>
            ) : (
              overdue.records.slice(0, 4).map((item) => (
                <div key={item.record_id} className="p-3 rounded-none border border-rose-200 bg-rose-50/30 flex items-center justify-between">
                  <div>
                    <span className="font-mono font-bold text-xs text-[#0D2538]">{item.reference_number}</span>
                    <p className="text-xs text-[#5D6A75] mt-0.5">
                      {item.assignee_name ? `Assigned: ${item.assignee_name}` : 'Unassigned'} &bull; Overdue:{' '}
                      <strong className="text-rose-700">{item.days_overdue} days</strong>
                    </p>
                  </div>
                  <Link to={`/instruments/${item.record_id}`}>
                    <Button size="sm" variant="outline" className="border-rose-300 text-rose-800">
                      Reassign
                    </Button>
                  </Link>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: High Triage Score FDRs */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Priority Risk Triage Queue
              </h2>
              <p className="text-xs text-[#5D6A75]">Calculated algorithmic score from findings and maturity</p>
            </div>
            <Link to="/command-center?tab=priority" className="text-xs text-[#0F766E] font-semibold hover:underline">
              Full Triage
            </Link>
          </div>

          <div className="bg-white rounded-none border border-[#C9D3DB] p-4 shadow-2xs space-y-3">
            {(!priorityQueue?.items || priorityQueue.items.length === 0) ? (
              <p className="text-xs text-[#5D6A75] text-center py-6">No high-risk instruments in triage queue.</p>
            ) : (
              priorityQueue.items.slice(0, 4).map((item) => (
                <div key={item.instrument_id} className="p-3 rounded-none border border-slate-200 bg-[#F5F4EF]/50 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-[#0D2538]">{item.reference_number}</span>
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-none bg-amber-100 text-amber-900 border border-amber-200">
                        Score: {item.priority_score}
                      </span>
                    </div>
                    <p className="text-xs text-[#5D6A75] mt-0.5">{item.bank_name} &bull; {formatINR(item.amount)}</p>
                  </div>
                  <Link to={`/instruments/${item.instrument_id}`}>
                    <Button size="sm" variant="outline" className="text-[#0F766E] border-[#0F766E]/40">
                      View FDR
                    </Button>
                  </Link>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
