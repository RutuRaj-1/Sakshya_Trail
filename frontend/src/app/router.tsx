import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { DashboardPage } from '@/app/routes/DashboardPage';
import { InstrumentsPage } from '@/app/routes/InstrumentsPage';
import { InstitutionsPage } from '@/app/routes/InstitutionsPage';
import { HealthPage } from '@/app/routes/HealthPage';
import { AuditPage } from '@/app/routes/AuditPage';
import { LoginPage } from '@/app/routes/LoginPage';
import { ChangePasswordPage } from '@/app/routes/ChangePasswordPage';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/change-password',
    element: (
      <ProtectedRoute>
        <ChangePasswordPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
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
        element: (
          <ProtectedRoute allowedRoles={['SYSTEM_ADMIN', 'AUDITOR', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY']}>
            <AuditPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
