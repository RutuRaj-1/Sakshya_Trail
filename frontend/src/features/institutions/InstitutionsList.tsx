import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Institution } from '@/types';
import { Badge } from '@/components/common/Badge';
import { Building2, Mail, MapPin, Phone, Eye, Edit2, ShieldAlert } from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';

interface Props {
  institutions: Institution[];
  isLoading: boolean;
  onEdit?: (institution: Institution) => void;
  onStatusToggle?: (institution: Institution) => void;
}

export const InstitutionsList: React.FC<Props> = ({
  institutions,
  isLoading,
  onEdit,
  onStatusToggle,
}) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 shadow-xs">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
        <p className="text-sm font-medium">Loading verified institutions from regulatory registry...</p>
      </div>
    );
  }

  if (institutions.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
        <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">No Institutions Listed</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
          No institutions match the current search filters or authorized institutional scope.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-700">
          <thead className="bg-slate-50 border-b border-slate-200 uppercase font-semibold text-slate-500 tracking-wider">
            <tr>
              <th className="py-3 px-4">Permanent Code</th>
              <th className="py-3 px-4">Institution Name</th>
              <th className="py-3 px-4">State / Office</th>
              <th className="py-3 px-4">Classification</th>
              <th className="py-3 px-4">Official Contact</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {institutions.map((inst) => {
              const isActive = inst.is_active;
              const isOwnInstitution = isInstitutionUser && user?.institution_id === inst.id;

              return (
                <tr
                  key={inst.id}
                  className={`hover:bg-slate-50/70 transition-colors ${
                    !isActive ? 'bg-slate-50/40 text-slate-400' : ''
                  }`}
                >
                  <td className="py-3 px-4 font-mono font-medium text-sentinel-700">
                    {inst.code || inst.aicte_id}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900">
                      {inst.legal_name || inst.name}
                    </div>
                    {inst.display_name && inst.display_name !== inst.legal_name && (
                      <div className="text-[11px] text-slate-400 font-sans">
                        aka {inst.display_name}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>{inst.city ? `${inst.city}, ${inst.state}` : inst.state}</span>
                    </div>
                    {inst.assigned_office && (
                      <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
                        {inst.assigned_office}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px]">
                      {inst.institution_type || inst.category}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1 text-slate-600">
                        <Mail className="w-3 h-3 text-slate-400 shrink-0" />
                        <span className="truncate max-w-[140px]">{inst.contact_email}</span>
                      </div>
                      {inst.contact_phone && (
                        <div className="flex items-center gap-1 text-slate-400 text-[11px]">
                          <Phone className="w-3 h-3 text-slate-400 shrink-0" />
                          <span>{inst.contact_phone}</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={isActive ? 'success' : 'default'}>
                      {isActive ? 'ACTIVE' : 'INACTIVE'}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => navigate(`/institutions/${inst.id}`)}
                        title="View Full Profile"
                        className="p-1.5 text-slate-600 hover:text-sentinel-700 hover:bg-sentinel-50 rounded-lg transition-colors flex items-center gap-1 font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Details</span>
                      </button>

                      {(isSystemAdmin || isOwnInstitution) && onEdit && (
                        <button
                          onClick={() => onEdit(inst)}
                          title="Edit Details"
                          className="p-1.5 text-slate-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {isSystemAdmin && onStatusToggle && (
                        <button
                          onClick={() => onStatusToggle(inst)}
                          title={isActive ? 'Deactivate Institution' : 'Activate Institution'}
                          className={`p-1.5 rounded-lg transition-colors ${
                            isActive
                              ? 'text-amber-600 hover:text-amber-800 hover:bg-amber-50'
                              : 'text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50'
                          }`}
                        >
                          <ShieldAlert className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
