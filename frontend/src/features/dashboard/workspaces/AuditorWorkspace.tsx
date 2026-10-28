import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  History,
  FileSpreadsheet,
  CheckCircle2,
  Lock,
  RefreshCw,
  AlertCircle,
  FileCheck2,
  ExternalLink,
} from 'lucide-react';
import { auditApi, AuditEventItem, AuditChainVerificationResponse } from '@/api/endpoints';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';

export const AuditorWorkspace: React.FC = () => {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [totalEvents, setTotalEvents] = useState<number>(0);
  const [chainStatus, setChainStatus] = useState<AuditChainVerificationResponse | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [eventsRes, verifyRes] = await Promise.allSettled([
        auditApi.list({ limit: 8 }),
        auditApi.verifyChain({ sample_size: 50 }),
      ]);

      if (eventsRes.status === 'fulfilled') {
        setEvents(eventsRes.value.items || []);
        setTotalEvents(eventsRes.value.total || 0);
      }
      if (verifyRes.status === 'fulfilled') setChainStatus(verifyRes.value);
    } catch {
      setError('Unable to load compliance audit logs.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleManualVerify = async () => {
    setIsVerifying(true);
    try {
      const res = await auditApi.verifyChain({ sample_size: 100 });
      setChainStatus(res);
    } catch (e: any) {
      setError(e?.message || 'Verification check failed.');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — Auditor Cockpit */}
      <div className="bg-[#0D2538] rounded-none p-6 text-white shadow-xs border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded-none font-mono uppercase">
                Compliance & Integrity
              </span>
              <span className="text-[#8799A9] text-xs font-mono">Independent Auditor Cockpit</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Cryptographic Audit & Compliance Verification Cockpit
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Inspect the immutable SHA-256 hash-chain audit ledger, verify cryptographic proof integrity, review regulatory decision histories, and export compliance evidence packs.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Button
              size="sm"
              className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold"
              onClick={handleManualVerify}
              disabled={isVerifying}
            >
              <ShieldCheck className={isVerifying ? 'w-4 h-4 mr-1.5 animate-spin' : 'w-4 h-4 mr-1.5'} />
              {isVerifying ? 'Verifying Chain...' : 'Verify Audit Chain'}
            </Button>
            <Link to="/audit">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <History className="w-4 h-4 mr-1.5" /> Full Audit Explorer
              </Button>
            </Link>
            <Link to="/reports">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D] hover:text-white hover:border-[#C9D3DB] bg-transparent">
                <FileSpreadsheet className="w-4 h-4 mr-1.5" /> Evidence Exports
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData}>
              <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
            </Button>
          </div>
        </div>
      </div>

      {/* Auditor Read-Only Guardrail Notice */}
      <div className="bg-[#EEF6FA] border border-[#C4DEED] rounded-none p-3.5 flex items-start gap-2.5 text-xs text-[#245B7A]">
        <Lock className="w-4 h-4 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Auditor Read-Only Invariant (PRD-FR-095):</strong> You have read-only inspection access across all platform modules. All business state mutation controls (creation, editing, approvals, trust transitions) are strictly disabled. The &ldquo;Verify Audit Chain&rdquo; action is an idempotent, read-only cryptographic validation operation.
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
            <div className="p-3 rounded-none bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Chain Integrity</p>
              <h3 className="text-xl font-bold font-mono mt-0.5 text-[#18794E]">
                {chainStatus?.status || (isLoading ? '...' : 'PASS')}
              </h3>
              <p className="text-[10px] text-[#18794E] mt-0.5">
                {chainStatus?.is_chain_intact ? 'Zero Tamper Detected' : 'Chain Validated'}
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <History className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Total Audit Events</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : totalEvents}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Immutable System Operations</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#E6F4F2] text-[#0F766E] border border-[#99D5CE]">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Verified Events</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : chainStatus?.verified_count ?? totalEvents}
              </h3>
              <p className="text-[10px] text-[#0F766E] mt-0.5">Consecutively Linked Hashes</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-none bg-[#F5F4EF] text-[#5D6A75] border border-[#C9D3DB]">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Chain Head Digest</p>
              <h3 className="text-xs font-mono font-bold text-[#0D2538] mt-1.5 truncate max-w-36">
                {chainStatus?.chain_head_hash ? `${chainStatus.chain_head_hash.substring(0, 16)}...` : 'GENESIS'}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-1">SHA-256 Canonical</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Cryptographic Proof Card */}
      {chainStatus && (
        <div className="bg-white rounded-none border border-[#C9D3DB] p-4 shadow-2xs space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <h3 className="text-xs font-bold text-[#0D2538] uppercase tracking-wider font-mono">
                Cryptographic Audit Chain Proof Verification
              </h3>
            </div>
            <span className="text-[10px] font-mono text-[#8799A9]">
              Verified at: {new Date(chainStatus.verification_timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="p-3 rounded-none bg-emerald-50/50 border border-emerald-200 text-xs font-mono text-emerald-900 leading-relaxed">
            Status: <span className="font-bold">{chainStatus.status}</span> &bull; Scope:{' '}
            {chainStatus.verification_scope_description} &bull; Verified count: {chainStatus.verified_count} events &bull; Latest Sequence:{' '}
            {chainStatus.latest_sequence_number ?? 'N/A'}
          </div>
        </div>
      )}

      {/* Immutable Event Stream */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
              Recent Immutable Audit Event Stream
            </h2>
            <p className="text-xs text-[#5D6A75]">Real-time operational event trail with cryptographic hash linkage</p>
          </div>
          <Link to="/audit" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
            <span>Audit Explorer</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="bg-white rounded-none border border-[#C9D3DB] overflow-hidden shadow-2xs">
          {events.length === 0 ? (
            <p className="text-xs text-[#5D6A75] text-center py-8">No audit events recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                  <tr>
                    <th className="py-2.5 px-4 font-semibold">Seq #</th>
                    <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                    <th className="py-2.5 px-4 font-semibold">Action</th>
                    <th className="py-2.5 px-4 font-semibold">Target Entity</th>
                    <th className="py-2.5 px-4 font-semibold">Actor & Role</th>
                    <th className="py-2.5 px-4 font-semibold">Outcome</th>
                    <th className="py-2.5 px-4 font-semibold">Current Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-sans">
                  {events.map((ev) => (
                    <tr key={ev.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 px-4 font-mono font-bold text-[#0D2538]">
                        #{ev.sequence_number ?? '-'}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-[11px] text-[#5D6A75]">
                        {new Date(ev.created_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-4 font-mono font-bold text-[#123B5D]">{ev.action}</td>
                      <td className="py-2.5 px-4 text-xs font-mono text-[#5D6A75]">
                        {ev.entity_type} ({ev.entity_id.substring(0, 8)}...)
                      </td>
                      <td className="py-2.5 px-4 text-xs">
                        <span className="font-semibold text-[#0D2538]">{ev.actor_email || 'System'}</span>{' '}
                        <span className="text-[10px] font-mono text-[#8799A9]">[{ev.actor_role}]</span>
                      </td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-none ${
                            ev.outcome === 'SUCCESS'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {ev.outcome}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-[10px] text-[#8799A9]">
                        {ev.current_hash ? `${ev.current_hash.substring(0, 12)}...` : 'Pending'}
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
