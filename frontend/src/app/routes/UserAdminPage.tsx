import React, { useState, useEffect, useCallback } from 'react';
import { usersApi, institutionsApi, authApi } from '@/api/endpoints';
import type { User, Institution, RoleInfo } from '@/types';
import { Badge } from '@/components/common/Badge';
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Shield,
  KeyRound,
  ShieldAlert,
  ShieldCheck,
  AlertCircle,
  Copy,
  Check,
  Building2,
  ChevronLeft,
  ChevronRight,
  X,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';

export const UserAdminPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Provisioning Modal State
  const [isProvisionOpen, setIsProvisionOpen] = useState(false);
  const [provisionForm, setProvisionForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'SCRUTINY_OFFICER',
    institution_id: '',
    must_change_password: true,
  });
  const [provisionErrors, setProvisionErrors] = useState<Record<string, string>>({});
  const [isProvisioning, setIsProvisioning] = useState(false);
  const [provisionApiError, setProvisionApiError] = useState<string | null>(null);

  // Reset Password Modal State
  const [resetTargetUser, setResetTargetUser] = useState<User | null>(null);
  const [tempPasswordResult, setTempPasswordResult] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [copied, setCopied] = useState(false);

  // Status Toggle Target
  const [statusToggleTarget, setStatusToggleTarget] = useState<User | null>(null);
  const [isTogglingStatus, setIsTogglingStatus] = useState(false);

  // Load roles & institutions for dropdowns
  useEffect(() => {
    async function loadMeta() {
      try {
        const [rolesData, instsData] = await Promise.all([
          authApi.getRoles(),
          institutionsApi.list({ limit: 100, is_active: true }),
        ]);
        setRoles(rolesData);
        setInstitutions(instsData.items);
      } catch (e) {
        console.error('Failed to load metadata', e);
      }
    }
    loadMeta();
  }, []);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activeParam =
        statusFilter === 'ACTIVE' ? true : statusFilter === 'INACTIVE' ? false : undefined;
      const roleParam = roleFilter !== 'ALL' ? roleFilter : undefined;

      const res = await usersApi.list({
        search: search.trim() || undefined,
        role: roleParam,
        is_active: activeParam,
        skip: (page - 1) * pageSize,
        limit: pageSize,
      });

      setUsers(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || 'Failed to retrieve user accounts.');
    } finally {
      setIsLoading(false);
    }
  }, [search, roleFilter, statusFilter, page]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const validateProvision = (): boolean => {
    const errs: Record<string, string> = {};
    if (!provisionForm.full_name.trim()) {
      errs.full_name = 'Full name is required.';
    }
    if (!provisionForm.email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(provisionForm.email.trim())) {
      errs.email = 'Please enter a valid email address.';
    }
    if (!provisionForm.password || provisionForm.password.length < 8) {
      errs.password = 'Initial password must be at least 8 characters.';
    }
    if (provisionForm.role === 'INSTITUTION_USER' && !provisionForm.institution_id) {
      errs.institution_id = 'Institution association is mandatory for Institution Users.';
    }
    setProvisionErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleProvisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateProvision() || isProvisioning) return;

    setIsProvisioning(true);
    setProvisionApiError(null);

    try {
      await usersApi.provision({
        full_name: provisionForm.full_name.trim(),
        email: provisionForm.email.trim().toLowerCase(),
        password: provisionForm.password,
        role: provisionForm.role,
        institution_id:
          provisionForm.role === 'INSTITUTION_USER' ? provisionForm.institution_id : null,
        must_change_password: provisionForm.must_change_password,
      });
      setIsProvisionOpen(false);
      setProvisionForm({
        full_name: '',
        email: '',
        password: '',
        role: 'SCRUTINY_OFFICER',
        institution_id: '',
        must_change_password: true,
      });
      await loadUsers();
    } catch (err: any) {
      setProvisionApiError(
        err?.response?.data?.message || err?.message || 'Failed to provision user.'
      );
    } finally {
      setIsProvisioning(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resetTargetUser || isResetting) return;
    setIsResetting(true);
    try {
      const res = await usersApi.resetPassword(resetTargetUser.id);
      setTempPasswordResult(res.temporary_password);
      await loadUsers();
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Password reset failed.');
    } finally {
      setIsResetting(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!statusToggleTarget || isTogglingStatus) return;
    setIsTogglingStatus(true);
    try {
      const newStatus = !statusToggleTarget.is_active;
      await usersApi.setStatus(statusToggleTarget.id, newStatus);
      setStatusToggleTarget(null);
      await loadUsers();
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Status change failed.');
    } finally {
      setIsTogglingStatus(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Users className="w-5 h-5 text-sentinel-600" />
            <span>User Administration</span>
          </h1>
          <p className="text-xs text-slate-500">
            Authorized administration and account lifecycle management for AICTE Regulation Bureau personnel
          </p>
        </div>

        <button
          onClick={() => {
            setProvisionApiError(null);
            setProvisionErrors({});
            setIsProvisionOpen(true);
          }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sentinel-600 hover:bg-sentinel-700 text-white font-semibold shadow-xs transition-all"
        >
          <UserPlus className="w-4 h-4" />
          <span>Provision Account</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by full name or email address..."
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white"
            />
          </div>

          {/* Role Filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
            >
              <option value="ALL">All Application Roles</option>
              {roles.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.display_name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as any);
              setPage(1);
            }}
            className="border border-slate-300 rounded-lg px-2.5 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active Users</option>
            <option value="INACTIVE">Deactivated</option>
          </select>
        </div>

        <div className="text-right text-[11px] text-slate-500 self-center">
          Showing <span className="font-semibold text-slate-800">{users.length}</span> of{' '}
          <span className="font-semibold text-slate-800">{total}</span> users
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 uppercase font-semibold text-slate-500 tracking-wider">
              <tr>
                <th className="py-3 px-4">User Identity</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Scope / Institution</th>
                <th className="py-3 px-4">Account Status</th>
                <th className="py-3 px-4">Security Policy</th>
                <th className="py-3 px-4 text-right">Administrative Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <div className="inline-block animate-spin rounded-full h-7 w-7 border-4 border-slate-200 border-t-sentinel-600 mb-2" />
                    <p>Loading user directories...</p>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    No users match the search criteria.
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const isCurrent = u.id === currentUser?.id;
                  const institutionObj = institutions.find((i) => i.id === u.institution_id);

                  return (
                    <tr
                      key={u.id}
                      className={`hover:bg-slate-50/70 transition-colors ${
                        !u.is_active ? 'bg-slate-50/40 text-slate-400' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                          <span>{u.full_name}</span>
                          {isCurrent && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-sentinel-100 text-sentinel-700 font-mono">
                              You
                            </span>
                          )}
                        </div>
                        <div className="text-slate-500 font-mono text-[11px]">{u.email}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px]">
                          <Shield className="w-3 h-3 text-sentinel-600" />
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        {u.role === 'INSTITUTION_USER' ? (
                          <div className="flex items-center gap-1 text-slate-700">
                            <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate max-w-[180px]">
                              {institutionObj
                                ? institutionObj.legal_name || institutionObj.name
                                : u.institution_id}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic">Internal AICTE Regulatory Bureau</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <Badge variant={u.is_active ? 'success' : 'default'}>
                          {u.is_active ? 'ACTIVE' : 'DEACTIVATED'}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4">
                        {u.must_change_password ? (
                          <span className="inline-flex items-center gap-1 text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded text-[10px] font-medium">
                            <KeyRound className="w-3 h-3" />
                            <span>Rotation Required</span>
                          </span>
                        ) : (
                          <span className="text-emerald-700 text-[11px] flex items-center gap-1">
                            <Check className="w-3.5 h-3.5" />
                            <span>Standard</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Reset Password Action */}
                          <button
                            onClick={() => {
                              setResetTargetUser(u);
                              setTempPasswordResult(null);
                            }}
                            title="Reset Temporary Password"
                            className="p-1.5 text-slate-600 hover:text-sentinel-700 hover:bg-sentinel-50 rounded-lg transition-colors flex items-center gap-1 font-medium"
                          >
                            <KeyRound className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Reset Pwd</span>
                          </button>

                          {/* Status Toggle Action */}
                          <button
                            onClick={() => setStatusToggleTarget(u)}
                            title={u.is_active ? 'Deactivate User' : 'Activate User'}
                            className={`p-1.5 rounded-lg transition-colors ${
                              u.is_active
                                ? 'text-amber-600 hover:text-amber-800 hover:bg-amber-50'
                                : 'text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50'
                            }`}
                          >
                            {u.is_active ? (
                              <ShieldAlert className="w-3.5 h-3.5" />
                            ) : (
                              <ShieldCheck className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl border border-slate-200 text-xs">
          <div className="text-slate-500">
            Page <span className="font-semibold text-slate-800">{page}</span> of{' '}
            <span className="font-semibold text-slate-800">{totalPages}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Provision User Modal */}
      {isProvisionOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-sentinel-100 text-sentinel-700 flex items-center justify-center font-bold">
                  <UserPlus className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">Provision User Account</h3>
                  <p className="text-[11px] text-slate-500">
                    Create authorized personnel credentials with role & institutional boundaries
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsProvisionOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleProvisionSubmit} className="p-6 space-y-3.5 text-xs">
              {provisionApiError && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{provisionApiError}</span>
                </div>
              )}

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={provisionForm.full_name}
                  onChange={(e) =>
                    setProvisionForm({ ...provisionForm, full_name: e.target.value })
                  }
                  placeholder="e.g. Dr. Rajesh Kumar"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white ${
                    provisionErrors.full_name ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {provisionErrors.full_name && (
                  <p className="text-rose-600 mt-0.5">{provisionErrors.full_name}</p>
                )}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Official Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  value={provisionForm.email}
                  onChange={(e) => setProvisionForm({ ...provisionForm, email: e.target.value })}
                  placeholder="rajesh.kumar@aicte-india.org"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white ${
                    provisionErrors.email ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {provisionErrors.email && (
                  <p className="text-rose-600 mt-0.5">{provisionErrors.email}</p>
                )}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Initial Account Password <span className="text-rose-500">*</span>
                </label>
                <input
                  type="password"
                  value={provisionForm.password}
                  onChange={(e) => setProvisionForm({ ...provisionForm, password: e.target.value })}
                  placeholder="Minimum 8 characters (Argon2id hashed)"
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white ${
                    provisionErrors.password ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {provisionErrors.password && (
                  <p className="text-rose-600 mt-0.5">{provisionErrors.password}</p>
                )}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Assigned Application Role <span className="text-rose-500">*</span>
                </label>
                <select
                  value={provisionForm.role}
                  onChange={(e) =>
                    setProvisionForm({ ...provisionForm, role: e.target.value, institution_id: '' })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white"
                >
                  {roles.map((r) => (
                    <option key={r.name} value={r.name}>
                      {r.display_name} ({r.name})
                    </option>
                  ))}
                </select>
              </div>

              {provisionForm.role === 'INSTITUTION_USER' && (
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Institution Association <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={provisionForm.institution_id}
                    onChange={(e) =>
                      setProvisionForm({ ...provisionForm, institution_id: e.target.value })
                    }
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sentinel-500 bg-white ${
                      provisionErrors.institution_id ? 'border-rose-400' : 'border-slate-300'
                    }`}
                  >
                    <option value="">Select registered institution...</option>
                    {institutions.map((inst) => (
                      <option key={inst.id} value={inst.id}>
                        {inst.code} - {inst.legal_name || inst.name} ({inst.state})
                      </option>
                    ))}
                  </select>
                  {provisionErrors.institution_id && (
                    <p className="text-rose-600 mt-0.5">{provisionErrors.institution_id}</p>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="must_change"
                  checked={provisionForm.must_change_password}
                  onChange={(e) =>
                    setProvisionForm({
                      ...provisionForm,
                      must_change_password: e.target.checked,
                    })
                  }
                  className="rounded text-sentinel-600 focus:ring-sentinel-500"
                />
                <label htmlFor="must_change" className="text-slate-700 cursor-pointer">
                  Require password change on first application login (Recommended)
                </label>
              </div>

              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsProvisionOpen(false)}
                  disabled={isProvisioning}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isProvisioning}
                  className="px-5 py-2 rounded-lg bg-sentinel-600 hover:bg-sentinel-700 text-white font-medium shadow-sm flex items-center gap-1.5"
                >
                  {isProvisioning && (
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  )}
                  <span>Provision Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resetTargetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-sentinel-100 text-sentinel-700">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Administrative Password Reset
                </h3>
                <p className="text-[11px] text-slate-500">
                  Target user: <span className="font-mono text-slate-800">{resetTargetUser.email}</span>
                </p>
              </div>
            </div>

            {!tempPasswordResult ? (
              <div className="space-y-3">
                <p className="text-slate-600 text-xs">
                  This procedure generates a high-entropy temporary password and sets the{' '}
                  <span className="font-semibold text-amber-700">must_change_password</span> flag.
                  The user will be strictly forced to rotate this password upon their next login.
                </p>
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px]">
                  <strong>Policy Notice:</strong> If email delivery is not configured, you must
                  securely communicate this temporary password directly to the verified officer.
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setResetTargetUser(null)}
                    disabled={isResetting}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleResetPassword}
                    disabled={isResetting}
                    className="px-4 py-2 rounded-lg bg-sentinel-600 hover:bg-sentinel-700 text-white font-medium shadow-sm flex items-center gap-1.5"
                  >
                    {isResetting && (
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    )}
                    <span>Generate Temporary Password</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-slate-900 text-white space-y-2">
                  <span className="text-[10px] uppercase tracking-wider text-slate-400">
                    Temporary Administrative Password
                  </span>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-base font-bold text-sentinel-300 tracking-wider">
                      {tempPasswordResult}
                    </span>
                    <button
                      onClick={() => copyToClipboard(tempPasswordResult)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      title="Copy to clipboard"
                    >
                      {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500">
                  Copy and securely communicate this temporary secret to the user. It will not be
                  displayed again or stored in plaintext.
                </p>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setResetTargetUser(null)}
                    className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-medium"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Status Toggle Modal */}
      {statusToggleTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3">
              <div
                className={`p-2.5 rounded-xl ${
                  statusToggleTarget.is_active
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                {statusToggleTarget.is_active ? (
                  <ShieldAlert className="w-5 h-5" />
                ) : (
                  <ShieldCheck className="w-5 h-5" />
                )}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  {statusToggleTarget.is_active ? 'Deactivate User Account' : 'Reactivate User Account'}
                </h3>
                <p className="text-[11px] text-slate-500 mt-1">
                  {statusToggleTarget.is_active
                    ? 'Deactivating this user revokes login access immediately. The account cannot be used until reactivated.'
                    : 'Reactivating this user restores authorized access to the application.'}
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <span className="font-semibold text-slate-700">Account:</span>{' '}
              <span className="text-slate-900">{statusToggleTarget.full_name}</span> (
              <span className="font-mono text-sentinel-700">{statusToggleTarget.email}</span>)
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setStatusToggleTarget(null)}
                disabled={isTogglingStatus}
                className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleToggleStatus}
                disabled={isTogglingStatus}
                className={`px-4 py-2 rounded-lg text-white font-medium shadow-sm flex items-center gap-1.5 ${
                  statusToggleTarget.is_active
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-emerald-600 hover:bg-emerald-700'
                }`}
              >
                {isTogglingStatus && (
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                )}
                <span>{statusToggleTarget.is_active ? 'Deactivate Account' : 'Reactivate Account'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
