import React, { useState } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  SlidersHorizontal,
  FileSpreadsheet,
  AlertTriangle,
  ShieldCheck,
  Clock,
  Search,
  History,
  Building2,
  Users,
  KeyRound,
  Activity,
  ChevronDown,
  ChevronRight,
  UploadCloud,
  X,
  FilePlus2,
  ClipboardList,
  RefreshCw,
  DoorOpen,
  Scale,
  Layers,
  Calendar,
  GitBranch,
  AlertOctagon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/features/auth/AuthContext';
import { useNavBadges } from '@/hooks/useNavBadges';

export interface NavDestination {
  name: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  allowedRoles?: string[];
  badgeKey?: 'reviewQueueCount' | 'verificationQueueCount' | 'releaseCasesCount';
  stageNumber?: number;
}

export interface NavGroup {
  id: string;
  title: string;
  items: NavDestination[];
  allowedRoles?: string[];
}

/**
 * SakshyaTrail Navigation Hierarchy:
 * 1. Experience A: FDR Workflow (Nine Canonical Stages)
 * 2. Experience B: Lifecycle & Monitoring (Portfolio Surveillance & Lineage)
 * 3. Experience C: My Workspace (Role-Specific Workspace & Command Center)
 * 4. Supporting Capabilities: Unified Search, Reports, Audit, Directory, Users, Security, Health
 */
export const NAV_GROUPS: NavGroup[] = [
  // ─── 1. Primary Experience A: Nine-Stage FDR Workflow ───────────────────────
  {
    id: 'fdr-workflow',
    title: 'FDR Workflow',
    items: [
      {
        name: 'FDR Submission & Registration',
        stageNumber: 1,
        to: '/instruments',
        icon: FilePlus2,
      },
      {
        name: 'Document Upload & Evidence',
        stageNumber: 2,
        to: '/documents',
        icon: UploadCloud,
      },
      {
        name: 'Validation & Discrepancy Detection',
        stageNumber: 3,
        to: '/findings/queue?status=OPEN',
        icon: AlertTriangle,
        allowedRoles: [
          'SYSTEM_ADMIN',
          'SCRUTINY_OFFICER',
          'BRANCH_HEAD',
          'COMPETENT_AUTHORITY',
          'FINANCE_OFFICER',
          'AUDITOR',
        ],
        badgeKey: 'reviewQueueCount',
      },
      {
        name: 'Scrutiny & Review',
        stageNumber: 4,
        to: '/findings/queue?status=IN_REVIEW',
        icon: ClipboardList,
        allowedRoles: [
          'SYSTEM_ADMIN',
          'SCRUTINY_OFFICER',
          'BRANCH_HEAD',
          'COMPETENT_AUTHORITY',
          'FINANCE_OFFICER',
          'AUDITOR',
        ],
      },
      {
        name: 'Bank Verification & Trust',
        stageNumber: 5,
        to: '/verification',
        icon: ShieldCheck,
        allowedRoles: [
          'SYSTEM_ADMIN',
          'SCRUTINY_OFFICER',
          'BRANCH_HEAD',
          'COMPETENT_AUTHORITY',
          'FINANCE_OFFICER',
          'AUDITOR',
        ],
        badgeKey: 'verificationQueueCount',
      },
      {
        name: 'Lifecycle Monitoring',
        stageNumber: 6,
        to: '/monitoring',
        icon: Clock,
      },
      {
        name: 'Renewal & Successor Lineage',
        stageNumber: 7,
        to: '/monitoring?tab=renewals',
        icon: RefreshCw,
      },
      {
        name: 'Release Readiness',
        stageNumber: 8,
        to: '/release?status=UNDER_REVIEW',
        icon: DoorOpen,
        badgeKey: 'releaseCasesCount',
      },
      {
        name: 'Maker-Checker Decision & Closure',
        stageNumber: 9,
        to: '/release?status=READY_FOR_AUTHORITY',
        icon: Scale,
      },
    ],
  },

  // ─── 2. Primary Experience B: Lifecycle & Monitoring ───────────────────────
  {
    id: 'lifecycle-monitoring',
    title: 'Lifecycle & Monitoring',
    items: [
      {
        name: 'Portfolio Overview',
        to: '/monitoring',
        icon: Layers,
      },
      {
        name: 'Maturity Calendar',
        to: '/monitoring?tab=calendar',
        icon: Calendar,
      },
      {
        name: 'Approaching & Overdue',
        to: '/monitoring?tab=maturities',
        icon: Clock,
      },
      {
        name: 'Renewal Queue',
        to: '/monitoring?tab=renewals',
        icon: RefreshCw,
      },
      {
        name: 'Predecessor–Successor Lineage',
        to: '/monitoring?tab=lineage',
        icon: GitBranch,
      },
      {
        name: 'Lifecycle Exceptions & Alerts',
        to: '/monitoring?tab=exceptions',
        icon: AlertOctagon,
      },
      {
        name: 'Policies & Scheduler',
        to: '/monitoring?tab=scheduler',
        icon: SlidersHorizontal,
        allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER'],
      },
    ],
  },

  // ─── 3. Primary Experience C: Role-Specific Dashboard / Workspace ──────────
  {
    id: 'workspace',
    title: 'My Workspace',
    items: [
      { name: 'Overview', to: '/dashboard', icon: LayoutDashboard },
      {
        name: 'Command Center',
        to: '/command-center',
        icon: SlidersHorizontal,
        allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY'],
      },
    ],
  },

  // ─── 4. Supporting Capabilities ─────────────────────────────────────────────
  {
    id: 'supporting-capabilities',
    title: 'Supporting Capabilities',
    items: [
      { name: 'Unified Search', to: '/search', icon: Search },
      {
        name: 'Operational Reports',
        to: '/reports',
        icon: FileSpreadsheet,
        allowedRoles: [
          'SYSTEM_ADMIN',
          'SCRUTINY_OFFICER',
          'BRANCH_HEAD',
          'COMPETENT_AUTHORITY',
          'FINANCE_OFFICER',
          'AUDITOR',
        ],
      },
      {
        name: 'Audit & Integrity',
        to: '/audit',
        icon: History,
        allowedRoles: ['SYSTEM_ADMIN', 'BRANCH_HEAD', 'COMPETENT_AUTHORITY', 'AUDITOR'],
      },
      {
        name: 'Institution Directory',
        to: '/institutions',
        icon: Building2,
        allowedRoles: [
          'SYSTEM_ADMIN',
          'SCRUTINY_OFFICER',
          'BRANCH_HEAD',
          'COMPETENT_AUTHORITY',
          'FINANCE_OFFICER',
          'AUDITOR',
        ],
      },
      {
        name: 'Users & Access',
        to: '/users',
        icon: Users,
        allowedRoles: ['SYSTEM_ADMIN'],
      },
      { name: 'Password Security', to: '/change-password', icon: KeyRound },
      {
        name: 'System Diagnostics',
        to: '/health',
        icon: Activity,
        allowedRoles: ['SYSTEM_ADMIN', 'SCRUTINY_OFFICER', 'AUDITOR'],
      },
    ],
  },
];

