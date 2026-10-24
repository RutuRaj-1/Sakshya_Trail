import React from 'react';
import type { Institution } from '@/types';
import { Badge } from '@/components/common/Badge';
import { Building2, Mail, MapPin } from 'lucide-react';

interface Props {
  institutions: Institution[];
  isLoading: boolean;
}

export const InstitutionsList: React.FC<Props> = ({ institutions, isLoading }) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
        <p className="text-sm">Loading registered institutions...</p>
      </div>
    );
  }

  if (institutions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">No Institutions Listed</h3>
        <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1">
          No higher education institutions are registered under this view.
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
              <th className="py-3 px-4">Permanent AICTE ID</th>
              <th className="py-3 px-4">Institution Name</th>
              <th className="py-3 px-4">State / Region</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Contact</th>
              <th className="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {institutions.map((inst) => (
              <tr key={inst.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3.5 px-4 font-mono font-medium text-xs text-sentinel-700">
                  {inst.aicte_id}
                </td>
                <td className="py-3.5 px-4 font-medium text-slate-900">
                  {inst.name}
                </td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-1.5 text-xs text-slate-600">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {inst.state}
                  </div>
                </td>
                <td className="py-3.5 px-4 text-xs text-slate-600">
                  {inst.category}
                </td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-1.5 text-xs text-slate-600">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    {inst.contact_email}
                  </div>
                </td>
                <td className="py-3.5 px-4">
                  <Badge variant={inst.status === 'ACTIVE' ? 'success' : 'default'}>
                    {inst.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
