import type { ApplicationRole } from '@/types';

/**
 * Validates redirect destinations to prevent open-redirect vulnerabilities.
 * Only allows safe, relative internal application paths.
 * Rejects protocol-relative URLs (//evil.com), backslashes, and external schemes.
 */
export function validateRedirectUrl(rawUrl: unknown, defaultUrl: string = '/dashboard'): string {
  if (typeof rawUrl !== 'string' || !rawUrl.trim()) {
    return defaultUrl;
  }

  const trimmed = rawUrl.trim();

  // Must begin with a single slash, not double-slash (protocol-relative), and contain no backslashes
  if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('\\')) {
    return defaultUrl;
  }

  // Prevent looping back to authentication or public landing page if intending an internal route
  if (trimmed === '/login' || trimmed === '/logout' || trimmed === '/') {
    return defaultUrl;
  }

  // Ensure no dangerous characters or protocols embedded
  const cleanPath = trimmed.split('?')[0].split('#')[0];
  if (cleanPath.includes(':') || cleanPath.includes('@')) {
    return defaultUrl;
  }

  return trimmed;
}

/**
 * Role-based route authorization map.
 * Defines which roles are permitted to access each route.
 * Canonical Source of Truth: RBAC.md
 */
const ROUTE_ROLE_PERMISSIONS: Array<{ pattern: RegExp; allowedRoles: ApplicationRole[] }> = [
  {
    pattern: /^\/users(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN'],
  },
  {
    pattern: /^\/audit(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'AUDITOR', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY'],
  },
  {
    pattern: /^\/command-center(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY'],
  },
  {
    pattern: /^\/findings(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY', 'FINANCE_OFFICER', 'AUDITOR'],
  },
  {
    pattern: /^\/verification(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY', 'FINANCE_OFFICER', 'AUDITOR'],
  },
  {
    pattern: /^\/institutions(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY', 'FINANCE_OFFICER', 'AUDITOR'],
  },
  {
    pattern: /^\/reports(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY', 'FINANCE_OFFICER', 'AUDITOR'],
  },
  {
    pattern: /^\/health(\/.*)?$/,
    allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'AUDITOR'],
  },
  {
    pattern: /^\/change-password$/,
    allowedRoles: [
      'SYSTEM_ADMIN',
      'SCRUTINY_OFFICER',
      'BRANCH_HEAD',
      'COMPETENT_AUTHORITY',
      'FINANCE_OFFICER',
      'INSTITUTION_USER',
      'AUDITOR',
    ],
  },
];

/**
 * Checks if a specific internal route is authorized for a user's assigned role.
 */
export function isRouteAuthorizedForRole(pathname: string, role?: ApplicationRole): boolean {
  if (!role) return false;

  const cleanPath = pathname.split('?')[0].split('#')[0];

  for (const rule of ROUTE_ROLE_PERMISSIONS) {
    if (rule.pattern.test(cleanPath)) {
      return rule.allowedRoles.includes(role);
    }
  }

  // All other authenticated routes are permitted by default for authenticated users
  return true;
}

/**
 * Returns the default dashboard destination for a given regulatory role.
 */
export function getDefaultDashboardRoute(_role?: ApplicationRole): string {
  return '/dashboard';
}

/**
 * Determines the safest and authorized post-login destination.
 * Validates the requested destination against open-redirects and role permissions.
 */
export function getSafePostLoginRedirect(
  requestedPath: unknown,
  role?: ApplicationRole
): string {
  const safePath = validateRedirectUrl(requestedPath, '/dashboard');

  if (role && !isRouteAuthorizedForRole(safePath, role)) {
    return getDefaultDashboardRoute(role);
  }

  return safePath;
}

/**
 * Role-level capability helpers aligning with authoritative backend RBAC policies.
 * Ensures consistent frontend visibility boundaries without ad-hoc checks.
 */

/**
 * Only INSTITUTION_USER (depositing/pledging for institution) and SYSTEM_ADMIN (bureau admin)
 * are authorized to create or register new FDR certificates.
 * Regulatory officers (SCRUTINY_OFFICER, BRANCH_HEAD, etc.) review and verify; they do not create deposits.
 */
export function canCreateInstrument(role?: ApplicationRole): boolean {
  if (!role) return false;
  return role === 'INSTITUTION_USER' || role === 'SYSTEM_ADMIN';
}

/**
 * Authorized roles for uploading FDR documents and evidence files.
 * Read-only auditors (AUDITOR) and non-evidence roles are excluded.
 */
export function canUploadDocument(role?: ApplicationRole): boolean {
  if (!role) return false;
  return ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'INSTITUTION_USER'].includes(role);
}

/**
 * Authorized roles for creating new release or refund requests.
 * Initiated by INSTITUTION_USER or bureau SYSTEM_ADMIN.
 */
export function canCreateReleaseRequest(role?: ApplicationRole): boolean {
  if (!role) return false;
  return role === 'INSTITUTION_USER' || role === 'SYSTEM_ADMIN';
}

/**
 * Authorized roles for sanctioning/approving statutory release petitions.
 * Strictly exclusive to COMPETENT_AUTHORITY.
 */
export function canApproveRelease(role?: ApplicationRole): boolean {
  if (!role) return false;
  return role === 'COMPETENT_AUTHORITY';
}

/**
 * Authorized roles for recording official release discharge orders.
 * Strictly restricted to FINANCE_OFFICER per Prompt 2 backend enforcement.
 */
export function canRecordReleaseOrder(role?: ApplicationRole): boolean {
  if (!role) return false;
  return role === 'FINANCE_OFFICER';
}

/**
 * Returns true if role is strictly read-only auditor.
 */
export function isAuditorRole(role?: ApplicationRole): boolean {
  return role === 'AUDITOR';
}

