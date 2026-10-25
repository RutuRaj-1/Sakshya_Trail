import React, { useState, useEffect } from 'react';
import { X, BookOpen, Search } from 'lucide-react';
import { commandCenterApi } from '@/api/commandCenter';
import type { MetricDefinition } from '@/types/commandCenter';

interface MetricDictionaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedMetricId?: string | null;
}

export const MetricDictionaryModal: React.FC<MetricDictionaryModalProps> = ({
  isOpen,
  onClose,
  selectedMetricId,
}) => {
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [activeMetric, setActiveMetric] = useState<MetricDefinition | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    async function loadDictionary() {
      setIsLoading(true);
      try {
        const res = await commandCenterApi.getMetricDictionary();
        setMetrics(res.metrics);
        if (selectedMetricId) {
          const match = res.metrics.find((m) => m.metric_id === selectedMetricId);
          if (match) setActiveMetric(match);
          else if (res.metrics.length > 0) setActiveMetric(res.metrics[0]);
        } else if (res.metrics.length > 0) {
          setActiveMetric(res.metrics[0]);
        }
      } catch (err) {
        console.error('Failed to load metric dictionary', err);
      } finally {
        setIsLoading(false);
      }
    }

    loadDictionary();
  }, [isOpen, selectedMetricId]);

  if (!isOpen) return null;

  const categories = ['ALL', ...Array.from(new Set(metrics.map((m) => m.category)))];

  const filteredMetrics = metrics.filter((m) => {
    const matchesCat = selectedCategory === 'ALL' || m.category === selectedCategory;
    const matchesSearch =
      !searchTerm ||
      m.metric_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.display_label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="metric-dict-title"
    >
      <div className="bg-white rounded-[10px] shadow-2xl border border-[#C9D3DB] w-full max-w-4xl max-h-[88vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[#C9D3DB] flex items-center justify-between bg-[#F5F4EF]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-[#EEF6FA] text-[#123B5D] rounded-lg">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 id="metric-dict-title" className="text-base sm:text-lg font-bold text-[#0D2538] flex items-center gap-2">
                <span>Command Center Metric Dictionary</span>
                <span className="text-xs font-mono font-normal text-[#5D6A75] bg-white px-2 py-0.5 rounded border border-[#C9D3DB]">
                  PRD-FR-077
                </span>
              </h2>
              <p className="text-xs text-[#5D6A75]">
                Authoritative reference defining calculation formulas, scope, inclusions, and exclusions.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-[#253746] p-1.5 rounded-lg hover:bg-slate-200/50 transition-colors"
            aria-label="Close metric dictionary"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Filter Bar */}
        <div className="p-3 border-b border-slate-100 bg-white flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search metrics by ID, label, or calculation..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-[#C9D3DB] rounded-lg focus:outline-hidden focus:ring-1 focus:ring-sentinel-500"
            />
          </div>
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium whitespace-nowrap transition-all ${
                  selectedCategory === cat
                    ? 'bg-[#123B5D] text-white font-semibold'
                    : 'bg-slate-100 text-[#5D6A75] hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Content Two-Column Layout */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-12">
          {/* List column */}
          <div className="md:col-span-5 border-r border-[#C9D3DB] overflow-y-auto max-h-[50vh] md:max-h-none divide-y divide-slate-100 p-2 space-y-1">
            {isLoading ? (
              <div className="p-6 text-center text-xs text-slate-400">Loading metrics...</div>
            ) : filteredMetrics.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400">No matching metrics found.</div>
            ) : (
              filteredMetrics.map((m) => (
                <div
                  key={m.metric_id}
                  onClick={() => setActiveMetric(m)}
                  className={`p-2.5 rounded-lg cursor-pointer transition-colors text-left ${
                    activeMetric?.metric_id === m.metric_id
                      ? 'bg-[#EEF6FA] border border-[#C4DEED] shadow-2xs'
                      : 'hover:bg-[#F5F4EF] border border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold text-[#0D2538]">
                      {m.metric_id}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.2 rounded">
                      {m.prd_mapping}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-[#0D2538] mt-1">{m.display_label}</div>
                  <div className="text-[11px] text-[#5D6A75] line-clamp-1 mt-0.5">{m.description}</div>
                </div>
              ))
            )}
          </div>

          {/* Detail column */}
          <div className="md:col-span-7 overflow-y-auto p-4 sm:p-5 bg-white space-y-4">
            {activeMetric ? (
              <div className="space-y-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold bg-[#EEF6FA] text-[#0D2538] px-2 py-0.5 rounded">
                      {activeMetric.metric_id}
                    </span>
                    <span className="text-xs font-mono text-[#5D6A75] bg-slate-100 px-2 py-0.5 rounded border border-[#C9D3DB]">
                      {activeMetric.prd_mapping}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-[#0D2538] mt-2">{activeMetric.display_label}</h3>
                  <p className="text-xs text-[#5D6A75] mt-1 leading-relaxed">{activeMetric.description}</p>
                </div>

                <div className="bg-slate-900 text-slate-200 rounded-lg p-3 font-mono text-xs space-y-1">
                  <div className="text-slate-400 text-[10px] uppercase tracking-wider font-semibold">
                    Calculation Rule:
                  </div>
                  <div className="overflow-x-auto text-[11px] text-emerald-400">{activeMetric.calculation_rule}</div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="bg-[#F5F4EF] p-3 rounded-lg border border-slate-100">
                    <span className="font-semibold text-[#253746] block mb-1">Inclusion Criteria:</span>
                    <span className="text-[#5D6A75] text-[11px] leading-relaxed">{activeMetric.inclusion_criteria}</span>
                  </div>
                  <div className="bg-[#F5F4EF] p-3 rounded-lg border border-slate-100">
                    <span className="font-semibold text-[#253746] block mb-1">Exclusion Criteria:</span>
                    <span className="text-[#5D6A75] text-[11px] leading-relaxed">{activeMetric.exclusion_criteria}</span>
                  </div>
                </div>

                <div className="space-y-2 text-xs border-t border-slate-100 pt-3">
                  <div className="flex justify-between">
                    <span className="text-[#5D6A75]">Date & Timezone Basis:</span>
                    <span className="font-mono text-[#253746] text-[11px]">{activeMetric.date_basis}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5D6A75]">Authorization Scope:</span>
                    <span className="text-[#253746] text-[11px] text-right max-w-72">{activeMetric.authorization_scope}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5D6A75]">Unconfigured Policy Handling:</span>
                    <span className="text-[#253746] text-[11px] text-right max-w-72">{activeMetric.unconfigured_handling}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#5D6A75]">REST API Endpoint:</span>
                    <code className="font-mono text-[#123B5D] text-[11px]">{activeMetric.api_endpoint}</code>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                Select a metric from the left list to view specifications.
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[#C9D3DB] bg-[#F5F4EF] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs bg-slate-900 text-white font-medium rounded-lg hover:bg-slate-800 transition"
          >
            Close Dictionary
          </button>
        </div>
      </div>
    </div>
  );
};
