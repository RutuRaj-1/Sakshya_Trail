import React from 'react';
import { useHealth } from '@/hooks/useHealth';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { apiClient } from '@/api/client';
import {
  Activity,
  Database,
  Server,
  RefreshCw,
  Code2,
} from 'lucide-react';

export const HealthPage: React.FC = () => {
  const { liveness, readiness, isLoading, refresh } = useHealth(5000);

  const isDbReady = readiness?.is_ready ?? false;
  const dbInfo = readiness?.components?.database;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#0D2538] tracking-tight flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#123B5D]" /> System Diagnostics & Health
          </h1>
          <p className="text-xs text-[#5D6A75]">
            Real-time liveness and readiness observability probes
          </p>
        </div>

        <Button size="sm" onClick={() => refresh()} disabled={isLoading} variant="outline">
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
          Run Health Check
        </Button>
      </div>

      {/* Grid of Diagnostics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Backend API Liveness */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5 text-[#123B5D]" />
              <h2 className="text-sm font-bold text-[#253746]">FastAPI Backend (Liveness)</h2>
            </div>
            {liveness ? (
              <Badge variant="success">ALIVE</Badge>
            ) : (
              <Badge variant="danger">DOWN</Badge>
            )}
          </div>

          <div className="space-y-2 text-xs font-mono bg-[#F5F4EF] p-3 rounded-lg border border-[#C9D3DB]">
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Service:</span>
              <span className="text-[#253746] font-semibold">{liveness?.service || 'SakshyaTrail'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Version:</span>
              <span className="text-[#253746]">{liveness?.version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Environment:</span>
              <span className="text-[#253746]">{liveness?.environment || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Probe Endpoint:</span>
              <span className="text-[#123B5D]">/api/v1/health/live</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Configured URL:</span>
              <span className="text-[#5D6A75] truncate max-w-[200px]">{apiClient.getBaseUrl()}</span>
            </div>
          </div>
        </Card>

        {/* Database Readiness Probe */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-[#123B5D]" />
              <h2 className="text-sm font-bold text-[#253746]">Database Layer (Readiness)</h2>
            </div>
            {isDbReady ? (
              <Badge variant="success">READY</Badge>
            ) : (
              <Badge variant="warning">DEGRADED / NOT READY</Badge>
            )}
          </div>

          <div className="space-y-2 text-xs font-mono bg-[#F5F4EF] p-3 rounded-lg border border-[#C9D3DB]">
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Status:</span>
              <span className={isDbReady ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>
                {dbInfo?.status || (isLoading ? 'Checking...' : 'Disconnected')}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Dialect:</span>
              <span className="text-[#253746] font-bold uppercase">{dbInfo?.dialect || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Ping Latency:</span>
              <span className="text-[#253746]">
                {dbInfo?.latency_ms !== undefined ? `${dbInfo.latency_ms} ms` : '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#5D6A75]">Probe Endpoint:</span>
              <span className="text-[#123B5D]">/api/v1/health/ready</span>
            </div>
            {dbInfo?.error && (
              <div className="pt-2 text-[11px] text-rose-600 border-t border-rose-200">
                Error: {dbInfo.error}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Raw Diagnostic Payloads */}
      <Card className="space-y-3">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-[#5D6A75]" />
          <h2 className="text-sm font-semibold text-[#253746]">Live JSON Payload Response</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <div className="text-[11px] font-semibold text-[#5D6A75] mb-1">GET /api/v1/health/live</div>
            <pre className="text-xs bg-slate-900 text-slate-200 p-3 rounded-lg overflow-x-auto font-mono">
              {JSON.stringify(liveness, null, 2) || '// No response from liveness endpoint'}
            </pre>
          </div>
          <div>
            <div className="text-[11px] font-semibold text-[#5D6A75] mb-1">GET /api/v1/health/ready</div>
            <pre className="text-xs bg-slate-900 text-slate-200 p-3 rounded-lg overflow-x-auto font-mono">
              {JSON.stringify(readiness, null, 2) || '// No response from readiness endpoint'}
            </pre>
          </div>
        </div>
      </Card>
    </div>
  );
};
