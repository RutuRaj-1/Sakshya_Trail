import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Instrument, TrustLevel, MaturityIndicator } from '@/types';
import { Badge } from '@/components/common/Badge';
import { formatINR, formatDate } from '@/lib/utils';
import {
  Building2,
  Calendar,
  Eye,
  EyeOff,
  Shield,
  Clock,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

interface Props {
  instruments: Instrument[];
  isLoading: boolean;
}

export const InstrumentsList: React.FC<Props> = ({ instruments, isLoading }) => {
  const navigate = useNavigate();
  const [maskReferences, setMaskReferences] = useState(false);

  const getTrustBadge = (trust: TrustLevel | string) => {
    switch (trust) {
      case 'L3_BANK_CONFIRMED':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-200">
            <Shield className="w-3 h-3 text-purple-700" />
            <span>L3 — Bank Confirmed</span>
          </span>
        );
      case 'L2_OFFICER_VERIFIED':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200">
            <Shield className="w-3 h-3 text-emerald-700" />
            <span>L2 — Officer Verified</span>
          </span>
        );
      case 'L1_DOCUMENT_CONSISTENT':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">
            <Shield className="w-3 h-3 text-blue-700" />
            <span>L1 — Doc Consistent</span>
          </span>
        );
      case 'L0_DECLARED':
      default:
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200">
            <Shield className="w-3 h-3 text-purple-600" />
            <span>L0 — Declared</span>
          </span>
        );
    }
  };

  const getMaturityBadge = (indicator: MaturityIndicator | string) => {
    switch (indicator) {
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-200">
            <AlertTriangle className="w-3 h-3 text-rose-600" />
            <span>Expired Term</span>
          </span>
        );
      case 'EXPIRING_SOON':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
            <Clock className="w-3 h-3 text-amber-600" />
            <span>Expiring &lt;90d</span>
          </span>
        );
      case 'ACTIVE':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Active Term</span>
          </span>
        );
    }
  };

  const maskRef = (ref: string) => {
    if (!maskReferences) return ref;
    if (ref.length <= 6) return '••••••';
    return `${ref.slice(0, 3)}••••${ref.slice(-4)}`;
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-[8px] border border-[#C9D3DB] p-12 text-center text-[#5D6A75] shadow-xs">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#C9D3DB] border-t-sentinel-600 mb-3" />
        <p className="text-sm font-medium">Loading security deposit registry records...</p>
      </div>
    );
  }

  if (instruments.length === 0) {
    return (
      <div className="bg-white rounded-[8px] border border-[#C9D3DB] p-12 text-center shadow-xs">
        <Shield className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-[#253746]">No Instruments Listed</h3>
        <p className="text-xs text-[#5D6A75] max-w-sm mx-auto mt-1">
          No security deposit FDR certificates match the current filters or authorized scope.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-[8px] border border-[#C9D3DB] overflow-hidden shadow-xs">
      {/* Table Subtoolbar */}
      <div className="px-4 py-2.5 bg-[#F5F4EF]/80 border-b border-[#C9D3DB] flex items-center justify-between text-xs text-[#5D6A75]">
        <span className="font-semibold text-[#253746]">
          Showing {instruments.length} Statutory Instrument Records
        </span>
        <button
          onClick={() => setMaskReferences(!maskReferences)}
          className="inline-flex items-center gap-1 text-[11px] text-[#5D6A75] hover:text-[#0D2538] font-medium px-2 py-1 rounded hover:bg-slate-200/60 transition-colors"
        >
          {maskReferences ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
          <span>{maskReferences ? 'Reveal References' : 'Mask References'}</span>
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-[#253746]">
          <thead className="bg-[#F5F4EF] border-b border-[#C9D3DB] uppercase font-semibold text-[#5D6A75] tracking-wider">
            <tr>
              <th className="py-3 px-4">Receipt Ref / Bank</th>
              <th className="py-3 px-4">Institution Entity</th>
              <th className="py-3 px-4">Deposit Principal</th>
              <th className="py-3 px-4">Term Dates</th>
              <th className="py-3 px-4">Maturity Window</th>
              <th className="py-3 px-4">Administrative Status</th>
              <th className="py-3 px-4">Trust Level</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {instruments.map((inst) => (
              <tr key={inst.id} className="hover:bg-[#F5F4EF]/70 transition-colors">
                {/* Ref & Bank */}
                <td className="py-3 px-4">
                  <div className="font-mono font-bold text-[#0D2538] text-xs">
                    {maskRef(inst.reference_number)}
                  </div>
                  <div className="text-[11px] text-[#5D6A75] flex items-center gap-1 mt-0.5">
                    <Building2 className="w-3 h-3 text-slate-400" />
                    <span>
                      {inst.bank_name} {inst.branch ? `· ${inst.branch}` : ''}
                    </span>
                  </div>
                </td>

                {/* Institution */}
                <td className="py-3 px-4">
                  <div className="font-medium text-[#253746]">
                    {inst.institution_name || 'AICTE Regulated Entity'}
                  </div>
                  {inst.institution_code && (
                    <div className="font-mono text-[10px] text-[#123B5D] font-semibold">
                      {inst.institution_code}
                    </div>
                  )}
                </td>

                {/* Amount */}
                <td className="py-3 px-4 font-bold text-[#0D2538] font-mono text-xs">
                  {formatINR(Number(inst.amount))}
                </td>

                {/* Term Dates */}
                <td className="py-3 px-4 font-mono text-[11px] text-[#5D6A75]">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    <span>Mat: {formatDate(inst.maturity_date)}</span>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Iss: {formatDate(inst.issue_date)}
                  </div>
                </td>

                {/* Concept 3: Derived Maturity Window */}
                <td className="py-3 px-4">
                  {getMaturityBadge(inst.maturity_indicator)}
                </td>

                {/* Concept 1: Administrative Status */}
                <td className="py-3 px-4">
                  <Badge variant={inst.status === 'REGISTERED' ? 'info' : 'default'}>
                    {inst.status}
                  </Badge>
                </td>

                {/* Concept 2: Trust Level */}
                <td className="py-3 px-4">
                  {getTrustBadge(inst.trust_level)}
                </td>

                {/* Actions */}
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => navigate(`/instruments/${inst.id}`)}
                    className="p-1.5 text-[#5D6A75] hover:text-[#123B5D] hover:bg-[#EEF6FA] rounded-lg transition-colors inline-flex items-center gap-1 font-semibold"
                    title="View Full Instrument Profile"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Details</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
