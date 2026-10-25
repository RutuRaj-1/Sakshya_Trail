import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ExternalLink, Clock, AlertTriangle } from 'lucide-react';
import type { VerificationQueueResponse } from '@/types/commandCenter';
import { Badge } from '@/components/common/Badge';

interface VerificationQueueWidgetProps {
  data: VerificationQueueResponse | null;
  isLoading: boolean;
}

export const VerificationQueueWidget: React.FC<VerificationQueueWidgetProps> = ({
  data,
  isLoading,
}) => {
  return (
    <div className="bg-white rounded-[8px] border border-[#C9D3DB] shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-[#F5F4EF]/50">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-purple-600" />
            <h3 className="font-semibold text-[#0D2538] text-sm">
              Bank Verification Desk & Telemetry
            </h3>
            <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded">
              PRD-FR-070d
            </span>
          </div>
          <p className="text-xs text-[#5D6A75] mt-0.5">
            Real-time tracking of in-flight requests, adapter health, and aging distribution.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="purple">{data?.total_outstanding ?? 0} In-Flight</Badge>
          {(data?.source_unavailable_count ?? 0) > 0 && (
            <Badge variant="danger">{data?.source_unavailable_count} Source Unavailable</Badge>
          )}
        </div>
      </div>

      {/* Age Distribution Strips */}
      {data && (
        <div className="px-4 py-2.5 bg-[#F5F4EF] border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <span className="text-[#5D6A75] font-medium">Aging Distribution:</span>
            <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-mono text-[11px]">
              &lt;7d: <strong>{data.age_distribution['<7d'] ?? 0}</strong>
            </span>
            <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-mono text-[11px]">
              7–14d: <strong>{data.age_distribution['7-14d'] ?? 0}</strong>
            </span>
            <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-mono text-[11px]">
              15–30d: <strong>{data.age_distribution['15-30d'] ?? 0}</strong>
            </span>
            <span className="bg-rose-100 text-rose-800 px-2 py-0.5 rounded font-mono text-[11px]">
              &gt;30d: <strong>{data.age_distribution['>30d'] ?? 0}</strong>
            </span>
          </div>
          <div className="text-[#5D6A75] text-xs">
            Average Aging: <strong className="text-[#253746]">{data.average_age_days} days</strong>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto max-h-72">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#F5F4EF] text-[#5D6A75] font-semibold border-b border-[#C9D3DB] sticky top-0">
            <tr>
              <th className="px-4 py-2.5">Reference Code</th>
              <th className="px-4 py-2.5">FDR Reference</th>
              <th className="px-4 py-2.5">Issuing Bank</th>
              <th className="px-4 py-2.5">Transmission Mode</th>
              <th className="px-4 py-2.5">Aging</th>
              <th className="px-4 py-2.5">Channel State</th>
              <th className="px-4 py-2.5 text-right">Verification Desk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-400">
                  Loading verification queue telemetry...
                </td>
              </tr>
            ) : !data || data.records.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-400">
                  ✅ No outstanding bank verification requests in queue.
                </td>
              </tr>
            ) : (
              data.records.map((item) => {
                const isSimulated =
                  item.channel.toUpperCase().includes('SIMULAT') ||
                  item.channel === 'SIMULATED';

                return (
                  <tr key={item.request_id} className="hover:bg-[#F5F4EF]/80 transition-colors">
                    <td className="px-4 py-2.5 font-mono font-medium text-[#0D2538]">
                      {item.reference_code}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[#253746]">
                      {item.instrument_reference}
                    </td>
                    <td className="px-4 py-2.5 text-[#253746]">
                      {item.bank_name}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[11px] text-[#253746]">{item.channel}</span>
                        {isSimulated && (
                          <span
                            className="bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold px-1.5 py-0.2 rounded inline-flex items-center gap-0.5"
                            title="Simulated Response — Prototype adapter only; strictly cannot promote to L3 trust"
                          >
                            SIMULATED
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center gap-1 font-mono text-[#253746]">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {item.age_days}d
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      {item.is_source_unavailable ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-200 px-1.5 py-0.5 rounded">
                          <AlertTriangle className="w-3 h-3" />
                          Source Unavailable
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold text-[#253746] bg-slate-100 px-1.5 py-0.5 rounded">
                          {item.status}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Link
                        to={`/verification/${item.instrument_id}`}
                        className="inline-flex items-center gap-1 text-[#123B5D] hover:text-[#0D2538] font-medium"
                      >
                        Verify Desk <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
