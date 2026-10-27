import React from 'react';
import { Link } from 'react-router-dom';
import { Calendar, AlertTriangle, ExternalLink } from 'lucide-react';
import type { MaturityWindowResponse } from '@/types/commandCenter';
import { formatINR } from '@/lib/utils';
import { Badge } from '@/components/common/Badge';

interface MaturityWindowSectionProps {
  data: MaturityWindowResponse | null;
  isLoading: boolean;
  selectedWindowDays: number;
  onWindowChange: (days: number) => void;
}

const trustBadges: Record<string, { label: string; variant: 'default' | 'info' | 'success' | 'purple' }> = {
  L0_DECLARED: { label: 'L0 Declared', variant: 'default' },
  L1_DOCUMENT_CONSISTENT: { label: 'L1 Consistent', variant: 'info' },
  L2_OFFICER_VERIFIED: { label: 'L2 Verified', variant: 'success' },
  L3_BANK_CONFIRMED: { label: 'L3 Confirmed', variant: 'purple' },
};

export const MaturityWindowSection: React.FC<MaturityWindowSectionProps> = ({
  data,
  isLoading,
  selectedWindowDays,
  onWindowChange,
}) => {
  const windowOptions = [
    { label: '30 Days', value: 30 },
    { label: '60 Days', value: 60 },
    { label: '90 Days', value: 90 },
    { label: '180 Days', value: 180 },
    { label: '365 Days', value: 365 },
  ];

  return (
    <div className="bg-white rounded-none border border-[#C9D3DB] shadow-xs overflow-hidden">
      {/* Header with window controls */}
      <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F5F4EF]/50">
        <div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-[#123B5D]" />
            <h3 className="font-semibold text-[#0D2538] text-sm">
              Maturity Window Monitor
            </h3>
            <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded-none">
              PRD-FR-070b
            </span>
          </div>
          <p className="text-xs text-[#5D6A75] mt-0.5">
            Instruments maturing within inclusive selectable calendar window.
          </p>
        </div>

        {/* Window Selector Buttons */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-none border border-[#C9D3DB]">
          {windowOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onWindowChange(opt.value)}
              className={`px-2.5 py-1 text-xs font-medium rounded-none transition-all ${
                selectedWindowDays === opt.value
                  ? 'bg-white text-[#0D2538] shadow-xs border border-[#C9D3DB]/60 font-semibold'
                  : 'text-[#5D6A75] hover:text-[#0D2538] hover:bg-slate-200/50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Mandatory Statutory Notice */}
      <div className="bg-amber-50/70 border-b border-amber-200/60 px-4 py-2 flex items-center gap-2 text-xs text-amber-900">
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
        <span>
          <strong>Statutory Compliance Guard:</strong> Maturity elapsed or approaching does <strong>not</strong> constitute proof of release or refund eligibility. Formal release requires complete checklist satisfaction and competent authority approval.
        </span>
      </div>

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 border-b border-slate-100 bg-white">
        <div>
          <span className="text-xs text-[#5D6A75]">Maturing Count</span>
          <div className="text-lg font-bold text-[#0D2538]">
            {isLoading ? '...' : data?.total_instruments ?? 0} FDRs
          </div>
        </div>
        <div>
          <span className="text-xs text-[#5D6A75]">Total Volume</span>
          <div className="text-lg font-bold text-[#0D2538]">
            {isLoading ? '...' : formatINR(data?.total_deposit_value ?? '0.00')}
          </div>
        </div>
        <div>
          <span className="text-xs text-[#5D6A75]">Window Range</span>
          <div className="text-xs font-medium text-[#253746] mt-1">
            {data ? `${data.start_date} → ${data.end_date}` : 'Calculating...'}
          </div>
        </div>
        <div>
          <span className="text-xs text-[#5D6A75]">Top Issuing Bank</span>
          <div className="text-xs font-medium text-[#253746] mt-1 truncate">
            {data && Object.keys(data.by_bank).length > 0
              ? Object.entries(data.by_bank).sort((a, b) => b[1] - a[1])[0][0]
              : 'None in window'}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#F5F4EF] text-[#5D6A75] font-semibold border-b border-[#C9D3DB]">
            <tr>
              <th className="px-4 py-2.5">Reference #</th>
              <th className="px-4 py-2.5">Institution</th>
              <th className="px-4 py-2.5">Issuing Bank & Branch</th>
              <th className="px-4 py-2.5">Amount (INR)</th>
              <th className="px-4 py-2.5">Maturity Date</th>
              <th className="px-4 py-2.5">Term Status</th>
              <th className="px-4 py-2.5">Trust State</th>
              <th className="px-4 py-2.5 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-400">
                  Loading maturity window records...
                </td>
              </tr>
            ) : !data || data.records.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-400">
                  No statutory instruments maturing within the selected {selectedWindowDays}-day window.
                </td>
              </tr>
            ) : (
              data.records.map((item) => {
                const trust = trustBadges[item.trust_level] || { label: item.trust_level, variant: 'default' };
                const isOverdue = item.days_to_maturity < 0;
                return (
                  <tr key={item.id} className="hover:bg-[#F5F4EF]/80 transition-colors">
                    <td className="px-4 py-2.5 font-mono font-medium text-[#0D2538]">
                      {item.reference_number}
                    </td>
                    <td className="px-4 py-2.5 text-[#253746] max-w-48 truncate">
                      {item.institution_name || item.institution_id}
                    </td>
                    <td className="px-4 py-2.5 text-[#5D6A75]">
                      <div>{item.bank_name}</div>
                      {item.branch && <div className="text-[10px] text-slate-400">{item.branch}</div>}
                    </td>
                    <td className="px-4 py-2.5 font-semibold text-[#0D2538]">
                      {formatINR(item.amount)}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[#253746]">
                      {item.maturity_date}
                    </td>
                    <td className="px-4 py-2.5">
                      {isOverdue ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded-none text-[10px] font-semibold bg-rose-100 text-rose-800">
                          Elapsed ({Math.abs(item.days_to_maturity)}d ago)
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded-none text-[10px] font-semibold bg-amber-100 text-amber-800">
                          In {item.days_to_maturity} days
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant={trust.variant}>{trust.label}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Link
                        to={`/instruments/${item.id}`}
                        className="inline-flex items-center gap-1 text-[#123B5D] hover:text-[#0D2538] font-medium"
                      >
                        Inspect <ExternalLink className="w-3 h-3" />
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
