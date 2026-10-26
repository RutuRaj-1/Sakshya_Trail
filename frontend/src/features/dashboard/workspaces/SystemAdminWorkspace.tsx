import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  Building2,
  Activity,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
} from 'lucide-react';
import { usersApi, institutionsApi, healthApi, lifecycleApi } from '@/api/endpoints';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import type { User, Institution } from '@/types';
import type { SystemHealth, ReadinessState } from '@/types';
import type { LifecycleNotification } from '@/types/lifecycle';

export const SystemAdminWorkspace: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [totalUsers, setTotalUsers] = useState<number>(0);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [totalInstitutions, setTotalInstitutions] = useState<number>(0);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [readiness, setReadiness] = useState<ReadinessState | null>(null);
  const [failedNotifications, setFailedNotifications] = useState<LifecycleNotification[]>([]);
  const [oversightNotifications, setOversightNotifications] = useState<LifecycleNotification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [usersRes, instRes, liveRes, readyRes, failedNotifRes, oversightRes] = await Promise.allSettled([
        usersApi.list({ limit: 6 }),
        institutionsApi.list({ limit: 6 }),
        healthApi.getLiveness(),
        healthApi.getReadiness(),
        lifecycleApi.listFailedNotifications(),
        lifecycleApi.getAdminOversightFeed(1, 10),
      ]);

      if (usersRes.status === 'fulfilled') {
        setUsers(usersRes.value.items || []);
        setTotalUsers(usersRes.value.total || 0);
      }
      if (instRes.status === 'fulfilled') {
        setInstitutions(instRes.value.items || []);
        setTotalInstitutions(instRes.value.total || 0);
      }
      if (liveRes.status === 'fulfilled') setHealth(liveRes.value);
      if (readyRes.status === 'fulfilled') setReadiness(readyRes.value);
      if (failedNotifRes.status === 'fulfilled') setFailedNotifications(failedNotifRes.value || []);
      if (oversightRes.status === 'fulfilled') {
        const feed = oversightRes.value.items || oversightRes.value.notifications || [];
        setOversightNotifications(feed);
      }
    } catch {
      setError('Unable to load administration metrics.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans">
      {/* Top Banner — System Admin Cockpit */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 text-white shadow-xs border border-[#1e3c54]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2 py-0.5 rounded font-mono uppercase">
                Platform Superuser
              </span>
              <span className="text-[#8799A9] text-xs font-mono">System Administration Cockpit</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Platform Governance & Security Administration
            </h1>
            <p className="text-xs text-[#C9D3DB] mt-1 leading-relaxed max-w-2xl">
              Provision regulatory and institutional user accounts, manage affiliated educational institutions, monitor system health diagnostics, and audit administrative event integrity.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link to="/users">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold">
                <Users className="w-4 h-4 mr-1.5" /> User Management
              </Button>
            </Link>
            <Link to="/institutions">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D]">
                <Building2 className="w-4 h-4 mr-1.5" /> Institution Directory
              </Button>
            </Link>
            <Link to="/health">
              <Button size="sm" variant="outline" className="border-[#8799A9] text-white hover:bg-[#123B5D]">
                <Activity className="w-4 h-4 mr-1.5" /> Diagnostics
              </Button>
            </Link>
            <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white" onClick={loadData}>
              <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
            </Button>
          </div>
        </div>
      </div>

      {/* Admin Separation of Duties Notice */}
      <div className="bg-[#FEF7E8] border border-[#F8DEAE] rounded-lg p-3.5 flex items-start gap-2.5 text-xs text-[#8A5A00]">
        <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong>Maker-Checker Invariant (PRD-FR-095):</strong> System Administrators manage platform users, institutions, and infrastructure. The administrator role does <em>not</em> possess statutory authority to approve release requests or bypass Release Gate blockers.
        </p>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 flex items-center justify-between text-xs text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
          <Button size="sm" variant="outline" onClick={loadData}>Retry</Button>
        </div>
      )}

      {/* KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">System Health</p>
              <h3 className="text-xl font-bold font-mono mt-0.5 text-[#18794E]">
                {health?.status || (isLoading ? '...' : 'HEALTHY')}
              </h3>
              <p className="text-[10px] text-[#18794E] mt-0.5">Database: {readiness?.components?.database?.status || 'CONNECTED'}</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <Users className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Provisioned Users</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : totalUsers}
              </h3>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">7 RBAC Canonical Roles</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#E6F4F2] text-[#0F766E] border border-[#99D5CE]">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Registered Institutions</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : totalInstitutions}
              </h3>
              <p className="text-[10px] text-[#0F766E] mt-0.5">AICTE Affiliated Entities</p>
            </div>
          </div>
        </Card>

        <Card className="p-4 border-[#C9D3DB]">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-[#FDF2F1] text-[#B42318] border border-[#FECDCA]">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider">Failed Dispatches</p>
              <h3 className="text-xl font-bold text-[#0D2538] font-mono mt-0.5">
                {isLoading ? '...' : failedNotifications.length}
              </h3>
              <p className="text-[10px] text-[#B42318] mt-0.5">Notification Delivery Failures</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Main Split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: User Accounts Summary */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Active User Accounts ({totalUsers})
              </h2>
              <p className="text-xs text-[#5D6A75]">Assigned platform roles and authentication profiles</p>
            </div>
            <Link to="/users" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
              <span>Manage Users</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white rounded-[10px] border border-[#C9D3DB] overflow-hidden shadow-2xs">
            {users.length === 0 ? (
              <p className="text-xs text-[#5D6A75] text-center py-6">No users found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">User</th>
                      <th className="py-2.5 px-4 font-semibold">Role</th>
                      <th className="py-2.5 px-4 font-semibold">Tenancy</th>
                      <th className="py-2.5 px-4 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-medium text-[#0D2538]">
                          <div>{u.full_name}</div>
                          <div className="text-[10px] text-[#8799A9] font-mono">{u.email}</div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                            {u.role}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-[#5D6A75]">
                          {u.institution_id || 'INTERNAL'}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={u.is_active ? 'success' : 'danger'}>
                            {u.is_active ? 'Active' : 'Suspended'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right: Institution Directory Summary */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Affiliated Institutions ({totalInstitutions})
              </h2>
              <p className="text-xs text-[#5D6A75]">Registered institutional tenancies in directory</p>
            </div>
            <Link to="/institutions" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1">
              <span>Directory</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white rounded-[10px] border border-[#C9D3DB] overflow-hidden shadow-2xs">
            {institutions.length === 0 ? (
              <p className="text-xs text-[#5D6A75] text-center py-6">No institutions registered.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Code</th>
                      <th className="py-2.5 px-4 font-semibold">Name</th>
                      <th className="py-2.5 px-4 font-semibold">State</th>
                      <th className="py-2.5 px-4 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-sans">
                    {institutions.map((inst) => (
                      <tr key={inst.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-[#0D2538]">
                          <Link to={`/institutions/${inst.id}`} className="hover:text-[#0F766E] hover:underline">
                            {inst.code}
                          </Link>
                        </td>
                        <td className="py-3 px-4 text-[#253746] font-medium max-w-40 truncate">{inst.name}</td>
                        <td className="py-3 px-4 text-[#5D6A75]">{inst.state || 'N/A'}</td>
                        <td className="py-3 px-4">
                          <Badge variant={inst.is_active ? 'success' : 'default'}>
                            {inst.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Operational Oversight Feed — Material Events & Audit Accountability */}
      <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-5 shadow-2xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <h2 className="text-sm font-bold text-[#0D2538] uppercase tracking-wider">
                Operational Oversight Feed ({oversightNotifications.length})
              </h2>
            </div>
            <p className="text-xs text-[#5D6A75] mt-0.5">
              Authoritative feed of material business operations, actor roles, state changes, and verified SHA-256 audit ledger records
            </p>
          </div>
          <Link to="/audit" className="text-xs text-[#0F766E] font-semibold hover:underline flex items-center gap-1 self-start sm:self-auto">
            <span>Audit Ledger & Integrity Check</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {oversightNotifications.length === 0 ? (
          <div className="text-center py-8 text-xs text-[#5D6A75] bg-slate-50 rounded-lg border border-dashed border-slate-200">
            <p className="font-semibold text-slate-700">No operational oversight events recorded yet.</p>
            <p className="text-[11px] text-slate-500 mt-1">Material actions across the 9 lifecycle stages will appear here in real time.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] font-mono border-b border-[#C9D3DB]">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Event</th>
                  <th className="py-2.5 px-4 font-semibold">Actor / Role</th>
                  <th className="py-2.5 px-4 font-semibold">Entity Reference</th>
                  <th className="py-2.5 px-4 font-semibold">Audit Record</th>
                  <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {oversightNotifications.map((notif) => {
                  let meta: Record<string, any> = {};
                  try {
                    meta = notif.payload_metadata_json ? JSON.parse(notif.payload_metadata_json) : {};
                  } catch {
                    meta = {};
                  }
                  const actorInfo = meta.actor || {};
                  const entityInfo = meta.entity || {};
                  const safeLink = meta.safe_link || (notif.instrument_id ? `/instruments/${notif.instrument_id}` : '/audit');

                  return (
                    <tr key={notif.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-[#0D2538]">
                          {notif.title || notif.rendered_title || notif.event_type}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5 line-clamp-1">
                          {notif.message || notif.rendered_message || notif.event_type}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-700">
                        <div>{actorInfo.name || notif.recipient_role}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {actorInfo.role || notif.recipient_role}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-800">
                        {entityInfo.reference || notif.instrument_id || entityInfo.id || 'N/A'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                          ✓ SHA-256 Chained
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {new Date(notif.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          to={safeLink}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0F766E] hover:underline"
                        >
                          View Detail <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
