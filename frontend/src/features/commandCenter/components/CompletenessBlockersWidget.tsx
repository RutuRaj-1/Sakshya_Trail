import React from 'react';
import { Link } from 'react-router-dom';
import { FileCheck, ArrowUpRight, AlertOctagon, HelpCircle } from 'lucide-react';
import type { DocumentCompletenessResponse, ReleaseBlockersResponse } from '@/types/commandCenter';

interface CompletenessBlockersWidgetProps {
  completeness: DocumentCompletenessResponse | null;
  blockers: ReleaseBlockersResponse | null;
  isLoading: boolean;
}

export const CompletenessBlockersWidget: React.FC<CompletenessBlockersWidgetProps> = ({
  completeness,
  blockers,
  isLoading,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 1. Document Completeness Checklist (PRD-FR-070e) */}
      <div className="bg-white rounded-none border border-[#C9D3DB] shadow-xs p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald-600" />
              <h3 className="font-semibold text-[#0D2538] text-sm">
                Document Completeness
              </h3>
              <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded-none">
                PRD-FR-070e
              </span>
            </div>
            {completeness?.policy_configured ? (
              <span className="text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-none font-mono">
                Policy v{completeness.policy_version ?? 1}
              </span>
            ) : (
              <span className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-none font-bold">
                POLICY UNCONFIGURED
              </span>
            )}
          </div>

          {!completeness?.policy_configured && (
            <div className="mt-3 bg-amber-50 border border-amber-200/80 rounded-none p-2.5 text-xs text-amber-900 flex items-start gap-2">
              <HelpCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <strong>Policy Configuration Notice:</strong> No active <code>REQUIRED_DOCUMENT_CATEGORIES</code> policy is published. System explicitly reports unconfigured policy state rather than misleading zeros.
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <div className="bg-[#F5F4EF] rounded-none p-3 border border-slate-100">
              <span className="text-[11px] text-[#5D6A75] font-medium">Present / Clean</span>
              <div className="text-xl font-bold text-emerald-600 mt-1">
                {isLoading ? '...' : completeness?.present_count ?? 0}
              </div>
            </div>
            <div className="bg-[#F5F4EF] rounded-none p-3 border border-slate-100">
              <span className="text-[11px] text-[#5D6A75] font-medium">Missing Req.</span>
              <div className="text-xl font-bold text-rose-600 mt-1">
                {isLoading ? '...' : completeness?.missing_count ?? 0}
              </div>
            </div>
            <div className="bg-[#F5F4EF] rounded-none p-3 border border-slate-100">
              <span className="text-[11px] text-[#5D6A75] font-medium">Unreadable</span>
              <div className="text-xl font-bold text-amber-600 mt-1">
                {isLoading ? '...' : completeness?.unreadable_count ?? 0}
              </div>
            </div>
            <div className="bg-[#F5F4EF] rounded-none p-3 border border-slate-100">
              <span className="text-[11px] text-[#5D6A75] font-medium">Awaiting Scan</span>
              <div className="text-xl font-bold text-blue-600 mt-1">
                {isLoading ? '...' : completeness?.awaiting_confirmation_count ?? 0}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-[#5D6A75]">
          <span>Wrong Category / Findings: <strong>{completeness?.wrong_category_count ?? 0}</strong></span>
          <Link to="/findings/queue" className="text-[#123B5D] hover:text-[#0D2538] font-medium inline-flex items-center gap-1">
            Review Findings <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* 2. Release & Refund Gate Blockers (PRD-FR-070f) */}
      <div className="bg-white rounded-none border border-[#C9D3DB] shadow-xs p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-rose-600" />
              <h3 className="font-semibold text-[#0D2538] text-sm">
                Release Gate Blockers
              </h3>
              <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded-none">
                PRD-FR-070f
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-none font-bold">
                {blockers?.blocked_requests_count ?? 0} Blocked
              </span>
              <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-none font-medium">
                {blockers?.ready_requests_count ?? 0} Ready
              </span>
            </div>
          </div>

          <div className="mt-3">
            <p className="text-xs text-[#5D6A75]">
              Active release/refund cases obstructed by unmet mandatory checklist items per Module 6 Release Gate engine.
            </p>

            {/* Blocked Cases List */}
            <div className="mt-3 space-y-2 max-h-40 overflow-y-auto pr-1">
              {isLoading ? (
                <div className="text-xs text-slate-400 py-3 text-center">Loading release blockers...</div>
              ) : !blockers || blockers.cases.length === 0 ? (
                <div className="text-xs text-[#5D6A75] py-4 text-center bg-[#F5F4EF] rounded-none">
                  ✅ No release or refund cases are currently obstructed by mandatory blockers.
                </div>
              ) : (
                blockers.cases.map((c) => (
                  <div
                    key={c.case_id}
                    className="p-2.5 rounded-none border border-rose-100 bg-rose-50/40 flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="font-mono font-bold text-[#0D2538] flex items-center gap-2">
                        <span>{c.case_number}</span>
                        <span className="text-[10px] bg-rose-200 text-rose-800 px-1.5 py-0.2 rounded-none">
                          {c.blockers_count} Blocker{c.blockers_count > 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#5D6A75] mt-0.5 truncate max-w-72">
                        FDR: {c.instrument_reference} ({c.case_type})
                      </div>
                    </div>
                    <Link
                      to={`/release/${c.case_id}`}
                      className="px-2 py-1 bg-white border border-[#C9D3DB] text-[#253746] hover:text-[#0D2538] rounded-none text-[11px] font-medium shrink-0 shadow-2xs hover:bg-[#F5F4EF]"
                    >
                      Resolve Gate
                    </Link>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-[#5D6A75]">
          <span>Total Active Cases: <strong>{blockers?.total_active_release_requests ?? 0}</strong></span>
          <Link to="/release" className="text-[#123B5D] hover:text-[#0D2538] font-medium inline-flex items-center gap-1">
            All Release Cases <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  );
};
