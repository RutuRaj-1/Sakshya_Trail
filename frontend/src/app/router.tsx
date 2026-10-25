import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { LandingPage } from '@/app/routes/LandingPage';
import { DashboardPage } from '@/app/routes/DashboardPage';
import { CommandCenterPage } from '@/app/routes/CommandCenterPage';
import { InstrumentsPage } from '@/app/routes/InstrumentsPage';
import { InstrumentDetailPage } from '@/app/routes/InstrumentDetailPage';
import { InstitutionsPage } from '@/app/routes/InstitutionsPage';
import { InstitutionDetailPage } from '@/app/routes/InstitutionDetailPage';
import { UserAdminPage } from '@/app/routes/UserAdminPage';
import { HealthPage } from '@/app/routes/HealthPage';
import { AuditPage } from '@/app/routes/AuditPage';
import { ReviewQueuePage } from '@/app/routes/ReviewQueuePage';
import { TrustVerificationDeskPage } from '@/app/routes/TrustVerificationDeskPage';
import { LoginPage } from '@/app/routes/LoginPage';
import { ChangePasswordPage } from '@/app/routes/ChangePasswordPage';
import { ReleaseCasesPage } from '@/app/routes/ReleaseCasesPage';
import { ReleaseDetailPage } from '@/app/routes/ReleaseDetailPage';
import { UnifiedSearchPage } from '@/app/routes/UnifiedSearchPage';
import { ReportsPage } from '@/app/routes/ReportsPage';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
  },
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
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'app',
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'command-center',
        element: <CommandCenterPage />,
      },
      {
        path: 'search',
        element: <UnifiedSearchPage />,
      },
      {
        path: 'reports',
        element: <ReportsPage />,
      },
      {
        path: 'instruments',
        element: <InstrumentsPage />,
      },
      {
        path: 'instruments/:id',
        element: <InstrumentDetailPage />,
      },
      {
        path: 'institutions',
        element: <InstitutionsPage />,
      },
      {
        path: 'institutions/:id',
        element: <InstitutionDetailPage />,
      },
      {
        path: 'release',
        element: <ReleaseCasesPage />,
      },
      {
        path: 'release/:id',
        element: <ReleaseDetailPage />,
      },
      {
        path: 'findings/queue',
        element: <ReviewQueuePage />,
      },
      {
        path: 'verification',
        element: <TrustVerificationDeskPage />,
      },
      {
        path: 'verification/:id',
        element: <TrustVerificationDeskPage />,
      },
      {
        path: 'users',
        element: (
          <ProtectedRoute allowedRoles={['SYSTEM_ADMIN']}>
            <UserAdminPage />
          </ProtectedRoute>
        ),
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
