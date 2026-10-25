import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { authApi } from '@/api/endpoints';
import { Button } from '@/components/common/Button';
import { KeyRound, Lock, AlertCircle, CheckCircle } from 'lucide-react';

export const ChangePasswordPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('All fields are mandatory.');
      return;
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    if (currentPassword === newPassword) {
      setError('New password cannot be identical to your current temporary password.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      });
      setSuccess(true);
      await refreshUser();
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 1500);
    } catch (err: any) {
      setError(err?.message || 'Password update failed. Please check your current password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-[10px] bg-amber-600 text-white shadow-md shadow-amber-900/20 mb-3">
          <KeyRound className="w-7 h-7 text-amber-100" />
        </div>
        <h2 className="text-2xl font-extrabold text-[#0D2538] tracking-tight">
          Password Rotation Required
        </h2>
        <p className="text-xs text-[#5D6A75] mt-1">
          {user?.must_change_password
            ? 'Your account was provisioned with a temporary password. You must set a permanent secure password to continue.'
            : 'Update your security credentials for SakshyaTrail regulatory access.'}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-sm border border-[#C9D3DB]/80 rounded-[10px]">
          {success ? (
            <div className="p-6 text-center space-y-3">
              <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-[#0D2538]">Password Changed Successfully</h3>
              <p className="text-xs text-[#5D6A75]">
                Your credentials have been securely updated with Argon2 encryption. Redirecting to your dashboard...
              </p>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && (
                <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-[10px] flex items-start gap-2.5 text-xs text-rose-700">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-[#253746] uppercase tracking-wider mb-1.5">
                  Current / Temporary Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-3 py-2 text-sm border border-[#8799A9] rounded-[10px] focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#253746] uppercase tracking-wider mb-1.5">
                  New Secure Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full pl-10 pr-3 py-2 text-sm border border-[#8799A9] rounded-[10px] focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#253746] uppercase tracking-wider mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    className="w-full pl-10 pr-3 py-2 text-sm border border-[#8799A9] rounded-[10px] focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  />
                </div>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  size="lg"
                  disabled={isLoading}
                  className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2.5 rounded-[10px] shadow-sm"
                >
                  {isLoading ? 'Updating Credentials...' : 'Save New Password & Continue'}
                </Button>
              </div>

              <div className="text-center pt-3 border-t border-slate-100 mt-4">
                <button
                  type="button"
                  onClick={() => {
                    sessionStorage.setItem('dismiss_password_rotation', 'true');
                    navigate('/', { replace: true });
                  }}
                  className="text-xs text-[#5D6A75] hover:text-[#253746] underline font-medium transition-colors"
                >
                  Remind me later & Return to Dashboard →
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
