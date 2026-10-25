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
    <aside className="w-64 bg-[#0D2538] text-white flex flex-col shrink-0 border-r border-[#1e3c54] select-none font-sans">
      {/* Brand Subheader */}
      <div className="p-3.5 border-b border-[#1e3c54] flex items-center justify-between bg-[#091b29]">
        <Link to="/dashboard" className="flex items-center gap-2 hover:opacity-95 transition-opacity">
          <img
            src="/logo.png"
            alt="SakshyaTrail"
            className="h-8 w-auto object-contain bg-white p-0.5 rounded-[4px] shadow-2xs"
          />
          <div>
            <span className="text-xs font-bold text-white tracking-tight block">
              Sakshya<span className="text-[#0F766E]">Trail</span>
            </span>
            <span className="text-[10px] text-[#8799A9] font-medium">
              Lifecycle Platform
            </span>
          </div>
        </Link>
        <span className="text-[10px] bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 px-1.5 py-0.5 rounded-[4px] font-mono font-semibold">
          SIH 26265
        </span>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-2.5 space-y-1 overflow-y-auto">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center justify-between px-3 py-2 rounded-[6px] text-xs font-medium transition-all group border-l-2',
                isActive
                  ? 'bg-[#123B5D] text-white border-[#0F766E] shadow-2xs'
                  : 'text-[#C9D3DB] border-transparent hover:text-white hover:bg-[#123B5D]/50 hover:border-[#8799A9]'
              )
            }
          >
            {({ isActive }) => (
              <>
                <div className="flex items-center gap-2.5">
                  <item.icon
                    className={cn(
                      'w-4 h-4 transition-colors shrink-0',
                      isActive ? 'text-[#8ACEC8]' : 'text-[#8799A9] group-hover:text-[#C9D3DB]'
                    )}
                  />
                  <span className="truncate">{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={cn(
                      'text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded-[3px]',
                      isActive
                        ? 'bg-[#0F766E] text-white'
                        : 'bg-[#123B5D] text-[#C9D3DB] group-hover:text-white'
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

      {/* Bottom Trust Level Guide - Structured Brutalism Container */}
      <div className="p-3 m-2.5 rounded-[6px] bg-[#091b29] border border-[#1e3c54] text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-white mb-2">
          <FileCheck2 className="w-3.5 h-3.5 text-[#0F766E]" />
          <span>Trust Hierarchy</span>
        </div>
        <div className="space-y-1 text-[11px] font-mono">
          <div className="flex justify-between items-center py-0.5 border-b border-[#1e3c54]/50">
            <span className="text-[#8799A9] font-bold">L0</span>
            <span className="text-[#C9D3DB]">Declared</span>
          </div>
          <div className="flex justify-between items-center py-0.5 border-b border-[#1e3c54]/50">
            <span className="text-[#64B5F6] font-bold">L1</span>
            <span className="text-[#C9D3DB]">Document-Consistent</span>
          </div>
          <div className="flex justify-between items-center py-0.5 border-b border-[#1e3c54]/50">
            <span className="text-[#8ACEC8] font-bold">L2</span>
            <span className="text-[#C9D3DB]">Officer-Verified</span>
          </div>
          <div className="flex justify-between items-center py-0.5">
            <span className="text-[#4ADE80] font-bold">L3</span>
            <span className="text-white font-bold">Authorized Response</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

