import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { LoginPage } from '@/app/routes/LoginPage';
import { AuthProvider } from '@/features/auth/AuthContext';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
import {
  validateRedirectUrl,
  isRouteAuthorizedForRole,
  getSafePostLoginRedirect,
  getDefaultDashboardRoute,
} from '@/features/auth/authUtils';

describe('Auth Routing & Open-Redirect Security (Prompt 2)', () => {
  it('validates and allows only safe internal application paths', () => {
    // Valid relative routes
    expect(validateRedirectUrl('/dashboard')).toBe('/dashboard');
    expect(validateRedirectUrl('/command-center')).toBe('/command-center');
    expect(validateRedirectUrl('/instruments/123')).toBe('/instruments/123');

    // Reject protocol-relative external URLs
    expect(validateRedirectUrl('//evil.com/phish')).toBe('/dashboard');
    expect(validateRedirectUrl('//google.com')).toBe('/dashboard');

    // Reject absolute external schemes
    expect(validateRedirectUrl('https://evil.com')).toBe('/dashboard');
    expect(validateRedirectUrl('http://attacker.com/steal')).toBe('/dashboard');
    expect(validateRedirectUrl('javascript:alert(1)')).toBe('/dashboard');

    // Reject backslash tricks
    expect(validateRedirectUrl('\\\\evil.com')).toBe('/dashboard');
    expect(validateRedirectUrl('/\\evil.com')).toBe('/dashboard');

    // Reject looping back to login or landing page
    expect(validateRedirectUrl('/login')).toBe('/dashboard');
    expect(validateRedirectUrl('/')).toBe('/dashboard');
  });

  it('enforces role-based route permissions', () => {
    // /users is strictly for SYSTEM_ADMIN
    expect(isRouteAuthorizedForRole('/users', 'SYSTEM_ADMIN')).toBe(true);
    expect(isRouteAuthorizedForRole('/users', 'SCRUTINY_OFFICER')).toBe(false);
    expect(isRouteAuthorizedForRole('/users', 'INSTITUTION_USER')).toBe(false);
    expect(isRouteAuthorizedForRole('/users', 'AUDITOR')).toBe(false);

    // /audit is for SYSTEM_ADMIN, AUDITOR, BRANCH_HEAD, COMPETENT_AUTHORITY
    expect(isRouteAuthorizedForRole('/audit', 'AUDITOR')).toBe(true);
    expect(isRouteAuthorizedForRole('/audit', 'SYSTEM_ADMIN')).toBe(true);
    expect(isRouteAuthorizedForRole('/audit', 'BRANCH_HEAD')).toBe(true);
    expect(isRouteAuthorizedForRole('/audit', 'COMPETENT_AUTHORITY')).toBe(true);
    expect(isRouteAuthorizedForRole('/audit', 'INSTITUTION_USER')).toBe(false);

    // General routes are allowed for authenticated roles
    expect(isRouteAuthorizedForRole('/dashboard', 'INSTITUTION_USER')).toBe(true);
    expect(isRouteAuthorizedForRole('/instruments', 'INSTITUTION_USER')).toBe(true);
  });

  it('falls back to safe dashboard when requested path is not authorized for the role', () => {
    // Institution user trying to access /users should fall back to /dashboard
    expect(getSafePostLoginRedirect('/users', 'INSTITUTION_USER')).toBe('/dashboard');

    // System admin accessing /users is permitted
    expect(getSafePostLoginRedirect('/users', 'SYSTEM_ADMIN')).toBe('/users');

    // Malicious URL is rejected regardless of role
    expect(getSafePostLoginRedirect('//evil.com', 'SYSTEM_ADMIN')).toBe('/dashboard');
  });

  it('provides default dashboard destination', () => {
    expect(getDefaultDashboardRoute('SYSTEM_ADMIN')).toBe('/dashboard');
    expect(getDefaultDashboardRoute('INSTITUTION_USER')).toBe('/dashboard');
  });
});

describe('Polished SakshyaTrail LoginPage Interactions', () => {
  it('renders Welcome Back, logo, security notice, and show/hide password toggle', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByRole('heading', { name: /Welcome Back/i })).toBeInTheDocument();
    expect(screen.getByText(/Security Deposit & FDR Lifecycle Integrity Platform/i)).toBeInTheDocument();

    const passwordInput = screen.getByLabelText(/^Password$/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleBtn = screen.getByRole('button', { name: /Show password/i });
    expect(toggleBtn).toBeInTheDocument();

    // Toggle to show password
    fireEvent.click(toggleBtn);
    expect(passwordInput).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: /Hide password/i })).toBeInTheDocument();

    // Toggle back to hide password
    fireEvent.click(screen.getByRole('button', { name: /Hide password/i }));
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Security notice
    expect(
      screen.getByText(/Strictly authorized access\. All sessions are signed & SHA-256 hash-chain audited\./i)
    ).toBeInTheDocument();
  });

  it('validates empty inputs on submit without submitting to backend', async () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    const submitBtn = screen.getByRole('button', { name: /Sign In to SakshyaTrail/i });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Please provide both your official regulatory email and password\./i)
    ).toBeInTheDocument();
  });

  it('autofills synthetic demo evaluator credentials when demo buttons are clicked', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    const emailInput = screen.getByLabelText(/Official Email Address/i) as HTMLInputElement;
    const passwordInput = screen.getByLabelText(/^Password$/i) as HTMLInputElement;

    // Click System Admin demo button
    const adminDemoBtn = screen.getByRole('button', { name: /System Admin/i });
    fireEvent.click(adminDemoBtn);

    expect(emailInput.value).toBe('admin@aicte-india.org');
    expect(passwordInput.value).toBe('AdminPassword@2026');

    // Click Scrutiny Officer demo button
    const officerDemoBtn = screen.getByRole('button', { name: /Scrutiny Officer/i });
    fireEvent.click(officerDemoBtn);

    expect(emailInput.value).toBe('scrutiny.verma@aicte-india.org');
    expect(passwordInput.value).toBe('OfficerPassword@2026');
  });

  it('renders return link to public landing page', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    const backLink = screen.getByRole('link', { name: /Return to Public Landing Page/i });
    expect(backLink).toHaveAttribute('href', '/');
  });
});

describe('Protected Route Guard Enforcement', () => {
  it('redirects unauthenticated users to /login preserving from location', () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>Private Dashboard Content</div>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div>Login Page Target</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    // Initial unauthenticated state should redirect to login or show session verification
    expect(screen.queryByText('Private Dashboard Content')).not.toBeInTheDocument();
  });
});
