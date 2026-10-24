import React, { useEffect, useState } from 'react';
import { InstrumentSummaryCards } from '@/features/instruments/InstrumentSummaryCards';
import { InstrumentsList } from '@/features/instruments/InstrumentsList';
import { instrumentsApi } from '@/api/endpoints';
import type { Instrument, InstrumentSummary } from '@/types';
import { Button } from '@/components/common/Button';
import {
  FileText,
  Building2,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<InstrumentSummary | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [sumRes, listRes] = await Promise.allSettled([
          instrumentsApi.getSummary(),
          instrumentsApi.list(),
        ]);
        if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
        if (listRes.status === 'fulfilled') setInstruments(listRes.value);
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
              AICTE Regulation Bureau
            </span>
            <span className="text-slate-400 text-xs font-mono">PS ID: 26265</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            FDR Sentinel — Security Deposit & FDR Lifecycle Integrity
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            Centralized digital governance for Fixed Deposit Receipts (FDRs) and institutional security deposits.
            Ensuring explicit trust provenance (L1–L4), automated maturity monitoring, and tamper-evident audit scrutiny.
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-5">
            <Link to="/instruments">
              <Button size="sm" className="bg-sentinel-500 hover:bg-sentinel-600 text-white">
                <FileText className="w-4 h-4 mr-1.5" /> View FDR Registry
              </Button>
            </Link>
            <Link to="/institutions">
              <Button size="sm" variant="outline" className="border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700">
                <Building2 className="w-4 h-4 mr-1.5" /> Institution Directory
              </Button>
            </Link>
            <Link to="/health">
              <Button size="sm" variant="ghost" className="text-slate-300 hover:text-white hover:bg-slate-800">
                Database Diagnostics <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            Portfolio Overview
          </h2>
          <span className="text-xs text-slate-400">Live regulatory metrics</span>
        </div>
        <InstrumentSummaryCards summary={summary} isLoading={isLoading} />
      </section>

      {/* Primary Workspace Section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Recent Security Deposits</h2>
            <p className="text-xs text-slate-500">
              Active instruments monitored for lien, validity, and maturity
            </p>
          </div>
          <Link to="/instruments">
            <Button size="sm" variant="outline">
              View All ({instruments.length})
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
