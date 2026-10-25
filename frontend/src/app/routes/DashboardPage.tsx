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
  SlidersHorizontal,
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
      {/* Top Banner - Structured Brutalism Hero */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 sm:p-8 text-white shadow-[0_1px_3px_rgba(13,37,56,0.08)] relative overflow-hidden border border-[#1e3c54]">
        <div className="relative z-10 max-w-3xl">
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[11px] font-semibold px-2.5 py-0.5 rounded-[4px] uppercase tracking-wider font-mono">
              {isInstitutionUser ? 'Institutional Portal' : 'Regulatory Bureau'}
            </span>
            <span className="text-[#8799A9] text-xs font-mono">SIH 26265</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            {isInstitutionUser ? 'Security Deposit Management Vault' : 'SakshyaTrail — Security Deposit & FDR Governance'}
          </h1>
          <p className="text-sm sm:text-base text-[#C9D3DB] leading-relaxed">
            Authoritative registry for statutory Fixed Deposit Receipts (FDRs) and institutional security deposits.
            Enforcing strict multi-tenant isolation, tiered evidentiary trust (L0–L3), and tamper-evident audit scrutiny.
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-5">
            <Link to="/command-center">
              <Button size="sm" className="bg-[#0F766E] hover:bg-[#09544E] text-white shadow-2xs font-semibold">
                <SlidersHorizontal className="w-4 h-4 mr-1.5" /> Command Center
              </Button>
            </Link>
            <Link to="/instruments">
              <Button size="sm" variant="outline" className="border-[#8799A9] bg-[#123B5D]/40 text-white hover:bg-[#123B5D]">
                <FileText className="w-4 h-4 mr-1.5" /> View FDR Registry
              </Button>
            </Link>
            <Link to="/institutions">
              <Button size="sm" variant="outline" className="border-[#8799A9] bg-[#123B5D]/40 text-white hover:bg-[#123B5D]">
                <Building2 className="w-4 h-4 mr-1.5" /> Institutions Directory
              </Button>
            </Link>
            {isSystemAdmin && (
              <Link to="/users">
                <Button size="sm" variant="outline" className="border-[#8799A9] bg-[#123B5D]/40 text-white hover:bg-[#123B5D]">
                  <Users className="w-4 h-4 mr-1.5" /> User Administration
                </Button>
              </Link>
            )}
            <Link to="/change-password">
              <Button size="sm" variant="ghost" className="text-[#C9D3DB] hover:text-white hover:bg-[#123B5D]/30">
                <KeyRound className="w-4 h-4 mr-1.5" /> Password Security
              </Button>
            </Link>
          </div>
        </div>
      </div>


      {/* Primary KPI Strip - Structured Brutalism */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#5D6A75]">
            {isInstitutionUser ? 'My Institution Overview' : 'Bureau-wide Operational Overview'}
          </h2>
          <span className="text-xs text-[#5D6A75] font-mono">Scoped live metrics</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Total Held Value */}
          <Card className="p-4 flex items-center gap-4 border-[#C9D3DB]">
            <div className="p-3 rounded-[8px] bg-[#EEF6FA] text-[#123B5D] border border-[#C4DEED]">
              <Coins className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-[#5D6A75] uppercase tracking-wider">Total Held Value</p>
              <h3 className="text-xl font-bold text-[#0D2538] mt-0.5 font-mono">
                {isLoading ? '...' : formatINR(summary?.total_deposit_value || '0')}
              </h3>
              <p className="text-[11px] text-[#5D6A75] mt-0.5">
                {summary?.total_instruments || 0} Total Instruments
              </p>
            </div>
          </Card>

          {/* Card 2: Active Institutions */}
          <Card className="p-4 flex items-center gap-4 border-[#C9D3DB]">
            <div className="p-3 rounded-[8px] bg-[#EEF6FA] text-[#245B7A] border border-[#C4DEED]">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-[#5D6A75] uppercase tracking-wider">
                {isInstitutionUser ? 'Affiliated Institution' : 'Active Institutions'}
              </p>
              <h3 className="text-xl font-bold text-[#0D2538] mt-0.5 font-mono">
                {isLoading ? '...' : summary?.total_active_institutions || 0}
              </h3>
              <p className="text-[11px] text-[#5D6A75] mt-0.5">
                {summary?.total_inactive_institutions || 0} Historical / Inactive
              </p>
            </div>
          </Card>

          {/* Card 3: Registered Instruments */}
          <Card className="p-4 flex items-center gap-4 border-[#C9D3DB]">
            <div className="p-3 rounded-[8px] bg-[#E7F3EC] text-[#18794E] border border-[#B4DFC9]">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-[#5D6A75] uppercase tracking-wider">Registered FDRs</p>
              <h3 className="text-xl font-bold text-[#0D2538] mt-0.5 font-mono">
                {isLoading ? '...' : (summary?.instruments_by_status?.REGISTERED || 0)}
              </h3>
              <p className="text-[11px] text-[#5D6A75] mt-0.5">
                {summary?.instruments_by_status?.DRAFT || 0} Draft records
              </p>
            </div>
          </Card>

          {/* Card 4: Approaching Maturity */}
          <Card className="p-4 flex items-center gap-4 border-[#C9D3DB]">
            <div className="p-3 rounded-[8px] bg-[#FEF7E8] text-[#8A5A00] border border-[#F8DEAE]">
              <ClockAlert className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-[#5D6A75] uppercase tracking-wider">Expiring Soon</p>
              <h3 className="text-xl font-bold text-[#8A5A00] mt-0.5 font-mono">
                {isLoading ? '...' : summary?.instruments_approaching_maturity || 0}
              </h3>
              <p className="text-[11px] text-[#8A5A00] mt-0.5 font-medium">
                Maturing in ≤ 90 days
              </p>
            </div>
          </Card>
        </div>
      </section>

      {/* Concept Breakdown: Administrative Status & Trust Level Distribution */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Administrative Status Distribution */}
        <Card className="p-5 border-[#C9D3DB]">
          <div className="flex items-center gap-2 mb-3">
            <Layers className="w-4 h-4 text-[#123B5D]" />
            <h3 className="text-xs font-bold text-[#0D2538] uppercase tracking-wider">
              Administrative Status Distribution
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-[8px] bg-[#E7F3EC] border border-[#B4DFC9]">
              <span className="text-[11px] font-bold text-[#18794E] uppercase tracking-wider font-mono">REGISTERED</span>
              <p className="text-2xl font-bold text-[#0D2538] mt-1 font-mono">
                {summary?.instruments_by_status?.REGISTERED || 0}
              </p>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">Formal statutory records</p>
            </div>
            <div className="p-3 rounded-[8px] bg-[#F5F4EF] border border-[#C9D3DB]">
              <span className="text-[11px] font-bold text-[#5D6A75] uppercase tracking-wider font-mono">DRAFT</span>
              <p className="text-2xl font-bold text-[#0D2538] mt-1 font-mono">
                {summary?.instruments_by_status?.DRAFT || 0}
              </p>
              <p className="text-[10px] text-[#5D6A75] mt-0.5">In-progress institutional entries</p>
            </div>
          </div>
        </Card>

        {/* Evidentiary Trust Level Distribution */}
        <Card className="p-5 border-[#C9D3DB]">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-[#0F766E]" />
            <h3 className="text-xs font-bold text-[#0D2538] uppercase tracking-wider">
              Evidentiary Trust Tiers (L0–L3)
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="p-2.5 rounded-[6px] bg-[#F5F4EF] border border-[#C9D3DB]">
              <span className="text-[10px] font-bold text-[#5D6A75] block font-mono">L0 DECLARED</span>
              <span className="text-lg font-bold text-[#0D2538] block mt-0.5 font-mono">
                {summary?.instruments_by_trust_level?.L0_DECLARED || 0}
              </span>
              <span className="text-[9px] text-[#8799A9]">Declared Only</span>
            </div>
            <div className="p-2.5 rounded-[6px] bg-[#EEF6FA] border border-[#C4DEED]">
              <span className="text-[10px] font-bold text-[#245B7A] block font-mono">L1 DOC-OK</span>
              <span className="text-lg font-bold text-[#0D2538] block mt-0.5 font-mono">
                {summary?.instruments_by_trust_level?.L1_DOCUMENT_CONSISTENT || 0}
              </span>
              <span className="text-[9px] text-[#5D6A75]">Consistent</span>
            </div>
            <div className="p-2.5 rounded-[6px] bg-[#E6F4F2] border border-[#99D5CE]">
              <span className="text-[10px] font-bold text-[#0F766E] block font-mono">L2 VERIFIED</span>
              <span className="text-lg font-bold text-[#0D2538] block mt-0.5 font-mono">
                {summary?.instruments_by_trust_level?.L2_OFFICER_VERIFIED || 0}
              </span>
              <span className="text-[9px] text-[#0F766E]">Officer Check</span>
            </div>
            <div className="p-2.5 rounded-[6px] bg-[#E7F3EC] border border-[#B4DFC9]">
              <span className="text-[10px] font-bold text-[#18794E] block font-mono">L3 AUTH-RESP</span>
              <span className="text-lg font-bold text-[#0D2538] block mt-0.5 font-mono">
                {summary?.instruments_by_trust_level?.L3_BANK_CONFIRMED || 0}
              </span>
              <span className="text-[9px] text-[#18794E]">Eligible Resp</span>
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
