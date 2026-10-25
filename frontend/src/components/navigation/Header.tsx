import { ShieldCheck, Database, RefreshCw, LogOut, KeyRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useHealth } from '@/hooks/useHealth';
import { useAuth } from '@/features/auth/AuthContext';
import { StatusIndicator } from '@/components/common/StatusIndicator';
import { Badge } from '@/components/common/Badge';

export const Header: React.FC = () => {
  const { liveness, readiness, isLoading, refresh } = useHealth();
  const { user, logout } = useAuth();

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
        return 'info';
      case 'INSTITUTION_USER':
        return 'default';
      case 'AUDITOR':
        return 'warning';
      default:
        return 'outline';
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 px-4 sm:px-6 flex items-center justify-between shadow-xs">
      {/* Title & Official Subtitle */}
      <Link to="/dashboard" className="flex items-center gap-3 hover:opacity-95 transition-opacity">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-sentinel-700 text-white font-bold shadow-sm shadow-sentinel-900/20">
          <ShieldCheck className="w-5 h-5 text-sentinel-200" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-slate-900">
              Sakshya<span className="text-teal-600">Trail</span>
            </h1>
            <Badge variant="info" className="text-[10px] py-0 px-1.5 font-semibold">
              v0.7.0 Integrity Platform
            </Badge>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            Security Deposit & FDR Lifecycle Integrity Platform
          </p>
        </div>
      </Link>

      {/* Real-time Diagnostics Bar & Authenticated User Section */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Backend & DB Health Indicator */}
        <div className="hidden lg:flex items-center gap-2.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs">
          <div className="flex items-center gap-1.5" title="FastAPI Backend Liveness">
            <StatusIndicator
              status={liveness ? 'online' : 'offline'}
              label={liveness ? 'API Alive' : 'API Offline'}
            />
          </div>

          <span className="text-slate-300">|</span>

          <div
            className="flex items-center gap-1.5"
            title={`Database: ${dbDialect} (${readiness?.components?.database?.status || 'Unknown'})`}
          >
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-mono text-[11px] text-slate-600">
              {dbDialect}
            </span>
            {isDbReady ? (
              <Badge variant="success" className="text-[10px] py-0 px-1">
                {dbLatency ? `${dbLatency}ms` : 'Ready'}
              </Badge>
            ) : (
              <Badge variant="warning" className="text-[10px] py-0 px-1">
                Not Connected
              </Badge>
            )}
          </div>

          <button
            onClick={() => refresh()}
            disabled={isLoading}
            className="text-slate-400 hover:text-slate-700 transition-colors ml-1 p-0.5 rounded cursor-pointer"
            title="Refresh connectivity probes"
            aria-label="Refresh health checks"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Authenticated User Identity */}
        {user ? (
          <div className="flex items-center gap-3 pl-2 sm:border-l sm:border-slate-200">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-800 leading-tight">
                {user.full_name}
              </div>
              <div className="flex items-center justify-end gap-1.5 mt-0.5">
                <Badge variant={getRoleBadgeVariant(user.role)} className="text-[9px] py-0 px-1 font-mono font-semibold">
                  {user.role}
                </Badge>
              </div>
            </div>

            <div
              className="w-8 h-8 rounded-full bg-sentinel-50 border border-sentinel-200 flex items-center justify-center font-bold text-sentinel-800 text-xs shadow-xs"
              title={`${user.full_name} (${user.email})`}
            >
              {getInitials(user.full_name)}
            </div>

            <Link
              to="/change-password"
              className="p-1.5 text-slate-400 hover:text-sentinel-700 hover:bg-sentinel-50 rounded-lg transition-colors cursor-pointer"
              title="Change account password"
              aria-label="Change password"
            >
              <KeyRound className="w-4 h-4" />
            </Link>

            <button
              onClick={() => logout()}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
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
