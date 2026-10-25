import React from 'react';
import { Card } from '@/components/common/Card';
import { InstrumentSummary } from '@/types';
import { formatINR } from '@/lib/utils';
import {
  Coins,
  ShieldCheck,
  ClockAlert,
  FileSearch,
  CheckCircle,
} from 'lucide-react';

interface Props {
  summary: InstrumentSummary | null;
  isLoading: boolean;
}

export const InstrumentSummaryCards: React.FC<Props> = ({ summary, isLoading }) => {
  const cards = [
    {
      title: 'Total Held Value',
      value: summary ? formatINR(summary.total_deposit_value) : '₹0',
      subtitle: `${summary?.total_instruments || 0} Total Instruments`,
      icon: Coins,
      color: 'text-[#123B5D] bg-[#EEF6FA] border-[#C4DEED]',
    },
    {
      title: 'Active Deposits',
      value: summary ? summary.active_count.toString() : '0',
      subtitle: 'Currently valid & lien-marked',
      icon: ShieldCheck,
      color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    },
    {
      title: 'Expiring Soon (90 Days)',
      value: summary ? summary.expiring_soon_count.toString() : '0',
      subtitle: 'Renewal notice required',
      icon: ClockAlert,
      color: 'text-amber-700 bg-amber-50 border-amber-200',
    },
    {
      title: 'Under Scrutiny',
      value: summary ? summary.under_scrutiny_count.toString() : '0',
      subtitle: 'Pending officer review',
      icon: FileSearch,
      color: 'text-blue-700 bg-blue-50 border-blue-200',
    },
    {
      title: 'Released / Discharged',
      value: summary ? summary.released_count.toString() : '0',
      subtitle: 'Authorized refunds completed',
      icon: CheckCircle,
      color: 'text-[#253746] bg-[#F5F4EF] border-[#C9D3DB]',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((c, i) => (
        <Card key={i} className="flex flex-col justify-between p-4">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium text-[#5D6A75]">{c.title}</span>
            <div className={`p-2 rounded-lg border ${c.color}`}>
              <c.icon className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold tracking-tight text-[#0D2538]">
              {isLoading ? (
                <div className="h-6 w-20 bg-slate-200 rounded animate-pulse" />
              ) : (
                c.value
              )}
            </div>
            <div className="text-[11px] text-[#5D6A75] mt-0.5">{c.subtitle}</div>
          </div>
        </Card>
      ))}
    </div>
  );
};
