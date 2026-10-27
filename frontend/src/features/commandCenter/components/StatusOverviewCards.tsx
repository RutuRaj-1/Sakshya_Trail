import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  ClockAlert,
  AlertOctagon,
  RefreshCw,
  FolderCheck,
  FileClock,
  ArrowUpRight,
} from 'lucide-react';
import type { StatusCountsResponse } from '@/types/commandCenter';
import { formatINR } from '@/lib/utils';

interface StatusOverviewCardsProps {
  data: StatusCountsResponse | null;
  isLoading: boolean;
  onOpenDictionary?: (metricId: string) => void;
}

export const StatusOverviewCards: React.FC<StatusOverviewCardsProps> = ({
  data,
  isLoading,
  onOpenDictionary,
}) => {
  const navigate = useNavigate();

  const cards = [
    {
      metricId: 'MTR-STAT-ACTIVE',
      title: 'Active Instruments',
      count: data?.active_count ?? 0,
      description: `Beyond ${data?.window_days ?? 90}d window`,
      icon: CheckCircle2,
      borderClass: 'border-emerald-200/80 hover:border-emerald-400',
      bgClass: 'bg-emerald-500/5',
      badgeClass: 'bg-emerald-100 text-emerald-800',
      iconClass: 'text-emerald-600',
      navFilter: 'ACTIVE',
    },
    {
      metricId: 'MTR-STAT-EXPIRING-SOON',
      title: 'Expiring Soon',
      count: data?.expiring_soon_count ?? 0,
      description: `Within next ${data?.window_days ?? 90} days`,
      icon: ClockAlert,
      borderClass: 'border-amber-200/80 hover:border-amber-400',
      bgClass: 'bg-amber-500/5',
      badgeClass: 'bg-amber-100 text-amber-800',
      iconClass: 'text-amber-600',
      navFilter: 'EXPIRING_SOON',
    },
    {
      metricId: 'MTR-STAT-MATURED',
      title: 'Matured Instruments',
      count: data?.matured_count ?? 0,
      description: 'Term elapsed, awaiting action',
      icon: AlertOctagon,
      borderClass: 'border-rose-200/80 hover:border-rose-400',
      bgClass: 'bg-rose-500/5',
      badgeClass: 'bg-rose-100 text-rose-800',
      iconClass: 'text-rose-600',
      navFilter: 'MATURED',
    },
    {
      metricId: 'MTR-STAT-RENEWED',
      title: 'Renewed / Replaced',
      count: data?.renewed_count ?? 0,
      description: 'Active successor in lineage',
      icon: RefreshCw,
      borderClass: 'border-blue-200/80 hover:border-blue-400',
      bgClass: 'bg-blue-500/5',
      badgeClass: 'bg-blue-100 text-blue-800',
      iconClass: 'text-blue-600',
      navFilter: 'RENEWED',
    },
    {
      metricId: 'MTR-STAT-RELEASED',
      title: 'Released Deposits',
      count: data?.released_count ?? 0,
      description: 'Discharged by authority order',
      icon: FolderCheck,
      borderClass: 'border-purple-200/80 hover:border-purple-400',
      bgClass: 'bg-purple-500/5',
      badgeClass: 'bg-purple-100 text-purple-800',
      iconClass: 'text-purple-600',
      navFilter: 'RELEASED',
    },
    {
      metricId: 'MTR-STAT-PENDING',
      title: 'Pending Review / Draft',
      count: data?.pending_count ?? 0,
      description: 'Intake or deficiency review',
      icon: FileClock,
      borderClass: 'border-[#8799A9] hover:border-slate-400',
      bgClass: 'bg-[#F5F4EF]0/5',
      badgeClass: 'bg-slate-200 text-[#253746]',
      iconClass: 'text-[#5D6A75]',
      navFilter: 'UNDER_SCRUTINY',
    },
  ];

  return (
    <section aria-labelledby="status-overview-heading" className="space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 id="status-overview-heading" className="text-base font-semibold text-[#0D2538] flex items-center gap-2">
            <span>Administrative Status Overview</span>
            <span className="text-xs font-mono font-normal text-[#5D6A75] bg-slate-100 px-2 py-0.5 rounded-none border border-[#C9D3DB]">
              PRD-FR-070a
            </span>
          </h2>
          <p className="text-xs text-[#5D6A75]">
            Strict separation between administrative state, trust level, and release eligibility.
          </p>
        </div>
        {data && (
          <div className="text-xs text-[#5D6A75] bg-slate-100 px-3 py-1.5 rounded-none border border-[#C9D3DB] flex items-center gap-3">
            <span>
              Total Scope: <strong className="text-[#0D2538]">{data.total_instruments}</strong> FDRs
            </span>
            <span className="text-slate-300">|</span>
            <span>
              Total Value: <strong className="text-[#0D2538]">{formatINR(data.total_deposit_value)}</strong>
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.metricId}
              onClick={() => navigate(`/instruments?status=${encodeURIComponent(card.navFilter)}`)}
              className={`rounded-none border p-4 bg-white shadow-xs cursor-pointer transition-all duration-150 relative overflow-hidden group select-none ${card.borderClass} ${card.bgClass}`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  navigate(`/instruments?status=${encodeURIComponent(card.navFilter)}`);
                }
              }}
              aria-label={`View ${card.title} - ${card.count} records`}
            >
              <div className="flex items-start justify-between">
                <div className="p-2 rounded-none bg-white shadow-xs border border-slate-100">
                  <Icon className={`w-4 h-4 ${card.iconClass}`} />
                </div>
                <div className="flex items-center gap-1">
                  {onOpenDictionary && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenDictionary(card.metricId);
                      }}
                      className="text-[10px] text-slate-400 hover:text-[#253746] p-0.5"
                      title="Inspect Metric Definition (PRD-FR-077)"
                      aria-label={`Inspect ${card.title} definition`}
                    >
                      ℹ️
                    </button>
                  )}
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#253746] transition-colors" />
                </div>
              </div>

              <div className="mt-3">
                <div className="text-2xl font-bold text-[#0D2538] tracking-tight">
                  {isLoading ? (
                    <div className="h-7 w-12 bg-slate-200 animate-pulse rounded-none" />
                  ) : (
                    card.count
                  )}
                </div>
                <div className="text-xs font-semibold text-[#253746] mt-1 line-clamp-1">
                  {card.title}
                </div>
                <div className="text-[11px] text-[#5D6A75] mt-0.5 line-clamp-1">
                  {card.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
