import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  SlidersHorizontal,
  ArrowUpRight,
  Info,
} from 'lucide-react';
import type { PriorityQueueResponse } from '@/types/commandCenter';
import { formatINR } from '@/lib/utils';

interface PriorityQueueDeskProps {
  data: PriorityQueueResponse | null;
  isLoading: boolean;
  minScore: number;
  onMinScoreChange: (score: number) => void;
}

export const PriorityQueueDesk: React.FC<PriorityQueueDeskProps> = ({
  data,
  isLoading,
  minScore,
  onMinScoreChange,
}) => {
  const [showWeightsInfo, setShowWeightsInfo] = useState(false);

  const getScoreBadgeClass = (score: number) => {
    if (score >= 75) return 'bg-rose-100 text-rose-800 border-rose-300';
    if (score >= 50) return 'bg-amber-100 text-amber-800 border-amber-300';
    if (score >= 25) return 'bg-blue-100 text-blue-800 border-blue-300';
    return 'bg-slate-100 text-[#253746] border-[#8799A9]';
  };

  return (
    <div className="bg-white rounded-[8px] border border-[#C9D3DB] shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F5F4EF]/50">
        <div>
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-[#123B5D]" />
            <h3 className="font-semibold text-[#0D2538] text-sm">
              Operational Priority Queue & Factor Transparency
            </h3>
            <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded">
              PRD-FR-075
            </span>
          </div>
          <p className="text-xs text-[#5D6A75] mt-0.5">
            Objective urgency ranking for officer scrutiny with fully explainable contributing factors.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Min score threshold selector */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-[#5D6A75] font-medium">Min Score:</span>
            <select
              aria-label="Filter Minimum Priority Score"
              value={minScore}
              onChange={(e) => onMinScoreChange(Number(e.target.value))}
              className="bg-white border border-[#C9D3DB] text-[#253746] text-xs rounded-md px-2 py-1 font-semibold focus:outline-hidden"
            >
              <option value={0}>All Items (0+)</option>
              <option value={25}>Moderate+ (25+)</option>
              <option value={50}>Elevated+ (50+)</option>
              <option value={75}>Critical Urgency (75+)</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => setShowWeightsInfo(!showWeightsInfo)}
            className="text-xs text-[#123B5D] bg-[#EEF6FA] border border-[#C4DEED] hover:bg-[#EEF6FA] px-2.5 py-1 rounded-md flex items-center gap-1 font-medium"
          >
            <Info className="w-3.5 h-3.5" />
            <span>Weights & Assumptions</span>
          </button>
        </div>
      </div>

      {/* Mandatory Statutory Notice Regarding Score Meaning */}
      <div className="bg-blue-50/70 border-b border-blue-200/60 px-4 py-2 flex items-start sm:items-center gap-2 text-xs text-blue-950">
        <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5 sm:mt-0" />
        <span>
          <strong>Methodological Clarification:</strong> This 0–100 ranking is strictly an <strong>operational workflow-priority score</strong> to guide scrutiny triage. It is <strong>NOT</strong> a fraud probability, credit rating, or authenticity determination. Anomaly flags do not prove fraud.
        </span>
      </div>

      {/* Disclosed Weight Assumptions Banner */}
      {showWeightsInfo && (
        <div className="bg-[#F5F4EF] border-b border-[#C9D3DB] p-3 text-xs text-[#253746] space-y-1">
          <div className="font-semibold text-[#0D2538]">Deterministic Weight Assumptions Disclosed:</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
            <div className="bg-white p-2 rounded border border-[#C9D3DB]">
              <span className="text-[#5D6A75] block">1. Urgency (Maturity Proximity):</span>
              <strong>35% Weight</strong>
            </div>
            <div className="bg-white p-2 rounded border border-[#C9D3DB]">
              <span className="text-[#5D6A75] block">2. Discrepancy Findings Severity:</span>
              <strong>25% Weight</strong>
            </div>
            <div className="bg-white p-2 rounded border border-[#C9D3DB]">
              <span className="text-[#5D6A75] block">3. Evidentiary Trust State:</span>
              <strong>20% Weight</strong>
            </div>
            <div className="bg-white p-2 rounded border border-[#C9D3DB]">
              <span className="text-[#5D6A75] block">4. Overdue Compliance Lead Time:</span>
              <strong>20% Weight</strong>
            </div>
          </div>
          <div className="text-[10px] text-[#5D6A75] pt-1">
            *Tie-breaking is deterministic: sorted by Priority Score descending, then recorded maturity date ascending, then reference number.
          </div>
        </div>
      )}

      {/* Priority Table */}
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#F5F4EF] text-[#5D6A75] font-semibold border-b border-[#C9D3DB] sticky top-0 z-10">
            <tr>
              <th className="px-4 py-2.5">Priority Score</th>
              <th className="px-4 py-2.5">Contributing Factors Breakdown</th>
              <th className="px-4 py-2.5">FDR Reference</th>
              <th className="px-4 py-2.5">Institution</th>
              <th className="px-4 py-2.5">Issuing Bank</th>
              <th className="px-4 py-2.5">Maturity Proximity</th>
              <th className="px-4 py-2.5">Amount (INR)</th>
              <th className="px-4 py-2.5 text-right">Triage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-400">
                  Computing operational priority ranks...
                </td>
              </tr>
            ) : !data || data.items.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-400">
                  No records match the minimum score threshold of {minScore}.
                </td>
              </tr>
            ) : (
              data.items.map((item) => (
                <tr key={item.instrument_id} className="hover:bg-[#F5F4EF]/80 transition-colors">
                  {/* Score */}
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex items-center justify-center font-mono font-extrabold text-xs px-2 py-1 rounded-md border ${getScoreBadgeClass(
                        item.priority_score
                      )}`}
                    >
                      {item.priority_score.toFixed(1)} / 100
                    </span>
                  </td>

                  {/* Factor Breakdown Bars */}
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5 text-[10px] font-mono">
                      <span
                        className="bg-slate-100 px-1.5 py-0.5 rounded text-[#253746]"
                        title={`Urgency Factor: ${item.urgency_factor}/100 (35% weight)`}
                      >
                        Urg: <strong>{item.urgency_factor.toFixed(0)}</strong>
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded ${
                          item.discrepancy_factor > 0 ? 'bg-rose-100 text-rose-800 font-bold' : 'bg-slate-100 text-[#253746]'
                        }`}
                        title={`Discrepancy Factor: ${item.discrepancy_factor}/100 (25% weight)`}
                      >
                        Disc: <strong>{item.discrepancy_factor.toFixed(0)}</strong>
                      </span>
                      <span
                        className="bg-slate-100 px-1.5 py-0.5 rounded text-[#253746]"
                        title={`Trust Factor: ${item.trust_factor}/100 (20% weight)`}
                      >
                        Trst: <strong>{item.trust_factor.toFixed(0)}</strong>
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded ${
                          item.overdue_factor > 0 ? 'bg-amber-100 text-amber-800 font-bold' : 'bg-slate-100 text-[#253746]'
                        }`}
                        title={`Overdue Factor: ${item.overdue_factor}/100 (20% weight)`}
                      >
                        Ovd: <strong>{item.overdue_factor.toFixed(0)}</strong>
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-2.5 font-mono font-medium text-[#0D2538]">
                    {item.reference_number}
                  </td>
                  <td className="px-4 py-2.5 text-[#253746] max-w-40 truncate">
                    {item.institution_name || item.institution_id}
                  </td>
                  <td className="px-4 py-2.5 text-[#5D6A75] truncate max-w-36">
                    {item.bank_name}
                  </td>
                  <td className="px-4 py-2.5 font-mono">
                    {item.days_to_maturity <= 0 ? (
                      <span className="text-rose-600 font-bold">
                        Elapsed ({Math.abs(item.days_to_maturity)}d ago)
                      </span>
                    ) : (
                      <span className="text-amber-700">
                        {item.days_to_maturity} days left
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-semibold text-[#0D2538]">
                    {formatINR(item.amount)}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <Link
                      to={`/instruments/${item.instrument_id}`}
                      className="inline-flex items-center gap-1 text-[#123B5D] hover:text-[#0D2538] font-medium"
                    >
                      Review <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
