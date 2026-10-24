import React from 'react';
import { Instrument, VerificationLevel, FDRStatus } from '@/types';
import { Badge } from '@/components/common/Badge';
import { formatINR, formatDate } from '@/lib/utils';
import { ShieldCheck, AlertCircle, Building, Calendar, Hash } from 'lucide-react';

interface Props {
  instruments: Instrument[];
  isLoading: boolean;
}

export const InstrumentsList: React.FC<Props> = ({ instruments, isLoading }) => {
  const getVerificationBadge = (level: VerificationLevel) => {
    switch (level) {
      case 'L4_BANK_CONFIRMED':
        return <Badge variant="purple">L4 Bank Confirmed</Badge>;
      case 'L3_OFFICER_VERIFIED':
        return <Badge variant="success">L3 Officer Verified</Badge>;
      case 'L2_DOCUMENT_CONSISTENT':
        return <Badge variant="info">L2 Doc Consistent</Badge>;
      default:
        return <Badge variant="outline">L1 Declared</Badge>;
    }
  };

  const getStatusBadge = (status: FDRStatus) => {
    switch (status) {
      case 'ACTIVE':
      case 'VERIFIED':
        return <Badge variant="success">{status}</Badge>;
      case 'UNDER_SCRUTINY':
      case 'SUBMITTED':
        return <Badge variant="info">{status}</Badge>;
      case 'MATURED':
      case 'RELEASE_REQUESTED':
        return <Badge variant="warning">{status}</Badge>;
      case 'RELEASED':
        return <Badge variant="default">{status}</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
        <p className="text-sm">Loading security deposit registry...</p>
      </div>
    );
  }

  if (instruments.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <ShieldCheck className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">No Instruments Registered</h3>
        <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1">
          No FDR instruments are recorded yet. You can submit initial test FDRs using the backend seed scripts or the submission action.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-700">
          <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase font-semibold text-slate-500 tracking-wider">
            <tr>
              <th className="py-3 px-4">Receipt Ref / Bank</th>
              <th className="py-3 px-4">Principal Amount</th>
              <th className="py-3 px-4">Maturity Date</th>
              <th className="py-3 px-4">Trust Level</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Joint AICTE Lien</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-normal">
            {instruments.map((inst) => (
              <tr key={inst.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3.5 px-4">
                  <div className="font-medium text-slate-900 font-mono text-xs flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-slate-400" />
                    {inst.reference_number}
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    <Building className="w-3 h-3 text-slate-400" />
                    {inst.bank_name} {inst.branch ? `· ${inst.branch}` : ''}
                  </div>
                </td>
                <td className="py-3.5 px-4 font-semibold text-slate-900">
                  {formatINR(inst.amount)}
                </td>
                <td className="py-3.5 px-4">
                  <div className="text-xs text-slate-700 flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    {formatDate(inst.maturity_date)}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Issued: {formatDate(inst.issue_date)}
                  </div>
                </td>
                <td className="py-3.5 px-4">
                  {getVerificationBadge(inst.verification_level)}
                </td>
                <td className="py-3.5 px-4">
                  {getStatusBadge(inst.status)}
                </td>
                <td className="py-3.5 px-4 text-xs">
                  {inst.joint_with_aicte && inst.lien_marked ? (
                    <span className="inline-flex items-center text-emerald-700 font-medium text-xs">
                      <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Lien Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-amber-700 font-medium text-xs">
                      <AlertCircle className="w-3.5 h-3.5 mr-1 text-amber-600" /> Unconfirmed Lien
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
