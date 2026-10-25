import React, { useState } from 'react';
import { BarChart3, Table as TableIcon, Info, Calendar } from 'lucide-react';
import type { MonthWiseMaturityLoadResponse } from '@/types/commandCenter';
import { formatINR } from '@/lib/utils';

interface MaturityLoadChartProps {
  data: MonthWiseMaturityLoadResponse | null;
  isLoading: boolean;
  selectedYear: number;
  onYearChange?: (year: number) => void;
}

export const MaturityLoadChart: React.FC<MaturityLoadChartProps> = ({
  data,
  isLoading,
  selectedYear,
  onYearChange,
}) => {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  // Compute maximum count and amount for relative bar heights
  const points = data?.points || [];
  const maxCount = Math.max(...points.map((p) => p.instrument_count), 1);

  const monthNames = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];

  return (
    <div className="bg-white rounded-[8px] border border-[#C9D3DB] shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F5F4EF]/50">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#123B5D]" />
            <h3 className="font-semibold text-[#0D2538] text-sm">
              Month-Wise Maturity Load (Calendar Year {selectedYear})
            </h3>
            <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded">
              PRD-FR-076
            </span>
          </div>
          <p className="text-xs text-[#5D6A75] mt-0.5">
            Deterministic calendar aggregation of statutory maturity schedules and deposit values.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Year selector */}
          <div className="flex items-center gap-1 text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <select
              aria-label="Select Calendar Year"
              value={selectedYear}
              onChange={(e) => onYearChange?.(Number(e.target.value))}
              className="bg-white border border-[#C9D3DB] text-[#253746] text-xs rounded-md px-2 py-1 font-semibold focus:outline-hidden focus:ring-1 focus:ring-sentinel-500"
            >
              {[selectedYear - 1, selectedYear, selectedYear + 1, selectedYear + 2].map((yr) => (
                <option key={yr} value={yr}>
                  {yr}
                </option>
              ))}
            </select>
          </div>

          {/* Toggle View */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-[#C9D3DB] text-xs">
            <button
              type="button"
              onClick={() => setViewMode('chart')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                viewMode === 'chart'
                  ? 'bg-white text-[#0D2538] shadow-xs font-semibold'
                  : 'text-[#5D6A75] hover:text-[#253746]'
              }`}
              aria-label="Chart view"
            >
              <BarChart3 className="w-3.5 h-3.5" /> Chart
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                viewMode === 'table'
                  ? 'bg-white text-[#0D2538] shadow-xs font-semibold'
                  : 'text-[#5D6A75] hover:text-[#253746]'
              }`}
              aria-label="Accessible table view"
            >
              <TableIcon className="w-3.5 h-3.5" /> Table
            </button>
          </div>
        </div>
      </div>

      {/* Strict Disclaimer Notice */}
      <div className="bg-[#F5F4EF] px-4 py-2 border-b border-slate-100 flex items-center gap-2 text-[11px] text-[#5D6A75]">
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>
          <strong>Accounting Transparency Notice:</strong> {data?.disclaimer || 'Deterministic calendar aggregation based strictly on recorded instrument maturity dates. Not a forecast or projection.'}
        </span>
      </div>

      {/* Main Content Area */}
      <div className="p-4">
        {isLoading ? (
          <div className="h-56 flex items-center justify-center text-xs text-slate-400">
            Loading deterministic maturity load data...
          </div>
        ) : viewMode === 'chart' ? (
          /* Accessible Visual Bar View */
          <div className="space-y-4">
            <div className="grid grid-cols-12 gap-1.5 sm:gap-2 items-end h-48 pt-6 pb-2 border-b border-[#C9D3DB]">
              {points.map((point) => {
                const heightPercent = point.instrument_count > 0
                  ? Math.max(12, Math.round((point.instrument_count / maxCount) * 100))
                  : 4;

                const hasData = point.instrument_count > 0;

                return (
                  <div
                    key={point.month}
                    className="flex flex-col items-center justify-end h-full group relative"
                  >
                    {/* Tooltip on hover */}
                    <div className="absolute -top-12 z-20 hidden group-hover:flex flex-col items-center bg-slate-900 text-white text-[10px] px-2 py-1 rounded shadow-md pointer-events-none whitespace-nowrap">
                      <span><strong>{monthNames[point.month - 1]} {point.year}</strong></span>
                      <span>{point.instrument_count} FDRs ({formatINR(point.total_amount)})</span>
                    </div>

                    <div
                      style={{ height: `${heightPercent}%` }}
                      className={`w-full rounded-t transition-all ${
                        hasData
                          ? 'bg-[#0F766E] group-hover:bg-[#09544E]'
                          : 'bg-slate-100'
                      }`}
                    />
                    <span className="text-[10px] font-mono text-[#5D6A75] mt-2 truncate w-full text-center">
                      {monthNames[point.month - 1]}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Grand Totals Summary */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs text-[#5D6A75] pt-1">
              <div>
                Total Scheduled Instruments ({selectedYear}):{' '}
                <strong className="text-[#0D2538] font-mono">{data?.grand_total_instruments ?? 0}</strong>
              </div>
              <div>
                Total Cumulative Deposit Value:{' '}
                <strong className="text-[#0D2538] font-mono">
                  {formatINR(data?.grand_total_amount ?? '0.00')}
                </strong>
              </div>
            </div>
          </div>
        ) : (
          /* Accessible Tabular View */
          <div className="overflow-x-auto max-h-56">
            <table className="w-full text-left text-xs" aria-label="Month-wise maturity table">
              <thead className="bg-[#F5F4EF] text-[#5D6A75] font-semibold border-b border-[#C9D3DB]">
                <tr>
                  <th className="px-3 py-2">Month Period</th>
                  <th className="px-3 py-2 text-right">Instruments Due</th>
                  <th className="px-3 py-2 text-right">Recorded Value (INR ₹)</th>
                  <th className="px-3 py-2 text-right">% of Annual Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {points.map((pt) => {
                  const pct = (data?.grand_total_instruments ?? 0) > 0
                    ? ((pt.instrument_count / data!.grand_total_instruments) * 100).toFixed(1)
                    : '0.0';

                  return (
                    <tr key={pt.month} className="hover:bg-[#F5F4EF]/80">
                      <td className="px-3 py-2 font-mono text-[#0D2538] font-medium">
                        {monthNames[pt.month - 1]} {pt.year} ({pt.month_label})
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-[#253746]">
                        {pt.instrument_count}
                      </td>
                      <td className="px-3 py-2 text-right font-mono font-semibold text-[#0D2538]">
                        {formatINR(pt.total_amount)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-[#5D6A75]">
                        {pct}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
