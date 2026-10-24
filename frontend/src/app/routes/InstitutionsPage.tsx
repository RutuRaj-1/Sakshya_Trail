import React, { useEffect, useState } from 'react';
import { InstitutionsList } from '@/features/institutions/InstitutionsList';
import { institutionsApi } from '@/api/endpoints';
import type { Institution } from '@/types';
import { Search } from 'lucide-react';

export const InstitutionsPage: React.FC = () => {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const data = await institutionsApi.list();
        setInstitutions(data);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  const filtered = institutions.filter((inst) =>
    inst.name.toLowerCase().includes(search.toLowerCase()) ||
    inst.aicte_id.toLowerCase().includes(search.toLowerCase()) ||
    inst.state.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Registered Institutions
          </h1>
          <p className="text-xs text-slate-500">
            Higher education technical institutions maintaining statutory security deposits with AICTE
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by ID, name or state..."
              className="text-xs border border-slate-300 rounded-lg pl-9 pr-3 py-2 bg-white text-slate-700 w-64 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
            />
          </div>
        </div>
      </div>

      <InstitutionsList institutions={filtered} isLoading={isLoading} />
    </div>
  );
};
