import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/components/common/Button';
import { Lock, Mail, AlertCircle, Eye, EyeOff, ShieldCheck, ArrowLeft } from 'lucide-react';
import { getSafePostLoginRedirect, getDefaultDashboardRoute } from '@/features/auth/authUtils';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, user, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailTouched, setEmailTouched] = useState(false);

  // If already authenticated, redirect immediately to the user's dashboard
  useEffect(() => {
    if (!isAuthLoading && isAuthenticated && user) {
      navigate(getDefaultDashboardRoute(user.role), { replace: true });
    }
  }, [isAuthenticated, user, isAuthLoading, navigate]);

  const rawFrom = (location.state as any)?.from?.pathname;

  const isEmailValid = (val: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prevent duplicate in-flight submissions
    if (isLoading) return;

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError('Please provide both your official regulatory email and password.');
      return;
    }

    if (!isEmailValid(trimmedEmail)) {
      setError('Please enter a valid official email address format (e.g. name@aicte-india.org).');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const authenticatedUser = await login(trimmedEmail, password);

      // Handle provisioned accounts requiring password rotation
      if (authenticatedUser.must_change_password) {
        navigate('/change-password', { replace: true });
      } else {
        const destination = getSafePostLoginRedirect(rawFrom, authenticatedUser.role);
        navigate(destination, { replace: true });
      }
    } catch (err: any) {
      const status = err?.status;
      if (status === 0 || err?.message?.includes('Network') || err?.message?.includes('Failed to fetch')) {
        setError(
          'Unable to connect to the SakshyaTrail authentication service. Please verify your network connection and ensure the backend service is operational.'
        );
      } else if (status === 401) {
        setError(
          'Authentication failed. The official email address or password provided is incorrect. Please verify your credentials and try again.'
        );
      } else if (status === 403) {
        setError(
          err?.message ||
            'Access restricted: Your regulatory account is inactive or has been disabled by a system administrator.'
        );
      } else {
        setError(err?.message || 'Authentication failed. Please verify your credentials and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemoAccount = (demoEmail: string, demoPw: string) => {
    setEmail(demoEmail);
    setPassword(demoPw);
    setError(null);
    setEmailTouched(true);
  };

  return (
    <div className="min-h-screen bg-[#F4F7FA] text-[#243447] flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans selection:bg-teal-500 selection:text-white">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link
          to="/"
          className="inline-flex items-center gap-2 group focus:outline-none focus:ring-2 focus:ring-[#0D9488] rounded-xl p-1 mb-2"
          title="Return to SakshyaTrail Landing Page"
        >
          <img
            src="/logo.png"
            alt="SakshyaTrail"
            className="h-16 w-auto mx-auto object-contain transition-transform group-hover:scale-105 drop-shadow-sm"
          />
        </Link>
        <h1 className="text-2xl font-extrabold text-[#0B253A] tracking-tight">
          Welcome Back
        </h1>
        <p className="text-xs text-[#607080] mt-1 max-w-sm mx-auto">
          Sign in to the SakshyaTrail Security Deposit & FDR Lifecycle Integrity Platform.
        </p>
      </div>

      {/* Main Authentication Card */}
      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-lg shadow-slate-200/50 border border-[#DCE4EB] rounded-2xl relative">
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            {/* Failure Alert */}
            {error && (
              <div
                role="alert"
                className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-[#C62828] animate-in fade-in duration-200"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-bold text-[#0B253A] uppercase tracking-wider mb-1.5"
              >
                Official Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-[#607080] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="username"
                  disabled={isLoading}
                  value={email}
                  onBlur={() => setEmailTouched(true)}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="name@aicte-india.org"
                  className={`w-full pl-10 pr-3 py-2.5 text-sm border rounded-xl focus:outline-none focus:ring-2 bg-white transition-colors ${
                    emailTouched && email && !isEmailValid(email)
                      ? 'border-rose-300 focus:ring-rose-500 text-rose-900'
                      : 'border-[#DCE4EB] focus:ring-[#0D9488] focus:border-[#0D9488] text-[#243447]'
                  }`}
                />
              </div>
              {emailTouched && email && !isEmailValid(email) && (
                <p className="text-[11px] text-rose-600 mt-1">Please enter a valid official email address.</p>
              )}
            </div>

            {/* Password Field with Show/Hide Toggle */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="password"
                  className="block text-xs font-bold text-[#0B253A] uppercase tracking-wider"
                >
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#607080] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  disabled={isLoading}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-10 py-2.5 text-sm border border-[#DCE4EB] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#0D9488] focus:border-[#0D9488] bg-white text-[#243447] transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none p-1 rounded cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit Action */}
            <Button
              type="submit"
              size="lg"
              disabled={isLoading}
              className="w-full bg-[#123C5A] hover:bg-[#0B253A] text-white font-bold py-2.5 rounded-xl shadow-md shadow-[#123C5A]/20 transition-all cursor-pointer mt-2"
            >
              {isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Verifying Session...</span>
                </div>
              ) : (
                'Sign In to SakshyaTrail'
              )}
            </Button>
          </form>

          {/* Public Return Link */}
          <div className="text-center mt-5 pt-4 border-t border-slate-100">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-xs text-[#607080] hover:text-[#0D9488] transition-colors font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Return to Public Landing Page
            </Link>
          </div>

          {/* Development & Evaluator Accounts Strip */}
          <div className="mt-6 pt-5 border-t border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                SIH Evaluator Demo Accounts
              </span>
              <span className="text-[10px] text-slate-400 font-mono">One-Click Autofill</span>
            </div>
            <p className="text-[11px] text-[#607080] mb-3 leading-tight">
              Select any regulatory role below to autofill synthetic test credentials for prototype evaluation:
            </p>

            <div className="grid grid-cols-2 gap-1.5 text-xs">
              {/* 1. Admin */}
              <button
                type="button"
                onClick={() => fillDemoAccount('admin@aicte-india.org', 'AdminPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group"
              >
                <div className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                  System Admin
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate">admin@aicte-india.org</div>
              </button>

              {/* 2. Scrutiny Officer */}
              <button
                type="button"
                onClick={() => fillDemoAccount('scrutiny.verma@aicte-india.org', 'OfficerPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group"
              >
                <div className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                  Scrutiny Officer
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate">scrutiny.verma@aicte...</div>
              </button>

              {/* 3. Branch Head */}
              <button
                type="button"
                onClick={() => fillDemoAccount('branch.head.north@aicte-india.org', 'BranchPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group"
              >
                <div className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                  Branch Head
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate">branch.head.north@...</div>
              </button>

              {/* 4. Competent Authority */}
              <button
                type="button"
                onClick={() => fillDemoAccount('authority.member@aicte-india.org', 'AuthorityPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group"
              >
                <div className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                  Competent Authority
                </div>
                <div className="text-[10px] text-purple-700 font-mono truncate">authority.member@...</div>
              </button>

              {/* 5. Finance Officer */}
              <button
                type="button"
                onClick={() => fillDemoAccount('finance.officer@aicte-india.org', 'FinancePassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group"
              >
                <div className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                  Finance Officer
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate">finance.officer@...</div>
              </button>

              {/* 6. Compliance Auditor */}
              <button
                type="button"
                onClick={() => fillDemoAccount('auditor.compliance@aicte-india.org', 'AuditorPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group"
              >
                <div className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                  Compliance Auditor
                </div>
                <div className="text-[10px] text-amber-700 font-mono truncate">auditor.compliance@...</div>
              </button>

              {/* 7. Institution User (Active) */}
              <button
                type="button"
                onClick={() => fillDemoAccount('nodal.pune@mims-demo.ac.in', 'NodalPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:border-teal-400 hover:bg-teal-50/40 transition-colors cursor-pointer group col-span-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#0B253A] group-hover:text-teal-900 text-[11px]">
                    Institution User (Nodal Officer)
                  </span>
                  <span className="text-[9px] bg-slate-100 text-slate-600 px-1 py-0.5 rounded font-mono">
                    MIMS Pune
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 font-mono truncate">nodal.pune@mims-demo.ac.in</div>
              </button>
            </div>
          </div>
        </div>

        {/* Regulatory Security Notice */}
        <div className="mt-6 text-center space-y-1">
          <p className="text-[11px] text-[#607080] flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#0D9488]" />
            Strictly authorized access. All sessions are signed & SHA-256 hash-chain audited.
          </p>
          <p className="text-[10px] text-slate-400 font-mono">
            Smart India Hackathon 2026 · Problem Statement ID: 26265
          </p>
        </div>
      </div>
    </div>
  );
};
