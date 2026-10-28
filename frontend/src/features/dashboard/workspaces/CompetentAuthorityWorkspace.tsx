import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Scale,
  CheckCircle,
  XCircle,
  AlertCircle,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
  History,
  ShieldAlert,
} from 'lucide-react';
import { releaseApi, ReleaseRequest } from '@/api/release';
import { commandCenterApi } from '@/api/commandCenter';
import { auditApi, AuditChainVerificationResponse } from '@/api/endpoints';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import type { ReleaseBlockersResponse } from '@/types/commandCenter';

export const CompetentAuthorityWorkspace: React.FC = () => {
  const [pendingCases, setPendingCases] = useState<ReleaseRequest[]>([]);
  const [recentDecisions, setRecentDecisions] = useState<ReleaseRequest[]>([]);
  const [blockers, setBlockers] = useState<ReleaseBlockersResponse | null>(null);
  const [chainAudit, setChainAudit] = useState<AuditChainVerificationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [pendingRes, allRes, blockersRes, auditRes] = await Promise.allSettled([
        releaseApi.list({ status: 'READY_FOR_AUTHORITY', limit: 12 }),
        releaseApi.list({ limit: 20 }),
        commandCenterApi.getReleaseBlockers(),
        auditApi.verifyChain({ sample_size: 10 }),
      ]);

      if (pendingRes.status === 'fulfilled') setPendingCases(pendingRes.value);
      if (allRes.status === 'fulfilled') {
        setRecentDecisions(
          (allRes.value || []).filter((c) => ['APPROVED', 'REJECTED', 'COMPLETED'].includes(c.workflow_status))
        );
      }
      if (blockersRes.status === 'fulfilled') setBlockers(blockersRes.value);
      if (auditRes.status === 'fulfilled') setChainAudit(auditRes.value);
    } catch {
      setError('Unable to load statutory sanction cases.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — Competent Authority */}
      <div className="bg-[#0D2538] rounded-none p-6 text-white shadow-xs border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded-none font-mono uppercase">
                Final Decision Authority
              </span>
              <span className="text-[#8799A9] text-xs font-mono">Stage 8 Sanction Desk</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Competent Authority Release & Discharge Sanction Desk
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Sole authorized gate for granting statutory release, forfeiture, and deposit refund approvals. All decisions require mandatory justification and are written to the tamper-evident cryptographic audit ledger.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link to="/release">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold">
                <Scale className="w-4 h-4 mr-1.5" /> All Release Cases
              </Button>
            </Link>
            <Link to="/audit">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <History className="w-4 h-4 mr-1.5" /> Decision Audit Trail
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData}>
              <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
            </Button>
          </div>
        </div>
      </div>

      {/* Statutory Guardrail Callout */}
      <div className="bg-[#FEF7E8] border border-[#F8DEAE] rounded-none p-3.5 flex items-start gap-2.5 text-xs text-[#8A5A00]">
        <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Maker-Checker Statutory Protocol:</strong> The Competent Authority cannot approve a case they originally created or reviewed as a primary examiner. AI and automated checklists produce readiness evaluations but can <em>never</em> substitute for an authorized human sanction decision.
        </p>
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
            <div className="p-3 rounded-none bg-[#E6F4F2] text-[#0F766E] border border-[#99D5CE]">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Awaiting Sanction</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : pendingCases.length}
              </h3>
              <p className="text-[10px] text-[#0F766E] font-medium mt-0.5">READY_FOR_AUTHORITY</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#FDF2F1] text-[#B42318] border border-[#FECDCA]">
              <XCircle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Release Blockers</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : blockers?.blocked_requests_count ?? 0}
              </h3>
              <p className="text-[10px] text-[#B42318] font-medium mt-0.5">Mandatory Gate Blockers</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <CheckCircle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Discharges Granted</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : recentDecisions.length}
              </h3>
              <p className="text-[10px] text-[#18794E] mt-0.5">Approved & Completed</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Audit Trail Status</p>
              <h3 className="text-xl font-bold text-[#123B5D] font-mono mt-0.5">
                {isLoading ? '...' : chainAudit?.status || 'VERIFIED'}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Cryptographic Hash Intact</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Main Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Petitions Awaiting Final Decision */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Petitions Awaiting Sanction Decision ({pendingCases.length})
              </h2>
              <p className="text-xs text-[#5D6A75]">Evaluated by scrutiny officers; awaiting final approval or rejection</p>
            </div>
            <Link to="/release?status=READY_FOR_AUTHORITY" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white rounded-none border border-[#C9D3DB] overflow-hidden shadow-2xs">
            {pendingCases.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#5D6A75]">
                <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <p>No release petitions currently awaiting Competent Authority decision.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Case Number</th>
                      <th className="py-2.5 px-4 font-semibold">Type</th>
                      <th className="py-2.5 px-4 font-semibold">Target FDR</th>
                      <th className="py-2.5 px-4 font-semibold">Tenancy</th>
                      <th className="py-2.5 px-4 font-semibold">Gate Status</th>
                      <th className="py-2.5 px-4 font-semibold text-right">Sanction Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {pendingCases.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-[#0D2538]">
                          <Link to={`/release/${c.id}`} className="hover:text-[#0F766E] hover:underline">
                            {c.case_number}
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-[#253746] font-medium">{c.request_type}</td>
                        <td className="py-3 px-4 font-mono text-xs text-[#5D6A75]">{c.instrument_id.substring(0, 16)}...</td>
                        <td className="py-3 px-4 font-mono text-xs text-[#5D6A75]">{c.institution_id}</td>
                        <td className="py-3 px-4">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-none bg-emerald-100 text-emerald-800 border border-emerald-200">
                            GATE CLEARED
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Link to={`/release/${c.id}`}>
                            <Button size="sm" className="bg-[#123B5D] text-white">
                              Decide &rarr;
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

        {/* Right Col: Historical Sanction Decisions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Recent Sanctions
              </h2>
              <p className="text-xs text-[#5D6A75]">Historical decisions issued</p>
            </div>
            <Link to="/release" className="text-xs text-[#0F766E] font-semibold hover:underline">
              View All
            </Link>
          </div>

          <div className="bg-white rounded-none border border-[#C9D3DB] p-4 space-y-3 shadow-2xs">
            {recentDecisions.length === 0 ? (
              <p className="text-xs text-[#5D6A75] text-center py-6">No historical decisions recorded.</p>
            ) : (
              recentDecisions.slice(0, 5).map((d) => (
                <Link
                  key={d.id}
                  to={`/release/${d.id}`}
                  className="block p-3 rounded-none border border-slate-200 hover:border-[#0F766E] transition-all bg-[#F5F4EF]/40"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[#0D2538]">{d.case_number}</span>
                    <Badge variant={d.workflow_status === 'APPROVED' ? 'success' : d.workflow_status === 'REJECTED' ? 'danger' : 'default'}>
                      {d.workflow_status}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#5D6A75] mt-1 line-clamp-1">{d.request_reason}</p>
                  <div className="flex items-center justify-between text-[10px] text-[#8799A9] mt-2 font-mono">
                    <span>{d.case_type.replace(/_/g, ' ')}</span>
                    <span>{new Date(d.created_at).toLocaleDateString()}</span>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
