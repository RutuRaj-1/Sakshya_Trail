import React from 'react';
import { ShieldCheck, Database, RefreshCw } from 'lucide-react';
import { useHealth } from '@/hooks/useHealth';
import { StatusIndicator } from '@/components/common/StatusIndicator';
import { Badge } from '@/components/common/Badge';

export const Header: React.FC = () => {
  const { liveness, readiness, isLoading, refresh } = useHealth();

  const isDbReady = readiness?.is_ready ?? false;
  const dbDialect = readiness?.components?.database?.dialect?.toUpperCase() || 'SQL';
  const dbLatency = readiness?.components?.database?.latency_ms;

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 px-4 sm:px-6 flex items-center justify-between shadow-xs">
      {/* Title & Official Subtitle */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-sentinel-700 text-white font-bold shadow-sm shadow-sentinel-900/20">
          <ShieldCheck className="w-5 h-5 text-sentinel-200" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-slate-900">
              FDR Sentinel
            </h1>
            <Badge variant="info" className="text-[10px] py-0 px-1.5 font-semibold">
              v0.1.0 Prototype
            </Badge>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            AICTE Regulation Bureau · Security Deposit & FDR Lifecycle Integrity
          </p>
        </div>
      </div>

      {/* Real-time Diagnostics Bar */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Backend & DB Health Indicator */}
        <div className="flex items-center gap-2.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs">
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

        {/* Current Active Persona / Role Tag */}
        <div className="hidden md:flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="text-right">
            <div className="text-xs font-semibold text-slate-800">Officer Portal</div>
            <div className="text-[10px] text-sentinel-700 font-medium">Regulation Bureau</div>
          </div>
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-700 text-xs">
            AI
          </div>
        </div>
      </div>
    </header>
  );
};
