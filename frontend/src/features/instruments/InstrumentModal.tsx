import React, { useState, useEffect } from 'react';
import { X, FileSpreadsheet, AlertTriangle, Shield, Check, Info } from 'lucide-react';
import type { Instrument, Institution } from '@/types';
import { instrumentsApi, institutionsApi } from '@/api/endpoints';
import { useAuth } from '@/features/auth/AuthContext';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  instrumentToEdit?: Instrument | null;
  defaultInstitutionId?: string;
}

const COMMON_BANKS = [
  'State Bank of India',
  'Bank of Baroda',
  'Canara Bank',
  'Union Bank of India',
  'HDFC Bank',
  'ICICI Bank',
  'Axis Bank',
  'Indian Bank',
  'Central Bank of India',
  'Bank of India',
  'Kotak Mahindra Bank',
];

export const InstrumentModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSuccess,
  instrumentToEdit,
  defaultInstitutionId,
}) => {
  const { user } = useAuth();
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const isEditing = !!instrumentToEdit;

  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [formData, setFormData] = useState(() => ({
    institution_id: defaultInstitutionId || (isInstitutionUser ? user?.institution_id || '' : ''),
    instrument_type: 'FDR',
    bank_name: 'State Bank of India',
    branch: '',
    reference_number: '',
    amount: '',
    currency: 'INR',
    issue_date: new Date().toISOString().split('T')[0],
    maturity_date: new Date(Date.now() + 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    lien_holder: 'AICTE Regulation Bureau',
    lien_details: 'Joint security deposit pledge with Member Secretary, AICTE',
    assigned_office: '',
    remarks: '',
    status: 'REGISTERED',
  }));

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Duplicate Warning State
  const [duplicateWarning, setDuplicateWarning] = useState<{
    message: string;
    matching_records: any[];
  } | null>(null);

  // Load active institutions if user is admin/officer
  useEffect(() => {
    async function fetchInstitutions() {
      try {
        const res = await institutionsApi.list({ is_active: true, limit: 100 });
        setInstitutions(res.items);
      } catch (err) {
        console.error('Failed to load institutions list', err);
      }
    }
    if (isOpen && !isInstitutionUser) {
      fetchInstitutions();
    }
  }, [isOpen, isInstitutionUser]);

  useEffect(() => {
    if (instrumentToEdit) {
      setFormData({
        institution_id: instrumentToEdit.institution_id,
        instrument_type: instrumentToEdit.instrument_type || 'FDR',
        bank_name: instrumentToEdit.bank_name,
        branch: instrumentToEdit.branch || '',
        reference_number: instrumentToEdit.reference_number,
        amount: String(instrumentToEdit.amount),
        currency: instrumentToEdit.currency || 'INR',
        issue_date: instrumentToEdit.issue_date,
        maturity_date: instrumentToEdit.maturity_date,
        lien_holder: instrumentToEdit.lien_holder || 'AICTE Regulation Bureau',
        lien_details: instrumentToEdit.lien_details || '',
        assigned_office: instrumentToEdit.assigned_office || '',
        remarks: instrumentToEdit.remarks || '',
        status: instrumentToEdit.status || 'REGISTERED',
      });
    } else {
      const defaultInst = defaultInstitutionId || (isInstitutionUser ? user?.institution_id || '' : '');
      setFormData({
        institution_id: defaultInst,
        instrument_type: 'FDR',
        bank_name: 'State Bank of India',
        branch: '',
        reference_number: '',
        amount: '',
        currency: 'INR',
        issue_date: new Date().toISOString().split('T')[0],
        maturity_date: new Date(Date.now() + 5 * 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        lien_holder: 'AICTE Regulation Bureau',
        lien_details: 'Joint security deposit pledge with Member Secretary, AICTE',
        assigned_office: '',
        remarks: '',
        status: 'REGISTERED',
      });
    }
    setErrors({});
    setApiError(null);
    setDuplicateWarning(null);
  }, [instrumentToEdit, isOpen, defaultInstitutionId, isInstitutionUser, user]);

  if (!isOpen) return null;

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!formData.institution_id) {
      errs.institution_id = 'Please select a registered institution.';
    }

    if (!formData.bank_name.trim()) {
      errs.bank_name = 'Bank name is mandatory.';
    }

    if (!formData.reference_number.trim()) {
      errs.reference_number = 'FDR reference / receipt certificate number is required.';
    }

    const numAmount = parseFloat(formData.amount);
    if (isNaN(numAmount) || numAmount <= 0) {
      errs.amount = 'Principal amount must be a positive number greater than zero.';
    }

    if (!formData.issue_date) {
      errs.issue_date = 'Issue date is required.';
    }

    if (!formData.maturity_date) {
      errs.maturity_date = 'Maturity date is required.';
    } else if (formData.issue_date && formData.maturity_date <= formData.issue_date) {
      errs.maturity_date = 'Maturity date must be strictly later than issue date.';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const submitInstrument = async (confirmDuplicate: boolean = false) => {
    setIsSubmitting(true);
    setApiError(null);

    try {
      const payload = {
        institution_id: formData.institution_id,
        instrument_type: formData.instrument_type,
        bank_name: formData.bank_name.trim(),
        branch: formData.branch.trim() || undefined,
        reference_number: formData.reference_number.trim().toUpperCase(),
        amount: parseFloat(formData.amount).toFixed(2),
        currency: formData.currency,
        issue_date: formData.issue_date,
        maturity_date: formData.maturity_date,
        lien_holder: formData.lien_holder.trim() || undefined,
        lien_details: formData.lien_details.trim() || undefined,
        assigned_office: formData.assigned_office.trim() || undefined,
        remarks: formData.remarks.trim() || undefined,
        status: formData.status,
        confirm_duplicate: confirmDuplicate,
      };

      if (isEditing && instrumentToEdit) {
        await instrumentsApi.update(instrumentToEdit.id, payload);
      } else {
        await instrumentsApi.create(payload);
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      const respData = err?.data || err?.response?.data;
      if (respData?.code === 'DUPLICATE_REFERENCE_WARNING') {
        const details = respData?.details || {};
        setDuplicateWarning({
          message: respData.error || 'Potential duplicate instrument reference detected.',
          matching_records: details.matching_records || [],
        });
      } else {
        setApiError(respData?.error || respData?.message || err?.message || 'Submission failed.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || isSubmitting) return;
    submitInstrument(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sentinel-100 text-sentinel-700 flex items-center justify-center font-bold">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-slate-900">
                  {isEditing ? 'Edit FDR Instrument Record' : 'Record Statutory FDR Instrument'}
                </h2>
                <span className="font-mono text-[10px] bg-purple-100 text-purple-800 font-bold px-2 py-0.5 rounded flex items-center gap-1">
                  <Shield className="w-3 h-3 text-purple-700" />
                  <span>L0 — DECLARED</span>
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Statutory fixed deposit receipt pledged jointly under AICTE Regulation Bureau terms
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
          {apiError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2 text-rose-700">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Submission Rejected</p>
                <p className="text-[11px] mt-0.5">{apiError}</p>
              </div>
            </div>
          )}

          {/* DUPLICATE WARNING MODAL / PANEL */}
          {duplicateWarning && (
            <div className="p-4 rounded-xl bg-amber-50 border-2 border-amber-300 space-y-3 animate-in fade-in">
              <div className="flex items-start gap-2.5 text-amber-900">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-xs">Potential Duplicate Reference Warning</h4>
                  <p className="text-[11px] text-amber-800 mt-0.5">
                    An instrument with this reference number and bank is already present in the registry.
                    To avoid duplicate confusion or record this instrument for regulatory inspection, confirm below.
                  </p>
                </div>
              </div>

              {duplicateWarning.matching_records.length > 0 && (
                <div className="bg-white rounded-lg border border-amber-200 p-2.5 max-h-36 overflow-y-auto space-y-1.5 text-[11px]">
                  <p className="font-semibold text-slate-700 text-[10px] uppercase">
                    Matching Registered Instrument(s):
                  </p>
                  {duplicateWarning.matching_records.map((rec) => (
                    <div
                      key={rec.id}
                      className="p-2 rounded bg-amber-50/50 border border-amber-100 flex items-center justify-between font-mono"
                    >
                      <div>
                        <span className="font-bold text-slate-800">{rec.reference_number}</span> —{' '}
                        <span className="text-slate-600">{rec.bank_name}</span>
                        {rec.institution_name && (
                          <div className="text-[10px] text-slate-500 font-sans">
                            {rec.institution_name}
                          </div>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-sentinel-700">₹ {rec.amount}</span>
                        <div className="text-[10px] text-slate-400 font-sans">{rec.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setDuplicateWarning(null)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 font-medium text-slate-700"
                >
                  Cancel & Revise Reference
                </button>
                <button
                  type="button"
                  onClick={() => submitInstrument(true)}
                  disabled={isSubmitting}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-1.5 shadow-xs"
                >
                  {isSubmitting ? (
                    <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  <span>Confirm & Record Duplicate for Review</span>
                </button>
              </div>
            </div>
          )}

          {/* Section: Institution Scoping */}
          <div>
            <label className="block font-medium text-slate-700 mb-1">
              Parent Institution <span className="text-rose-500">*</span>
            </label>
            {isInstitutionUser ? (
              <input
                type="text"
                disabled
                value={user?.institution_id ? `Assigned Institution (${user.institution_id})` : 'Unassigned'}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-slate-100 text-slate-500 cursor-not-allowed font-medium"
              />
            ) : (
              <select
                disabled={isEditing}
                value={formData.institution_id}
                onChange={(e) => setFormData({ ...formData, institution_id: e.target.value })}
                className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                  errors.institution_id ? 'border-rose-400' : 'border-slate-300'
                } ${isEditing ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''}`}
              >
                <option value="">Select registered institution...</option>
                {institutions.map((inst) => (
                  <option key={inst.id} value={inst.id}>
                    {inst.code} — {inst.legal_name || inst.name} ({inst.city}, {inst.state})
                  </option>
                ))}
              </select>
            )}
            {errors.institution_id && <p className="text-rose-600 mt-1">{errors.institution_id}</p>}
          </div>

          {/* Section: Banking & Reference */}
          <div className="pt-2 border-t border-slate-200">
            <h3 className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider mb-2">
              Banking & Instrument Identity
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Issuing Bank Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  list="bank-suggestions"
                  value={formData.bank_name}
                  onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                  placeholder="e.g. State Bank of India"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.bank_name ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                <datalist id="bank-suggestions">
                  {COMMON_BANKS.map((b) => (
                    <option key={b} value={b} />
                  ))}
                </datalist>
                {errors.bank_name && <p className="text-rose-600 mt-1">{errors.bank_name}</p>}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Branch Name / IFSC Location
                </label>
                <input
                  type="text"
                  value={formData.branch}
                  onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                  placeholder="e.g. Nariman Point Branch, Mumbai"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  FDR / Receipt Certificate Number <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.reference_number}
                  onChange={(e) =>
                    setFormData({ ...formData, reference_number: e.target.value.toUpperCase() })
                  }
                  placeholder="e.g. FDR-SBI-2026-9901"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.reference_number ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {errors.reference_number && (
                  <p className="text-rose-600 mt-1">{errors.reference_number}</p>
                )}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Principal Deposit Amount (INR) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  placeholder="e.g. 2500000.00"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.amount ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {errors.amount && <p className="text-rose-600 mt-1">{errors.amount}</p>}
              </div>
            </div>
          </div>

          {/* Section: Term Dates */}
          <div className="pt-2 border-t border-slate-200">
            <h3 className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider mb-2">
              Statutory Deposit Term
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Issue / Deposit Start Date <span className="text-rose-500">*</span>
                </label>
                <input
                  type="date"
                  value={formData.issue_date}
                  onChange={(e) => setFormData({ ...formData, issue_date: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 font-mono"
                />
                {errors.issue_date && <p className="text-rose-600 mt-1">{errors.issue_date}</p>}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Maturity Expiry Date <span className="text-rose-500">*</span>
                </label>
                <input
                  type="date"
                  value={formData.maturity_date}
                  onChange={(e) => setFormData({ ...formData, maturity_date: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.maturity_date ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {errors.maturity_date && (
                  <p className="text-rose-600 mt-1">{errors.maturity_date}</p>
                )}
              </div>
            </div>
          </div>

          {/* Section: Trust Level & Regulatory Information */}
          <div className="pt-2 border-t border-slate-200 space-y-3">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-start gap-2">
              <Info className="w-4 h-4 text-sentinel-600 shrink-0 mt-0.5" />
              <div className="text-[11px] text-slate-600 space-y-1">
                <p>
                  <strong>Trust Level Assignment:</strong> All newly registered instruments start strictly at{' '}
                  <span className="font-mono text-purple-700 font-bold">L0 — DECLARED</span>. Advancement to
                  L1 (Document Consistent), L2 (Officer Verified), and L3 (Bank Confirmed) is managed through
                  the independent verification pipeline.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Lien Holder Beneficiary</label>
                <input
                  type="text"
                  value={formData.lien_holder}
                  onChange={(e) => setFormData({ ...formData, lien_holder: e.target.value })}
                  placeholder="AICTE Regulation Bureau"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Initial Administrative Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                >
                  <option value="REGISTERED">REGISTERED (Formal Registry Submission)</option>
                  <option value="DRAFT">DRAFT (Saved Institutional Draft)</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Administrative Remarks</label>
                <textarea
                  rows={2}
                  value={formData.remarks}
                  onChange={(e) => setFormData({ ...formData, remarks: e.target.value })}
                  placeholder="Any initial submission remarks or context..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>
            </div>
          </div>

          {/* Footer buttons */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-lg bg-sentinel-600 hover:bg-sentinel-700 text-white font-medium shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Recording...</span>
                </>
              ) : (
                <span>{isEditing ? 'Save Changes' : 'Record Instrument'}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
