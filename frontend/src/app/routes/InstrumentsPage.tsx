import React, { useEffect, useState } from 'react';
import { InstrumentsList } from '@/features/instruments/InstrumentsList';
import { instrumentsApi } from '@/api/endpoints';
import type { Instrument } from '@/types';

export const InstrumentsPage: React.FC = () => {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const fetchInstruments = async () => {
    setIsLoading(true);
    try {
      const data = await instrumentsApi.list({
        status: statusFilter || undefined,
      });
      setInstruments(data);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInstruments();
  }, [statusFilter]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Security Deposit / FDR Instruments
          </h1>
          <p className="text-xs text-slate-500">
            Lifecycle registry of all submitted, verified, and active bank fixed deposit receipts
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
          >
            <option value="">All Statuses</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_SCRUTINY">Under Scrutiny</option>
            <option value="VERIFIED">Verified</option>
            <option value="ACTIVE">Active</option>
            <option value="MATURED">Matured</option>
            <option value="RELEASED">Released</option>
          </select>
        </div>
      </div>

      <InstrumentsList instruments={instruments} isLoading={isLoading} />
    </div>
  );
};
