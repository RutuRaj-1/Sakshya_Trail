import React from 'react';
import { useAuth } from '@/features/auth/AuthContext';
import { InstitutionWorkspace } from '@/features/dashboard/workspaces/InstitutionWorkspace';
import { ScrutinyOfficerWorkspace } from '@/features/dashboard/workspaces/ScrutinyOfficerWorkspace';
import { BranchHeadWorkspace } from '@/features/dashboard/workspaces/BranchHeadWorkspace';
import { CompetentAuthorityWorkspace } from '@/features/dashboard/workspaces/CompetentAuthorityWorkspace';
import { FinanceOfficerWorkspace } from '@/features/dashboard/workspaces/FinanceOfficerWorkspace';
import { AuditorWorkspace } from '@/features/dashboard/workspaces/AuditorWorkspace';
import { SystemAdminWorkspace } from '@/features/dashboard/workspaces/SystemAdminWorkspace';
import { Clock } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-[#5D6A75]">
        <Clock className="w-8 h-8 animate-spin mb-3 text-slate-400" />
        <p className="text-xs font-medium">Loading authorized role workspace...</p>
      </div>
    );
  }

  switch (user?.role) {
    case 'INSTITUTION_USER':
      return <InstitutionWorkspace />;
    case 'SCRUTINY_OFFICER':
      return <ScrutinyOfficerWorkspace />;
    case 'BRANCH_HEAD':
      return <BranchHeadWorkspace />;
    case 'COMPETENT_AUTHORITY':
      return <CompetentAuthorityWorkspace />;
    case 'FINANCE_OFFICER':
      return <FinanceOfficerWorkspace />;
    case 'AUDITOR':
      return <AuditorWorkspace />;
    case 'SYSTEM_ADMIN':
      return <SystemAdminWorkspace />;
    default:
      return <InstitutionWorkspace />;
  }
};