interface SidebarProps {
  onCloseMobile?: () => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ onCloseMobile, className }) => {
  const { user } = useAuth();
  const badges = useNavBadges();
  const location = useLocation();

  // Collapsible groups with persisted state
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>(() => {
    try {
      const stored = localStorage.getItem('sakshya_nav_collapsed');
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const toggleGroup = (groupId: string) => {
    setCollapsedGroups((prev) => {
      const next = { ...prev, [groupId]: !prev[groupId] };
      try {
        localStorage.setItem('sakshya_nav_collapsed', JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const isRoleAllowed = (allowedRoles?: string[]) => {
    if (!allowedRoles || allowedRoles.length === 0) return true;
    return allowedRoles.includes(user?.role || '');
  };

  /**
   * Evaluates if a navigation destination is active, supporting query parameter destinations.
   */
  const isDestinationActive = (destTo: string): boolean => {
    if (destTo.includes('?')) {
      const [destPath, destQuery] = destTo.split('?');
      return location.pathname === destPath && location.search.includes(destQuery);
    }
    if (destTo === '/dashboard') {
      return location.pathname === '/dashboard';
    }
    if (destTo === '/monitoring') {
      return (
        location.pathname === '/monitoring' &&
        (!location.search || location.search === '' || location.search === '?tab=overview')
      );
    }
    if (destTo === '/release') {
      return location.pathname === '/release' && (!location.search || location.search === '');
    }
    if (destTo === '/findings/queue') {
      return (
        location.pathname === '/findings/queue' &&
        (!location.search || location.search === '')
      );
    }
    if (destTo === '/instruments') {
      return (
        location.pathname === '/instruments' &&
        (!location.search || location.search === '')
      );
    }
    return location.pathname === destTo || location.pathname.startsWith(`${destTo}/`);
  };

  return (
    <aside
      className={cn(
        'w-64 bg-[#0D2538] text-white flex flex-col shrink-0 border-r border-[#1e3c54] select-none font-sans h-full',
        className
      )}
    >
      {/* Brand Header */}
      <div className="p-3.5 border-b border-[#1e3c54] flex items-center justify-between bg-[#091b29]">
        <Link
          to="/dashboard"
          onClick={onCloseMobile}
          className="flex items-center gap-2 hover:opacity-95 transition-opacity"
        >
          <img
            src="/logo.png"
            alt="SakshyaTrail"
            className="h-8 w-auto object-contain bg-white p-0.5 rounded-[4px] shadow-2xs"
          />
          <div>
            <span className="text-xs font-bold text-white tracking-tight block">
              Sakshya<span className="text-[#0F766E]">Trail</span>
            </span>
            <span className="text-[10px] text-[#8799A9] font-medium block leading-none mt-0.5">
              Lifecycle Platform
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 px-1.5 py-0.5 rounded-[4px] font-mono font-semibold">
            SIH 26265
          </span>
          {onCloseMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-[#8799A9] hover:text-white rounded"
              aria-label="Close sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 p-2.5 space-y-3 overflow-y-auto" aria-label="Main Navigation">
        {NAV_GROUPS.map((group) => {
          if (!isRoleAllowed(group.allowedRoles)) return null;

          const visibleItems = group.items.filter((item) => isRoleAllowed(item.allowedRoles));
          if (visibleItems.length === 0) return null;

          const isCollapsed = Boolean(collapsedGroups[group.id]);
          const isGroupActive = visibleItems.some((item) => isDestinationActive(item.to));

          return (
            <div key={group.id} className="space-y-1">
              {/* Group Header Button */}
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#8799A9] hover:text-[#C9D3DB] transition-colors rounded cursor-pointer group"
                aria-expanded={!isCollapsed}
              >
                <div className="flex items-center gap-1.5">
                  <span>{group.title}</span>
                  {isGroupActive && isCollapsed && (
                    <span
                      className="w-1.5 h-1.5 rounded-full bg-[#0F766E]"
                      title="Active route in this section"
                    />
                  )}
                </div>
                {isCollapsed ? (
                  <ChevronRight className="w-3 h-3 text-[#8799A9] group-hover:text-white transition-transform" />
                ) : (
                  <ChevronDown className="w-3 h-3 text-[#8799A9] group-hover:text-white transition-transform" />
                )}
              </button>

              {/* Collapsible Destination List */}
              {!isCollapsed && (
                <div className="space-y-0.5 pl-0.5">
                  {visibleItems.map((item) => {
                    const badgeCount = item.badgeKey ? badges[item.badgeKey] : undefined;
                    const isActive = isDestinationActive(item.to);

                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        onClick={onCloseMobile}
                        className={cn(
                          'flex items-center justify-between px-2.5 py-1.5 rounded-[6px] text-xs font-medium transition-all group border-l-2',
                          isActive
                            ? 'bg-[#123B5D] text-white border-[#0F766E] shadow-2xs font-semibold'
                            : 'text-[#C9D3DB] border-transparent hover:text-white hover:bg-[#123B5D]/40 hover:border-[#8799A9]'
                        )}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <item.icon
                            className={cn(
                              'w-4 h-4 transition-colors shrink-0',
                              isActive ? 'text-[#8ACEC8]' : 'text-[#8799A9] group-hover:text-[#C9D3DB]'
                            )}
                          />
                          {item.stageNumber !== undefined && (
                            <span
                              className={cn(
                                'font-mono text-[9px] font-bold shrink-0',
                                isActive
                                  ? 'text-[#8ACEC8]'
                                  : 'text-[#8799A9] group-hover:text-[#C9D3DB]'
                              )}
                            >
                              0{item.stageNumber}
                            </span>
                          )}
                          <span className="truncate">{item.name}</span>
                        </div>

                        {/* Live Count Badge (Shown only when meaningful and available) */}
                        {badgeCount !== undefined && badgeCount > 0 && (
                          <span
                            className={cn(
                              'text-[10px] font-mono font-bold px-1.5 py-0.2 rounded shrink-0',
                              isActive
                                ? 'bg-[#0F766E] text-white'
                                : 'bg-[#123B5D] text-[#8ACEC8] group-hover:bg-[#0F766E] group-hover:text-white'
                            )}
                            title={`${badgeCount} active item(s)`}
                          >
                            {badgeCount}
                          </span>
                        )}
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* User Scope Footer */}
      <div className="p-3 m-2 rounded-[6px] bg-[#091b29] border border-[#1e3c54] text-[11px] text-[#8799A9]">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase font-bold text-[#C9D3DB] tracking-wider">
            Session Scope
          </span>
          <span className="font-mono text-[9px] text-[#8ACEC8] bg-[#123B5D] px-1 py-0.2 rounded font-semibold">
            {user?.role?.slice(0, 12)}
          </span>
        </div>
        <div className="truncate text-white font-medium mt-1">
          {user?.institution_id ? 'Tenancy Scoped' : 'Central Bureau'}
        </div>
      </div>
    </aside>
  );
};
