import React from 'react';
import { Database, RefreshCw, LogOut, KeyRound, Menu } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useHealth } from '@/hooks/useHealth';
import { useAuth } from '@/features/auth/AuthContext';
import { StatusIndicator } from '@/components/common/StatusIndicator';
import { Badge } from '@/components/common/Badge';

export interface HeaderProps {
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleMobileMenu }) => {
  const { liveness, readiness, isLoading, refresh } = useHealth();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const isDbReady = readiness?.is_ready ?? false;
  const dbDialect = readiness?.components?.database?.dialect?.toUpperCase() || 'SQL';
  const dbLatency = readiness?.components?.database?.latency_ms;

  const getInitials = (name?: string) => {
    if (!name) return 'U';
    const parts = name.split(' ');
    return parts.length >= 2 ? `${parts[0][0]}${parts[1][0]}`.toUpperCase() : name.slice(0, 2).toUpperCase();
  };

  const getRoleBadgeVariant = (role?: string) => {
    switch (role) {
      case 'SYSTEM_ADMIN':
        return 'danger';
      case 'COMPETENT_AUTHORITY':
      case 'BRANCH_HEAD':
        return 'purple';
      case 'SCRUTINY_OFFICER':
      case 'FINANCE_OFFICER':
        return 'teal';
      case 'INSTITUTION_USER':
        return 'default';
      case 'AUDITOR':
        return 'warning';
      default:
        return 'outline';
    }
  };

  return (
    <header className="h-16 bg-white border-b border-[#C9D3DB] sticky top-0 z-30 px-3 sm:px-6 flex items-center justify-between shadow-[0_1px_2px_rgba(13,37,56,0.03)] font-sans">
      <div className="flex items-center gap-2 sm:gap-3">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="lg:hidden p-1.5 text-[#5D6A75] hover:text-[#0D2538] hover:bg-[#F5F4EF] rounded-[6px] transition cursor-pointer"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Title & Official Subtitle */}
        <Link to="/dashboard" className="flex items-center gap-2.5 sm:gap-3 hover:opacity-95 transition-opacity">
          <img
            src="/logo.png"
            alt="SakshyaTrail Logo"
            className="h-8 sm:h-9 w-auto object-contain drop-shadow-2xs"
          />
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-[#0D2538]">
              Sakshya<span className="text-[#0F766E]">Trail</span>
            </h1>
            <Badge variant="teal" className="text-[10px] py-0 px-1.5 font-semibold">
              v0.7.0 Integrity Platform
            </Badge>
          </div>
          <p className="text-xs text-[#5D6A75] hidden sm:block font-medium">
            Security Deposit & FDR Lifecycle Integrity Platform
          </p>
        </div>
      </Link>
    </div>

      {/* Real-time Diagnostics Bar & Authenticated User Section */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Backend & DB Health Indicator - Structured Brutalism Container */}
        <div className="hidden lg:flex items-center gap-2.5 px-3 py-1 bg-[#F5F4EF] border border-[#C9D3DB] rounded-[6px] text-xs">
          <div className="flex items-center gap-1.5" title="FastAPI Backend Liveness">
            <StatusIndicator
              status={liveness ? 'online' : 'offline'}
              label={liveness ? 'API Alive' : 'API Offline'}
            />
          </div>

          <span className="text-[#8799A9]">|</span>

          <div
            className="flex items-center gap-1.5"
            title={`Database: ${dbDialect} (${readiness?.components?.database?.status || 'Unknown'})`}
          >
            <Database className="w-3.5 h-3.5 text-[#5D6A75]" />
            <span className="font-mono text-[11px] text-[#253746] font-semibold">
              {dbDialect}
            </span>
            {isDbReady ? (
              <Badge variant="success" className="text-[10px] py-0 px-1 font-mono">
                {dbLatency ? `${dbLatency}ms` : 'Ready'}
              </Badge>
            ) : (
              <Badge variant="warning" className="text-[10px] py-0 px-1 font-mono">
                Not Connected
              </Badge>
            )}
          </div>

          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="text-[#5D6A75] hover:text-[#0D2538] transition-colors ml-1 p-0.5 rounded-[4px] cursor-pointer"
            title="Refresh connectivity probes"
            aria-label="Refresh health checks"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Authenticated User Identity */}
        {user ? (
          <div className="flex items-center gap-3 pl-2 sm:border-l sm:border-[#C9D3DB]">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-[#0D2538] leading-tight">
                {user.full_name}
              </div>
              <div className="flex items-center justify-end gap-1.5 mt-0.5">
                <Badge variant={getRoleBadgeVariant(user.role)} className="text-[9px] py-0 px-1 font-mono font-semibold">
                  {user.role}
                </Badge>
              </div>
            </div>

            <div
              className="w-8 h-8 rounded-full bg-[#123B5D] text-white flex items-center justify-center font-bold text-xs shadow-2xs"
              title={`${user.full_name} (${user.email})`}
            >
              {getInitials(user.full_name)}
            </div>

            <Link
              to="/change-password"
              className="p-1.5 text-[#5D6A75] hover:text-[#123B5D] hover:bg-[#EDF1F3] rounded-[6px] transition-colors cursor-pointer"
              title="Change account password"
              aria-label="Change password"
            >
              <KeyRound className="w-4 h-4" />
            </Link>

            <button
              onClick={async () => {
                await logout();
                navigate('/', { replace: true });
              }}
              className="p-1.5 text-[#5D6A75] hover:text-[#B42318] hover:bg-[#FDF2F1] rounded-[6px] transition-colors cursor-pointer"
              title="Sign out of regulatory session"
              aria-label="Log out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
};

