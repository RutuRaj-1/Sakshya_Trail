import React from 'react';
import { OperationalReportsWorkspace } from '@/features/commandCenter/components/OperationalReportsWorkspace';

export const ReportsPage: React.FC = () => {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <OperationalReportsWorkspace />
    </div>
  );
};
