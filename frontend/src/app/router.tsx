import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { DashboardPage } from '@/app/routes/DashboardPage';
import { InstrumentsPage } from '@/app/routes/InstrumentsPage';
import { InstitutionsPage } from '@/app/routes/InstitutionsPage';
import { HealthPage } from '@/app/routes/HealthPage';
import { AuditPage } from '@/app/routes/AuditPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'instruments',
        element: <InstrumentsPage />,
      },
      {
        path: 'institutions',
        element: <InstitutionsPage />,
      },
      {
        path: 'health',
        element: <HealthPage />,
      },
      {
        path: 'audit',
        element: <AuditPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
