import React, { useEffect, useState } from 'react';
import { InstrumentsList } from '@/features/instruments/InstrumentsList';
import { instrumentsApi, dashboardApi } from '@/api/endpoints';
import type { Instrument, DashboardSummary } from '@/types';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { formatINR } from '@/lib/utils';
import { useAuth } from '@/features/auth/AuthContext';
import {
  FileText,
  Building2,
  Coins,
  ShieldCheck,
  ClockAlert,
  Users,
  KeyRound,
  Shield,
  Layers,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'SYSTEM_ADMIN';
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [sumRes, listRes] = await Promise.allSettled([
          dashboardApi.getSummary(),
          instrumentsApi.list({ limit: 10 }),
        ]);
        if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
        if (listRes.status === 'fulfilled') setInstruments(listRes.value.items);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-linear-to-r from-sentinel-950 via-slate-900 to-slate-850 rounded-2xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden border border-slate-800">
        <div className="relative z-10 max-w-3xl">
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-sentinel-500/20 text-sentinel-300 border border-sentinel-400/30 text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">
              {isInstitutionUser ? 'Institutional Portal' : 'AICTE Regulation Bureau'}
            </span>
            <span className="text-slate-400 text-xs font-mono">Module 1 Baseline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            {isInstitutionUser ? 'Security Deposit Management Vault' : 'FDR Sentinel — Security Deposit & FDR Governance'}
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            Authoritative registry for statutory Fixed Deposit Receipts (FDRs) and institutional security deposits.
            Enforcing strict multi-tenant isolation, tiered evidentiary trust (L0–L3), and tamper-evident audit scrutiny.
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-5">
            <Link to="/instruments">
              <Button size="sm" className="bg-sentinel-500 hover:bg-sentinel-600 text-white shadow-sm">
                <FileText className="w-4 h-4 mr-1.5" /> View FDR Registry
              </Button>
            </Link>
            <Link to="/institutions">
              <Button size="sm" variant="outline" className="border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700">
                <Building2 className="w-4 h-4 mr-1.5" /> Institutions Directory
              </Button>
            </Link>
            {isSystemAdmin && (
              <Link to="/users">
                <Button size="sm" variant="outline" className="border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700">
                  <Users className="w-4 h-4 mr-1.5" /> User Administration
                </Button>
              </Link>
            )}
            <Link to="/change-password">
              <Button size="sm" variant="ghost" className="text-slate-300 hover:text-white hover:bg-slate-800">
                <KeyRound className="w-4 h-4 mr-1.5" /> Password Security
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Primary KPI Strip */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            {isInstitutionUser ? 'My Institution Overview' : 'Bureau-wide Operational Overview'}
          </h2>
          <span className="text-xs text-slate-400">Scoped live metrics</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Total Held Value */}
          <Card className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-sentinel-50 text-sentinel-700 border border-sentinel-200">
              <Coins className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Held Value</p>
              <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                {isLoading ? '...' : formatINR(summary?.total_deposit_value || '0')}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {summary?.total_instruments || 0} Total Instruments
              </p>
            </div>
          </Card>

          {/* Card 2: Active Institutions */}
          <Card className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-blue-50 text-blue-700 border border-blue-200">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {isInstitutionUser ? 'Affiliated Institution' : 'Active Institutions'}
              </p>
              <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                {isLoading ? '...' : summary?.total_active_institutions || 0}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {summary?.total_inactive_institutions || 0} Historical / Inactive
              </p>
            </div>
          </Card>

          {/* Card 3: Registered Instruments */}
          <Card className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Registered FDRs</p>
              <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                {isLoading ? '...' : (summary?.instruments_by_status?.REGISTERED || 0)}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {summary?.instruments_by_status?.DRAFT || 0} Draft records
              </p>
            </div>
          </Card>

          {/* Card 4: Approaching Maturity */}
          <Card className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
              <ClockAlert className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Expiring Soon</p>
              <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                {isLoading ? '...' : summary?.instruments_approaching_maturity || 0}
              </h3>
              <p className="text-[11px] text-amber-700 mt-0.5">
                Maturing in ≤ 90 days
              </p>
            </div>
          </Card>
        </div>
      </section>

      {/* Concept Breakdown: Administrative Status & Trust Level Distribution */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Administrative Status Distribution */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-slate-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Administrative Status Distribution
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200/80">
              <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">REGISTERED</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {summary?.instruments_by_status?.REGISTERED || 0}
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">Formal statutory records</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">DRAFT</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {summary?.instruments_by_status?.DRAFT || 0}
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">In-progress institutional entries</p>
            </div>
          </div>
        </Card>

        {/* Evidentiary Trust Level Distribution */}
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-slate-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Evidentiary Trust Tiers
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="p-2.5 rounded-lg bg-slate-100 border border-slate-200">
              <span className="text-[10px] font-bold text-slate-600 block">L0 DECLARED</span>
              <span className="text-lg font-bold text-slate-900 block mt-0.5">
                {summary?.instruments_by_trust_level?.L0_DECLARED || 0}
              </span>
              <span className="text-[9px] text-slate-400">Baseline</span>
            </div>
            <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200">
              <span className="text-[10px] font-bold text-blue-700 block">L1 DOC OK</span>
              <span className="text-lg font-bold text-slate-900 block mt-0.5">
                {summary?.instruments_by_trust_level?.L1_DOCUMENT_CONSISTENT || 0}
              </span>
              <span className="text-[9px] text-slate-400">Module 2</span>
            </div>
            <div className="p-2.5 rounded-lg bg-purple-50 border border-purple-200">
              <span className="text-[10px] font-bold text-purple-700 block">L2 VERIFIED</span>
              <span className="text-lg font-bold text-slate-900 block mt-0.5">
                {summary?.instruments_by_trust_level?.L2_OFFICER_VERIFIED || 0}
              </span>
              <span className="text-[9px] text-slate-400">Module 3</span>
            </div>
            <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200">
              <span className="text-[10px] font-bold text-emerald-700 block">L3 BANK CONF</span>
              <span className="text-lg font-bold text-slate-900 block mt-0.5">
                {summary?.instruments_by_trust_level?.L3_BANK_CONFIRMED || 0}
              </span>
              <span className="text-[9px] text-slate-400">Module 4</span>
            </div>
          </div>
        </Card>
      </section>

      {/* Recent Instruments Table */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Recent Security Deposits</h2>
            <p className="text-xs text-slate-500">
              Active instruments monitored for lien marking, validity dates, and maturity
            </p>
          </div>
          <Link to="/instruments">
            <Button size="sm" variant="outline">
              View All Instruments
            </Button>
          </Link>
        </div>

        <InstrumentsList
          instruments={instruments.slice(0, 5)}
          isLoading={isLoading}
        />
      </section>
    </div>
  );
};
