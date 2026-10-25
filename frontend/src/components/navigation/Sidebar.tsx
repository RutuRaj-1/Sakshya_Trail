import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  FileSpreadsheet,
  History,
  Activity,
  FileCheck2,
  Users,
  KeyRound,
  AlertTriangle,
  ShieldCheck,
  FileText,
  SlidersHorizontal,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/features/auth/AuthContext';

interface NavItem {
  name: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  adminOnly?: boolean;
}

const baseNavItems: NavItem[] = [
  { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { name: 'Command Center', to: '/command-center', icon: SlidersHorizontal, badge: 'Module 7' },
  { name: 'Unified Search', to: '/search', icon: Search, badge: 'Search' },
  { name: 'Operational Reports', to: '/reports', icon: FileSpreadsheet, badge: 'Reports' },
  { name: 'Release / Refund Cases', to: '/release', icon: FileText, badge: 'Module 6' },
  { name: 'Review Queue', to: '/findings/queue', icon: AlertTriangle, badge: 'Scrutiny' },
  { name: 'Trust & Verification', to: '/verification', icon: ShieldCheck, badge: 'Trust' },
  { name: 'FDR Instruments', to: '/instruments', icon: FileSpreadsheet, badge: 'Core' },
  { name: 'Institutions', to: '/institutions', icon: Building2 },
  { name: 'User Admin', to: '/users', icon: Users, badge: 'Admin', adminOnly: true },
  { name: 'Audit History', to: '/audit', icon: History },
  { name: 'Password Security', to: '/change-password', icon: KeyRound },
  { name: 'System Diagnostics', to: '/health', icon: Activity },
];

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';

  const visibleItems = baseNavItems.filter((item) => !item.adminOnly || isSystemAdmin);

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800 select-none">
      {/* Brand Subheader */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <Link to="/dashboard" className="flex items-center gap-2 hover:opacity-90 transition-opacity">
          <img
            src="/logo.png"
            alt="SakshyaTrail"
            className="h-8 w-auto object-contain bg-white/95 p-0.5 rounded shadow-2xs"
          />
          <div>
            <span className="text-xs font-bold text-white tracking-tight block">
              Sakshya<span className="text-teal-400">Trail</span>
            </span>
            <span className="text-[10px] text-slate-400 font-medium">
              Lifecycle Platform
            </span>
          </div>
        </Link>
        <span className="text-[10px] bg-slate-800 text-teal-400 border border-teal-500/20 px-1.5 py-0.5 rounded font-mono font-semibold">
          SIH 26265
        </span>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all group',
                isActive
                  ? 'bg-sentinel-700 text-white shadow-sm shadow-sentinel-950/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              )
            }
          >
            {({ isActive }) => (
              <>
                <div className="flex items-center gap-3">
                  <item.icon
                    className={cn(
                      'w-4 h-4 transition-colors',
                      isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'
                    )}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={cn(
                      'text-[10px] font-semibold px-1.5 py-0.5 rounded',
                      isActive
                        ? 'bg-sentinel-800 text-sentinel-200'
                        : 'bg-slate-800 text-slate-400 group-hover:text-slate-300'
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom Trust Level Guide */}
      <div className="p-4 m-3 rounded-lg bg-slate-850 border border-slate-800/80 text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200 mb-2">
          <FileCheck2 className="w-3.5 h-3.5 text-sentinel-400" />
          <span>Trust Hierarchy</span>
        </div>
        <div className="space-y-1 text-[11px] text-slate-400 font-mono">
          <div className="flex justify-between">
            <span className="text-slate-500">L1</span>
            <span className="text-slate-300">Declared</span>
          </div>
          <div className="flex justify-between">
            <span className="text-blue-400">L2</span>
            <span className="text-slate-300">Consistent</span>
          </div>
          <div className="flex justify-between">
            <span className="text-emerald-400">L3</span>
            <span className="text-slate-300">Verified</span>
          </div>
          <div className="flex justify-between">
            <span className="text-purple-400">L4</span>
            <span className="text-slate-200 font-bold">Confirmed</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
