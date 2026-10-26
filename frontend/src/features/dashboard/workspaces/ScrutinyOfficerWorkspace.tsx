import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  FileCheck2,
  ShieldCheck,
  Search,
  ArrowRight,
  RefreshCw,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { findingsApi } from '@/api/endpoints';
import { commandCenterApi } from '@/api/commandCenter';
import { releaseApi, ReleaseRequest } from '@/api/release';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import type { ValidationFindingItem } from '@/types';
import type { DocumentCompletenessResponse, VerificationQueueResponse } from '@/types/commandCenter';

export const ScrutinyOfficerWorkspace: React.FC = () => {
  const [findings, setFindings] = useState<ValidationFindingItem[]>([]);
  const [totalFindings, setTotalFindings] = useState<number>(0);
  const [releaseCases, setReleaseCases] = useState<ReleaseRequest[]>([]);
  const [completeness, setCompleteness] = useState<DocumentCompletenessResponse | null>(null);
  const [verificationQueue, setVerificationQueue] = useState<VerificationQueueResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [findingsRes, releaseRes, compRes, verifRes] = await Promise.allSettled([
        findingsApi.getQueue({ status: ['OPEN', 'INVESTIGATING'], limit: 8 }),
        releaseApi.list({ limit: 8 }),
        commandCenterApi.getDocumentCompleteness(),
        commandCenterApi.getVerificationQueue({ limit: 5 }),
      ]);

      if (findingsRes.status === 'fulfilled') {
        setFindings(findingsRes.value.items || []);
        setTotalFindings(findingsRes.value.total || 0);
      }
      if (releaseRes.status === 'fulfilled') {
        setReleaseCases(
          (releaseRes.value || []).filter((c) => ['SUBMITTED', 'UNDER_REVIEW'].includes(c.workflow_status))
        );
      }
      if (compRes.status === 'fulfilled') setCompleteness(compRes.value);
      if (verifRes.status === 'fulfilled') setVerificationQueue(verifRes.value);
    } catch {
      setError('Unable to load scrutiny data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const criticalFindings = findings.filter((f) => f.severity === 'CRITICAL' || f.severity === 'HIGH');

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — Scrutiny Desk */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 text-white shadow-xs border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded font-mono uppercase">
                Regulatory Examination
              </span>
              <span className="text-[#8799A9] text-xs font-mono">L1/L2 Scrutiny Officer</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Scrutiny & Regulatory Examination Desk
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Inspect algorithmic rule discrepancies, review certified document hashes, evaluate release readiness checklist gates, and attestate evidentiary trust.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link to="/findings/queue">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold">
                <AlertTriangle className="w-4 h-4 mr-1.5" /> Open Review Queue
              </Button>
            </Link>
            <Link to="/verification">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D]">
                <ShieldCheck className="w-4 h-4 mr-1.5" /> Verification Desk
              </Button>
            </Link>
            <Link to="/search">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D]">
                <Search className="w-4 h-4 mr-1.5" /> Unified Search
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData}>
              <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center justify-between text-xs text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
          <Button size="sm" variant="outline" onClick={loadData}>
            Retry
          </Button>
        </div>
      )}

      {/* KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#FDF2F1] text-[#B42318] border border-[#FECDCA]">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Open Discrepancies</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : totalFindings}
              </h3>
              <p className="text-[10px] text-[#B42318] font-medium mt-0.5">
                {criticalFindings.length} Critical / High Severity
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#FEF7E8] text-[#8A5A00] border border-[#F8DEAE]">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Release Reviews</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : releaseCases.length}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Awaiting Scrutiny & Readiness</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Document Quality</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : completeness?.missing_count ?? 0}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Missing Required Documents</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#E6F4F2] text-[#0F766E] border border-[#99D5CE]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Bank Verifications</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : verificationQueue?.total_outstanding ?? 0}
              </h3>
              <p className="text-[10px] text-[#0F766E] mt-0.5">L3 External Confirmation Queue</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Main Workspace Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Priority Discrepancy Queue */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Priority Validation Findings Queue
              </h2>
              <p className="text-xs text-[#5D6A75]">Discrepancies identified by the deterministic rule engine</p>
            </div>
            <Link to="/findings/queue" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
              <span>View Full Queue ({totalFindings})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white rounded-[10px] border border-[#C9D3DB] overflow-hidden shadow-2xs">
            {findings.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#5D6A75]">
                <FileCheck2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <p>No open validation discrepancies found in your review queue.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Severity</th>
                      <th className="py-2.5 px-4 font-semibold">Rule Code</th>
                      <th className="py-2.5 px-4 font-semibold">Target Instrument</th>
                      <th className="py-2.5 px-4 font-semibold">Discrepancy Detail</th>
                      <th className="py-2.5 px-4 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {findings.map((finding) => (
                      <tr key={finding.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4">
                          <span
                            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                              finding.severity === 'CRITICAL'
                                ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                : finding.severity === 'HIGH'
                                ? 'bg-orange-100 text-orange-800 border border-orange-200'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {finding.severity}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-[#0D2538]">{finding.rule_id}</td>
                        <td className="py-3 px-4 font-mono text-xs">
                          <Link to={`/instruments/${finding.instrument_id}`} className="text-[#0F766E] hover:underline">
                            {finding.instrument_id.substring(0, 16)}...
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-[#5D6A75] max-w-xs truncate">{finding.explanation || 'Validation failure'}</td>
                        <td className="py-3 px-4 text-right">
                          <Link to="/findings/queue">
                            <Button size="sm" variant="outline" className="text-[#0F766E] border-[#0F766E]/40">
                              Examine
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

        {/* Right Col: Release Cases Requiring Readiness Review */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Release Case Reviews
              </h2>
              <p className="text-xs text-[#5D6A75]">Readiness evaluation & recommendation</p>
            </div>
            <Link to="/release" className="text-xs text-[#0F766E] font-semibold hover:underline">
              View All
            </Link>
          </div>

          <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 space-y-3 shadow-2xs">
            {releaseCases.length === 0 ? (
              <p className="text-xs text-[#5D6A75] text-center py-6">No release requests awaiting scrutiny review.</p>
            ) : (
              releaseCases.map((rc) => (
                <Link
                  key={rc.id}
                  to={`/release/${rc.id}`}
                  className="block p-3 rounded-lg border border-slate-200 hover:border-[#0F766E] transition-all bg-[#F5F4EF]/40"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-xs text-[#0D2538]">{rc.case_number}</span>
                    <Badge variant={rc.workflow_status === 'SUBMITTED' ? 'info' : 'warning'}>
                      {rc.workflow_status.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#5D6A75] mt-1 line-clamp-1">{rc.request_reason}</p>
                  <div className="flex items-center justify-between text-[10px] text-[#8799A9] mt-2 font-mono">
                    <span>Inst: {rc.institution_id}</span>
                    <span className="text-[#0F766E] font-semibold">Evaluate &rarr;</span>
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
