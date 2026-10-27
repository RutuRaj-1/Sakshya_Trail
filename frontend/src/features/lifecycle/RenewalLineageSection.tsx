import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  GitCommit,
  GitBranch,
  RefreshCw,
  PlusCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Info,
  Calendar,
  History,
  X,
  ExternalLink,
} from 'lucide-react';
import { lifecycleApi } from '@/api/endpoints';
import type {
  LineageTreeResponse,
  ContinuityAssessmentResponse,
  RenewalCreateSuccessorRequest,
  LineageCorrectionRequest,
} from '@/types/lifecycle';
import { formatINR, formatDate } from '@/lib/utils';
import { Badge } from '@/components/common/Badge';

interface RenewalLineageSectionProps {
  instrumentId: string;
  predecessorRecord: {
    id: string;
    reference_number: string;
    bank_name: string;
    branch?: string | null;
    amount: string | number;
    currency?: string;
    issue_date?: string | null;
    maturity_date?: string | null;
    status: string;
    trust_level: string;
    institution_id: string;
  };
  canInitiateRenewal: boolean;
  isOfficerOrAdmin: boolean;
  onRefreshParent?: () => void;
}

export const RenewalLineageSection: React.FC<RenewalLineageSectionProps> = ({
  instrumentId,
  predecessorRecord,
  canInitiateRenewal,
  isOfficerOrAdmin,
  onRefreshParent,
}) => {
  const [lineageTree, setLineageTree] = useState<LineageTreeResponse | null>(null);
  const [continuity, setContinuity] = useState<ContinuityAssessmentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Renewal Modal
  const [isRenewalModalOpen, setIsRenewalModalOpen] = useState(false);
  const [isDraftLoading, setIsDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formValues, setFormValues] = useState<{
    reference_number: string;
    bank_name: string;
    branch: string;
    amount: string;
    currency: string;
    issue_date: string;
    maturity_date: string;
    effective_date: string;
    lien_holder: string;
    lien_details: string;
    joint_with_aicte: boolean;
    reason_or_reference: string;
  }>({
    reference_number: '',
    bank_name: '',
    branch: '',
    amount: '',
    currency: 'INR',
    issue_date: '',
    maturity_date: '',
    effective_date: '',
    lien_holder: 'AICTE Regulation Bureau',
    lien_details: '',
    joint_with_aicte: true,
    reason_or_reference: '',
  });

  // Correction Modal
  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState(false);
  const [correctionLineageId, setCorrectionLineageId] = useState<string>('');
  const [correctionAction, setCorrectionAction] = useState<'DEACTIVATE' | 'SUPERSEDE' | 'UPDATE_REASON'>('DEACTIVATE');
  const [correctionReason, setCorrectionReason] = useState('');
  const [isCorrectionSubmitting, setIsCorrectionSubmitting] = useState(false);

  const loadLineageData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [treeRes, contRes] = await Promise.allSettled([
        lifecycleApi.getLineage(instrumentId),
        lifecycleApi.getContinuity(instrumentId),
      ]);

      if (treeRes.status === 'fulfilled') {
        setLineageTree(treeRes.value);
      }
      if (contRes.status === 'fulfilled') {
        setContinuity(contRes.value);
      } else {
        setContinuity(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load lineage data');
    } finally {
      setIsLoading(false);
    }
  }, [instrumentId]);

  useEffect(() => {
    loadLineageData();
  }, [loadLineageData]);

  const handleOpenRenewalModal = async () => {
    setIsRenewalModalOpen(true);
    setIsDraftLoading(true);
    setDraftError(null);
    try {
      const draft = await lifecycleApi.getRenewalDraft(instrumentId);
      setFormValues({
        reference_number: '',
        bank_name: draft.suggested_fields.bank_name || predecessorRecord.bank_name || '',
        branch: draft.suggested_fields.branch || predecessorRecord.branch || '',
        amount: draft.suggested_fields.amount || String(predecessorRecord.amount) || '',
        currency: draft.suggested_fields.currency || 'INR',
        issue_date: draft.suggested_fields.suggested_issue_date || '',
        maturity_date: draft.suggested_fields.suggested_maturity_date || '',
        effective_date: draft.suggested_fields.suggested_effective_date || draft.suggested_fields.suggested_issue_date || '',
        lien_holder: draft.suggested_fields.lien_holder || 'AICTE Regulation Bureau',
        lien_details: draft.suggested_fields.lien_details || '',
        joint_with_aicte: draft.suggested_fields.joint_with_aicte ?? true,
        reason_or_reference: `Statutory renewal replacement for FDR ${predecessorRecord.reference_number}`,
      });
    } catch (err: any) {
      setDraftError(
        err?.response?.data?.message || err?.message || 'Failed to initiate renewal draft.'
      );
    } finally {
      setIsDraftLoading(false);
    }
  };

  const handleCreateRenewalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValues.reference_number.trim()) {
      alert('Successor FDR Reference Number is required.');
      return;
    }
    if (!formValues.issue_date || !formValues.maturity_date) {
      alert('Issue Date and Maturity Date are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: RenewalCreateSuccessorRequest = {
        bank_name: formValues.bank_name,
        branch: formValues.branch || undefined,
        reference_number: formValues.reference_number.trim(),
        amount: parseFloat(formValues.amount) || Number(predecessorRecord.amount),
        currency: formValues.currency,
        issue_date: formValues.issue_date,
        maturity_date: formValues.maturity_date,
        effective_date: formValues.effective_date || undefined,
        lien_holder: formValues.lien_holder || undefined,
        lien_details: formValues.lien_details || undefined,
        joint_with_aicte: formValues.joint_with_aicte,
        relationship_type: 'RENEWAL',
        reason_or_reference: formValues.reason_or_reference || undefined,
      };

      await lifecycleApi.createSuccessorRenewal(instrumentId, payload);
      setIsRenewalModalOpen(false);
      await loadLineageData();
      if (onRefreshParent) onRefreshParent();
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Renewal successor creation failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!correctionReason.trim() || correctionReason.trim().length < 5) {
      alert('A detailed audit explanation (at least 5 characters) is mandatory for lineage corrections.');
      return;
    }

    setIsCorrectionSubmitting(true);
    try {
      const payload: LineageCorrectionRequest = {
        action: correctionAction,
        reason: correctionReason.trim(),
      };
      await lifecycleApi.correctLineage(correctionLineageId, payload);
      setIsCorrectionModalOpen(false);
      setCorrectionReason('');
      await loadLineageData();
      if (onRefreshParent) onRefreshParent();
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Lineage correction failed.');
    } finally {
      setIsCorrectionSubmitting(false);
    }
  };

  const hasAncestors = Boolean(lineageTree?.ancestors && lineageTree.ancestors.length > 0);
  const hasSuccessors = Boolean(lineageTree?.successors && lineageTree.successors.length > 0);
  const hasLineage = hasAncestors || hasSuccessors;

  return (
    <div className="bg-white rounded-none border border-slate-200 shadow-2xs overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-none bg-indigo-50 border border-indigo-200 text-indigo-700">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-800">Renewal & Predecessor/Successor Lineage</h3>
              <span className="font-mono text-[9px] uppercase bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-none font-semibold border border-indigo-200">
                Module 5 Prompt 4
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Statutory renewal chain tracking, immutable predecessor retention, and policy-governed gap/overlap assessment.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadLineageData}
            disabled={isLoading}
            className="p-1.5 rounded-none border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
            title="Refresh Lineage"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {canInitiateRenewal && !hasSuccessors && (
            <button
              onClick={handleOpenRenewalModal}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-none font-semibold text-xs transition-colors shadow-2xs"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Start Renewal / Replacement</span>
            </button>
          )}
        </div>
      </div>

      <div className="p-5 space-y-6">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-none text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Core Renewal Principle Advisory */}
        <div className="p-4 rounded-none border border-indigo-100 bg-indigo-50/40 text-[11px] text-slate-600 flex items-start gap-3">
          <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-indigo-900">
              Core Renewal Principle: Autonomous Successor Record
            </p>
            <p className="text-slate-600">
              A renewal creates a new successor instrument. Predecessors retain their original deposit fields,
              uploaded documents, Module 3 findings, and historical trust level. Linking does{' '}
              <strong className="text-slate-800">not</strong> copy L2/L3 verification status or release the predecessor.
            </p>
          </div>
        </div>

        {/* Visual Lineage Chain / Timeline */}
        {isLoading ? (
          <div className="py-8 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
            <p className="text-xs">Analyzing lineage graph & continuity...</p>
          </div>
        ) : !hasLineage ? (
          <div className="p-8 border-2 border-dashed border-slate-200 rounded-none text-center bg-slate-50/50">
            <GitCommit className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-700">Root / Standalone Instrument</p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto mt-1">
              This FDR is not currently linked as a successor to any prior deposit, nor has a replacement
              successor been registered yet.
            </p>
            {canInitiateRenewal && (
              <button
                onClick={handleOpenRenewalModal}
                className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-none font-semibold text-xs transition-colors"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Initiate Renewal Draft for this FDR</span>
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <h4 className="font-bold text-slate-700 text-xs flex items-center gap-2">
              <History className="w-3.5 h-3.5 text-indigo-600" />
              <span>Lineage Chain & Deposit Progression</span>
            </h4>

            {/* Tree Nodes List */}
            <div className="relative border-l-2 border-indigo-200 ml-4 pl-5 space-y-4">
              {/* Ancestors */}
              {lineageTree?.ancestors.map((item) => (
                <div key={item.instrument_id} className="relative">
                  <div className="absolute -left-[27px] top-2 w-3.5 h-3.5 rounded-full bg-slate-400 border-2 border-white ring-2 ring-slate-300" />
                  <div className="p-3.5 rounded-none border border-slate-200 bg-slate-50/80 hover:bg-slate-100/80 transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] uppercase font-bold text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded-none">
                          Predecessor (Depth -{item.depth})
                        </span>
                        <Link
                          to={`/instruments/${item.instrument_id}`}
                          className="font-bold text-xs text-indigo-700 hover:text-indigo-900 inline-flex items-center gap-1"
                        >
                          <span>{item.reference_number}</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </div>
                      <Badge variant="outline">
                        {item.status}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-600">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Bank</span>
                        <span className="font-medium text-slate-800">{item.bank_name}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Amount</span>
                        <span className="font-semibold text-slate-800">{formatINR(Number(item.amount))}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Maturity</span>
                        <span>{item.maturity_date ? formatDate(item.maturity_date) : '—'}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Trust Level</span>
                        <span className="font-mono text-[10px] font-bold text-purple-700">{item.trust_level}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Current Instrument Node */}
              <div className="relative">
                <div className="absolute -left-[29px] top-2 w-4 h-4 rounded-full bg-indigo-600 border-2 border-white ring-2 ring-indigo-400 shadow-sm" />
                <div className="p-4 rounded-none border-2 border-indigo-500 bg-indigo-50/30 shadow-2xs">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] uppercase font-bold text-white bg-indigo-600 px-2 py-0.5 rounded-none shadow-2xs">
                        Current FDR Record
                      </span>
                      <span className="font-bold text-xs text-slate-900">
                        {predecessorRecord.reference_number}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-none bg-white text-purple-800 border border-purple-200">
                        {predecessorRecord.trust_level}
                      </span>
                      <Badge variant="default">
                        {predecessorRecord.status}
                      </Badge>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px] text-slate-700">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Bank / Branch</span>
                      <span className="font-medium">{predecessorRecord.bank_name}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Principal Amount</span>
                      <span className="font-bold text-slate-900">{formatINR(Number(predecessorRecord.amount))}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Maturity Date</span>
                      <span className="font-medium">
                        {predecessorRecord.maturity_date ? formatDate(predecessorRecord.maturity_date) : '—'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Link Status</span>
                      <span className="font-medium text-indigo-700">
                        {hasSuccessors ? 'Superceded by Successor' : hasAncestors ? 'Active Successor' : 'Standalone'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Successors */}
              {lineageTree?.successors.map((item) => (
                <div key={item.instrument_id} className="relative">
                  <div className="absolute -left-[27px] top-2 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-white ring-2 ring-emerald-300" />
                  <div className="p-3.5 rounded-none border border-emerald-200 bg-emerald-50/30 hover:bg-emerald-50/60 transition-colors">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] uppercase font-bold text-emerald-800 bg-emerald-100 px-1.5 py-0.5 rounded-none border border-emerald-200">
                          Successor Deposit (+{item.depth})
                        </span>
                        <Link
                          to={`/instruments/${item.instrument_id}`}
                          className="font-bold text-xs text-emerald-800 hover:text-emerald-950 inline-flex items-center gap-1"
                        >
                          <span>{item.reference_number}</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-bold text-purple-700 bg-white px-1.5 py-0.5 rounded-none border border-purple-200">
                          {item.trust_level}
                        </span>
                        <Badge variant="outline">
                          {item.status}
                        </Badge>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-600">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Bank</span>
                        <span className="font-medium text-slate-800">{item.bank_name}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Amount</span>
                        <span className="font-semibold text-slate-800">{formatINR(Number(item.amount))}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Maturity</span>
                        <span>{item.maturity_date ? formatDate(item.maturity_date) : '—'}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Verification Desk</span>
                        <Link
                          to={`/verification/${item.instrument_id}`}
                          className="text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center gap-0.5"
                        >
                          <span>Scrutiny & Bank L3</span>
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Direct Lineage Link Details & Correction Action */}
            {lineageTree?.direct_successor_lineage && (
              <div className="mt-3 p-3.5 rounded-none border border-slate-200 bg-slate-50 flex items-center justify-between text-[11px]">
                <div className="space-y-0.5">
                  <span className="text-slate-500 font-medium">Link Reason / Statutory Memo:</span>
                  <p className="font-semibold text-slate-800">
                    {lineageTree.direct_successor_lineage.reason_or_reference || 'Statutory renewal continuity link.'}
                  </p>
                  <span className="text-[10px] text-slate-400">
                    Created at: {formatDate(lineageTree.direct_successor_lineage.created_at)} | Concurrency Version:{' '}
                    {lineageTree.direct_successor_lineage.concurrency_version}
                  </span>
                </div>

                {isOfficerOrAdmin && (
                  <button
                    onClick={() => {
                      setCorrectionLineageId(lineageTree.direct_successor_lineage!.id);
                      setIsCorrectionModalOpen(true);
                    }}
                    className="px-2.5 py-1 text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-100 rounded-none font-medium text-[11px] transition-colors"
                  >
                    Manage / Correct Edge
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Gap / Overlap Continuity Assessment Card */}
        {continuity && (
          <div className="p-4 rounded-none border border-slate-200 bg-slate-50/70 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-indigo-600" />
                <h4 className="font-bold text-slate-800 text-xs">Continuity & Gap/Overlap Assessment</h4>
              </div>

              {/* Outcome Badge */}
              {continuity.outcome === 'CONTINUITY_WITHIN_CONFIGURED_TOLERANCE' && (
                <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-none bg-emerald-100 text-emerald-800 border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>Within Tolerance</span>
                </span>
              )}
              {continuity.outcome === 'POTENTIAL_GAP' && (
                <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-none bg-amber-100 text-amber-800 border border-amber-200">
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                  <span>Potential Validity Gap ({continuity.gap_days} Days)</span>
                </span>
              )}
              {continuity.outcome === 'POTENTIAL_OVERLAP' && (
                <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-none bg-blue-100 text-blue-800 border border-blue-200">
                  <Info className="w-3 h-3 text-blue-600" />
                  <span>Overlap Detected ({continuity.overlap_days} Days)</span>
                </span>
              )}
              {continuity.outcome === 'CONTINUITY_UNDETERMINED' && (
                <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-none bg-slate-200 text-slate-800 border border-slate-300">
                  <Clock className="w-3 h-3 text-slate-600" />
                  <span>Continuity Undetermined</span>
                </span>
              )}
              {continuity.outcome === 'POLICY_UNCONFIGURED' && (
                <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded-none bg-rose-100 text-rose-800 border border-rose-200">
                  <AlertTriangle className="w-3 h-3 text-rose-600" />
                  <span>Policy Unconfigured</span>
                </span>
              )}
            </div>

            <p className="text-[11px] text-slate-600 leading-relaxed">{continuity.explanation}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px] pt-1 border-t border-slate-200/70">
              <div>
                <span className="text-slate-400 block text-[10px]">Predecessor Maturity</span>
                <span className="font-semibold text-slate-800">
                  {continuity.dates_compared.predecessor_maturity
                    ? formatDate(continuity.dates_compared.predecessor_maturity)
                    : '—'}
                </span>
                <span className="text-[9px] text-slate-400 block font-mono">
                  {continuity.date_source_fields.predecessor}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Successor Comparison Date</span>
                <span className="font-semibold text-slate-800">
                  {continuity.dates_compared.successor_comparison_date
                    ? formatDate(continuity.dates_compared.successor_comparison_date)
                    : '—'}
                </span>
                <span className="text-[9px] text-slate-400 block font-mono">
                  {continuity.date_source_fields.successor}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Comparison Semantics</span>
                <span className="font-mono text-[10px] text-slate-700 block truncate">
                  {continuity.comparison_semantics}
                </span>
                {continuity.is_provisional && (
                  <span className="text-[9px] text-amber-600 font-semibold">(Provisional proxy)</span>
                )}
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Finding Engine</span>
                <span className="font-medium text-slate-800">
                  {continuity.finding_id ? (
                    <span className="text-amber-700 font-bold">Module 3 Finding Linked</span>
                  ) : (
                    <span className="text-slate-500">No Discrepancy</span>
                  )}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Independent Trust & Document Scrutiny Warning */}
        <div className="p-4 rounded-none border border-amber-200 bg-amber-50/50 space-y-2">
          <div className="flex items-center gap-2 text-amber-900 font-bold text-xs">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>Successor Trust & Documentation Obligations</span>
          </div>
          <p className="text-[11px] text-amber-800 leading-relaxed">
            Registering or linking a successor does <strong>not</strong> certify the renewed deposit. The successor
            starts at <strong>L0_DECLARED</strong> and requires independent Module 2 document upload, Module 3 OCR
            consistency scrutiny, and Module 4 bank host-to-host confirmation before achieving statutory trust.
          </p>
        </div>
      </div>

      {/* Renewal Creation Modal */}
      {isRenewalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-none border border-slate-200 shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-none bg-indigo-50 border border-indigo-200 text-indigo-700">
                  <RefreshCw className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Initiate Renewal / Replacement FDR</h3>
                  <p className="text-[11px] text-slate-500">
                    Creates brand-new successor instrument linked to predecessor {predecessorRecord.reference_number}.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsRenewalModalOpen(false)}
                className="p-1 rounded-none text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs">
              {isDraftLoading ? (
                <div className="py-12 text-center text-slate-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
                  <p>Resolving active policy and pre-filling predecessor summary...</p>
                </div>
              ) : draftError ? (
                <div className="p-4 rounded-none bg-rose-50 border border-rose-200 text-rose-800 space-y-2">
                  <p className="font-bold">Draft Initialization Blocked</p>
                  <p>{draftError}</p>
                </div>
              ) : (
                <form onSubmit={handleCreateRenewalSubmit} className="space-y-5">
                  {/* Read-Only Predecessor Comparison Banner */}
                  <div className="p-4 rounded-none border border-slate-200 bg-slate-50/80 space-y-2">
                    <span className="font-bold text-[11px] text-slate-500 uppercase tracking-wider block">
                      Predecessor Record (Read-Only Immutable Context)
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                      <div>
                        <span className="text-slate-400 block text-[10px]">Reference</span>
                        <span className="font-semibold text-slate-800">{predecessorRecord.reference_number}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Bank / Branch</span>
                        <span className="font-medium text-slate-800">{predecessorRecord.bank_name}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Current Amount</span>
                        <span className="font-bold text-slate-900">{formatINR(Number(predecessorRecord.amount))}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">Maturity Date</span>
                        <span className="font-semibold text-slate-800">
                          {predecessorRecord.maturity_date ? formatDate(predecessorRecord.maturity_date) : '—'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Successor Fields Form */}
                  <div className="space-y-4">
                    <h4 className="font-bold text-slate-800 text-xs flex items-center gap-2">
                      <PlusCircle className="w-4 h-4 text-indigo-600" />
                      <span>New Successor Instrument Details</span>
                    </h4>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          New FDR Reference Number <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={formValues.reference_number}
                          onChange={(e) => setFormValues({ ...formValues, reference_number: e.target.value })}
                          placeholder="e.g. FDR-2026-RN-9982"
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Principal Amount (INR) <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          required
                          value={formValues.amount}
                          onChange={(e) => setFormValues({ ...formValues, amount: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Bank Name <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={formValues.bank_name}
                          onChange={(e) => setFormValues({ ...formValues, bank_name: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Branch Name / IFSC
                        </label>
                        <input
                          type="text"
                          value={formValues.branch}
                          onChange={(e) => setFormValues({ ...formValues, branch: e.target.value })}
                          placeholder="e.g. Connaught Place Branch"
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Issue Date <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="date"
                          required
                          value={formValues.issue_date}
                          onChange={(e) => setFormValues({ ...formValues, issue_date: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Maturity Date <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="date"
                          required
                          value={formValues.maturity_date}
                          onChange={(e) => setFormValues({ ...formValues, maturity_date: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>

                      <div className="sm:col-span-2">
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Actual Effective / Valid-From Date (Recommended for Strict Continuity Evaluation)
                        </label>
                        <input
                          type="date"
                          value={formValues.effective_date}
                          onChange={(e) => setFormValues({ ...formValues, effective_date: e.target.value })}
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                        <p className="text-[10px] text-slate-400 mt-1">
                          If left blank, the prototype policy may use the issue date as a provisional proxy or flag
                          continuity as undetermined.
                        </p>
                      </div>

                      <div className="sm:col-span-2">
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Relationship Reason / Statutory Memo
                        </label>
                        <input
                          type="text"
                          value={formValues.reason_or_reference}
                          onChange={(e) => setFormValues({ ...formValues, reason_or_reference: e.target.value })}
                          placeholder="e.g. Mandatory statutory 3-year rollover under AICTE Approval Process Handbook"
                          className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                    <p className="text-[10px] text-slate-500">
                      Successor is initialized at <strong>L0_DECLARED</strong>. Predecessor is never cancelled automatically.
                    </p>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setIsRenewalModalOpen(false)}
                        className="px-4 py-2 border border-slate-200 text-slate-700 rounded-none text-xs font-semibold hover:bg-slate-100 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-none text-xs font-semibold transition-colors shadow-2xs flex items-center gap-1.5"
                      >
                        {isSubmitting ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span>Creating & Linking Successor...</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Register & Link Successor</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Lineage Correction Modal */}
      {isCorrectionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-none border border-slate-200 shadow-xl max-w-md w-full p-5 space-y-4 text-xs">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">Correct Lineage Relationship</h3>
              <button
                onClick={() => setIsCorrectionModalOpen(false)}
                className="p-1 rounded-none text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Correction Action
                </label>
                <select
                  value={correctionAction}
                  onChange={(e) => setCorrectionAction(e.target.value as any)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="DEACTIVATE">Deactivate / Cancel Link (Status: CANCELLED)</option>
                  <option value="SUPERSEDE">Supersede Link (Status: SUPERSEDED)</option>
                  <option value="UPDATE_REASON">Update Audit Reason</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Mandatory Audit Explanation <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  rows={3}
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  placeholder="Explain the regulatory or clerical reason for modifying this lineage edge..."
                  className="w-full px-3 py-2 border border-slate-200 rounded-none text-xs focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsCorrectionModalOpen(false)}
                  className="px-3 py-1.5 border border-slate-200 text-slate-700 rounded-none text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCorrectionSubmitting}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-none text-xs font-semibold"
                >
                  {isCorrectionSubmitting ? 'Applying...' : 'Apply Correction'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
