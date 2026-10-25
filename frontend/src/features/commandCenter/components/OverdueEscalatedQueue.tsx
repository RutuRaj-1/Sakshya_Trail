import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Flame, Building, UserCheck } from 'lucide-react';
import type { OverdueEscalatedResponse } from '@/types/commandCenter';
import { Badge } from '@/components/common/Badge';

interface OverdueEscalatedQueueProps {
  data: OverdueEscalatedResponse | null;
  isLoading: boolean;
  isInstitutionUser?: boolean;
}

export const OverdueEscalatedQueue: React.FC<OverdueEscalatedQueueProps> = ({
  data,
  isLoading,
  isInstitutionUser = false,
}) => {
  return (
    <div className="bg-white rounded-[8px] border border-[#C9D3DB] shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-[#F5F4EF]/50">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-rose-600" />
          <h3 className="font-semibold text-[#0D2538] text-sm">
            Overdue & Escalated Work Items
          </h3>
          <span className="text-[10px] font-mono text-[#5D6A75] bg-slate-200/80 px-1.5 py-0.5 rounded">
            PRD-FR-070c
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="danger">{data?.total_overdue ?? 0} Overdue</Badge>
          <Badge variant="warning">{data?.total_escalated ?? 0} Escalated</Badge>
        </div>
      </div>

      {/* Office Workload Distribution (when authorized) */}
      {!isInstitutionUser && data && Object.keys(data.by_office).length > 0 && (
        <div className="px-4 py-2.5 bg-[#F5F4EF] border-b border-slate-100 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[#5D6A75] font-medium">Office Breakdown:</span>
          {Object.entries(data.by_office).map(([office, count]) => (
            <span
              key={office}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white border border-[#C9D3DB] text-[#253746] font-mono text-[11px]"
            >
              <Building className="w-3 h-3 text-slate-400" />
              {office}: <strong>{count}</strong>
            </span>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto max-h-80">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#F5F4EF] text-[#5D6A75] font-semibold border-b border-[#C9D3DB] sticky top-0">
            <tr>
              <th className="px-4 py-2.5">Record Type</th>
              <th className="px-4 py-2.5">Identifier / Reference</th>
              <th className="px-4 py-2.5">Institution</th>
              <th className="px-4 py-2.5">Assigned Office</th>
              {!isInstitutionUser && <th className="px-4 py-2.5">Assignee</th>}
              <th className="px-4 py-2.5">Due Date</th>
              <th className="px-4 py-2.5">Overdue Age</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5 text-right">Route</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {isLoading ? (
              <tr>
                <td colSpan={isInstitutionUser ? 8 : 9} className="p-8 text-center text-slate-400">
                  Loading overdue and escalated items...
                </td>
              </tr>
            ) : !data || data.records.length === 0 ? (
              <tr>
                <td colSpan={isInstitutionUser ? 8 : 9} className="p-8 text-center text-slate-400">
                  ✅ No overdue compliance actions or escalated cases in scope.
                </td>
              </tr>
            ) : (
              data.records.map((item) => {
                const routeUrl =
                  item.record_type === 'RELEASE_CASE'
                    ? `/release/${item.record_id}`
                    : `/instruments/${item.record_id}`;

                return (
                  <tr key={`${item.record_type}-${item.record_id}`} className="hover:bg-[#F5F4EF]/80 transition-colors">
                    <td className="px-4 py-2.5">
                      <span className="font-mono text-[10px] uppercase font-bold text-[#253746] bg-slate-100 px-1.5 py-0.5 rounded">
                        {item.record_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono font-medium text-[#0D2538]">
                      {item.reference_number}
                    </td>
                    <td className="px-4 py-2.5 text-[#253746] max-w-40 truncate">
                      {item.institution_name || item.institution_id}
                    </td>
                    <td className="px-4 py-2.5 text-[#5D6A75]">
                      {item.assigned_office ? (
                        <span className="font-mono text-[11px]">{item.assigned_office}</span>
                      ) : (
                        <span className="text-slate-400 italic">Unavailable</span>
                      )}
                    </td>
                    {!isInstitutionUser && (
                      <td className="px-4 py-2.5 text-[#5D6A75]">
                        {item.assignee_name ? (
                          <div className="flex items-center gap-1 text-[11px]">
                            <UserCheck className="w-3 h-3 text-slate-400" />
                            <span>{item.assignee_name}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned</span>
                        )}
                      </td>
                    )}
                    <td className="px-4 py-2.5 font-mono text-[#5D6A75]">
                      {item.due_date || 'N/A'}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-800">
                        +{item.days_overdue} days
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      {item.is_escalated ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">
                          <Flame className="w-3 h-3" />
                          Escalated ({item.escalation_role || 'Higher Office'})
                        </span>
                      ) : (
                        <span className="text-[#5D6A75] text-xs">{item.due_condition}</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Link
                        to={routeUrl}
                        className="inline-flex items-center gap-1 text-[#123B5D] hover:text-[#0D2538] font-medium"
                      >
                        Open <ArrowUpRight className="w-3 h-3" />
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
