import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/components/common/Button';
import { ShieldCheck, Lock, Mail, AlertCircle } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rawFrom = (location.state as any)?.from?.pathname;
  const from = (!rawFrom || rawFrom === '/') ? '/dashboard' : rawFrom;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide both your official email and password.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const user = await login(email, password);
      if (user.must_change_password) {
        navigate('/change-password', { replace: true });
      } else {
        navigate(from, { replace: true });
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemoAccount = (demoEmail: string, demoPw: string) => {
    setEmail(demoEmail);
    setPassword(demoPw);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-sentinel-700 text-white shadow-md shadow-sentinel-900/20 mb-3">
          <ShieldCheck className="w-7 h-7 text-sentinel-200" />
        </div>
        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Sakshya<span className="text-teal-600">Trail</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Security Deposit & FDR Lifecycle Integrity Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-sm border border-slate-200/80 rounded-2xl">
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-700">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Official Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@aicte-india.org"
                  className="w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-sentinel-600 focus:border-sentinel-600 bg-white"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-3 py-2.5 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-sentinel-600 focus:border-sentinel-600 bg-white"
                />
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              disabled={isLoading}
              className="w-full bg-sentinel-700 hover:bg-sentinel-800 text-white font-semibold py-2.5 rounded-xl shadow-sm"
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Verifying Session...</span>
                </div>
              ) : (
                'Sign In to SakshyaTrail'
              )}
            </Button>
          </form>

          <div className="text-center mt-4">
            <Link to="/" className="text-xs text-slate-500 hover:text-teal-700 transition-colors font-medium">
              ← Return to Public Landing Page
            </Link>
          </div>

          {/* Quick Demo Credentials Panel */}
          <div className="mt-8 pt-6 border-t border-slate-100">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 text-center mb-3">
              One-Click Evaluator Demo Accounts
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => fillDemoAccount('admin@aicte-india.org', 'AdminPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition-colors"
              >
                <div className="font-semibold text-slate-800">System Admin</div>
                <div className="text-[10px] text-slate-500 font-mono">admin@aicte...</div>
              </button>

              <button
                type="button"
                onClick={() => fillDemoAccount('scrutiny.verma@aicte-india.org', 'OfficerPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition-colors"
              >
                <div className="font-semibold text-slate-800">Scrutiny Officer</div>
                <div className="text-[10px] text-slate-500 font-mono">scrutiny...</div>
              </button>

              <button
                type="button"
                onClick={() => fillDemoAccount('nodal@diet-delhi.ac.in', 'NodalPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition-colors"
              >
                <div className="font-semibold text-slate-800">Institution User</div>
                <div className="text-[10px] text-amber-600 font-medium">Must rotate PW</div>
              </button>

              <button
                type="button"
                onClick={() => fillDemoAccount('auditor.compliance@aicte-india.org', 'AuditorPassword@2026')}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-slate-50 transition-colors"
              >
                <div className="font-semibold text-slate-800">Auditor</div>
                <div className="text-[10px] text-slate-500 font-mono">Read-only</div>
              </button>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6 font-mono">
          Session security: Signed JWT · HttpOnly SameSite Cookie · Argon2id Hashes
        </p>
      </div>
    </div>
  );
};
