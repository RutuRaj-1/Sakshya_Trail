import React, { useState, useEffect } from 'react';
import { X, Building2, AlertCircle } from 'lucide-react';
import type { Institution } from '@/types';
import { institutionsApi } from '@/api/endpoints';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  institutionToEdit?: Institution | null;
  isInstitutionUser?: boolean;
}

const INSTITUTION_TYPES = [
  'TECHNICAL_INSTITUTE',
  'ENGINEERING_COLLEGE',
  'PHARMACY_INSTITUTE',
  'MANAGEMENT_STUDIES',
  'POLYTECHNIC_COLLEGE',
  'APPLIED_ARTS_AND_CRAFTS',
  'HOTEL_MANAGEMENT',
];

const INDIAN_STATES = [
  'Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh',
  'Gujarat', 'West Bengal', 'Telangana', 'Rajasthan', 'Kerala',
  'Madhya Pradesh', 'Andhra Pradesh', 'Punjab', 'Haryana', 'Bihar',
  'Odisha', 'Assam', 'Goa', 'Jharkhand', 'Uttarakhand', 'Himachal Pradesh'
];

export const InstitutionModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSuccess,
  institutionToEdit,
  isInstitutionUser = false,
}) => {
  const isEditing = !!institutionToEdit;

  const [formData, setFormData] = useState({
    code: '',
    legal_name: '',
    display_name: '',
    institution_type: 'TECHNICAL_INSTITUTE',
    contact_name: 'Registrar / Nodal Officer',
    contact_email: '',
    contact_phone: '+91-11-29581000',
    address_line1: 'Institutional Area',
    address_line2: '',
    city: 'New Delhi',
    state: 'Delhi',
    postal_code: '110001',
    assigned_office: 'Northern Regional Office',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (institutionToEdit) {
      setFormData({
        code: institutionToEdit.code || '',
        legal_name: institutionToEdit.legal_name || institutionToEdit.name || '',
        display_name: institutionToEdit.display_name || '',
        institution_type: institutionToEdit.institution_type || institutionToEdit.category || 'TECHNICAL_INSTITUTE',
        contact_name: institutionToEdit.contact_name || 'Registrar / Nodal Officer',
        contact_email: institutionToEdit.contact_email || '',
        contact_phone: institutionToEdit.contact_phone || '+91-11-29581000',
        address_line1: institutionToEdit.address_line1 || 'Institutional Area',
        address_line2: institutionToEdit.address_line2 || '',
        city: institutionToEdit.city || 'New Delhi',
        state: institutionToEdit.state || 'Delhi',
        postal_code: institutionToEdit.postal_code || '110001',
        assigned_office: institutionToEdit.assigned_office || '',
      });
    } else {
      setFormData({
        code: '',
        legal_name: '',
        display_name: '',
        institution_type: 'TECHNICAL_INSTITUTE',
        contact_name: 'Registrar / Nodal Officer',
        contact_email: '',
        contact_phone: '+91-11-29581000',
        address_line1: 'Institutional Area',
        address_line2: '',
        city: 'New Delhi',
        state: 'Delhi',
        postal_code: '110001',
        assigned_office: 'Northern Regional Office',
      });
    }
    setErrors({});
    setApiError(null);
  }, [institutionToEdit, isOpen]);

  if (!isOpen) return null;

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!isEditing) {
      if (!formData.code.trim()) {
        errs.code = 'Institution code is required.';
      } else if (formData.code.trim().length < 2) {
        errs.code = 'Institution code must be at least 2 characters.';
      }
    }

    if (!isInstitutionUser) {
      if (!formData.legal_name.trim()) {
        errs.legal_name = 'Official legal entity name is required.';
      } else if (formData.legal_name.trim().length < 2) {
        errs.legal_name = 'Legal name must be at least 2 characters.';
      }
    }

    if (!formData.contact_email.trim()) {
      errs.contact_email = 'Contact email is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact_email.trim())) {
      errs.contact_email = 'Please enter a valid institutional email address.';
    }

    if (!formData.contact_name.trim()) {
      errs.contact_name = 'Contact officer name is required.';
    }

    if (!formData.state.trim()) {
      errs.state = 'State / Region is required.';
    }

    if (!formData.postal_code.trim()) {
      errs.postal_code = 'Postal code is required.';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate() || isSubmitting) return;

    setIsSubmitting(true);
    setApiError(null);

    try {
      if (isEditing && institutionToEdit) {
        // If institution user, only send permitted contact fields
        const payload = isInstitutionUser
          ? {
              contact_name: formData.contact_name,
              contact_email: formData.contact_email,
              contact_phone: formData.contact_phone,
              address_line1: formData.address_line1,
              address_line2: formData.address_line2 || null,
              city: formData.city,
              state: formData.state,
              postal_code: formData.postal_code,
            }
          : {
              legal_name: formData.legal_name,
              display_name: formData.display_name || null,
              institution_type: formData.institution_type,
              contact_name: formData.contact_name,
              contact_email: formData.contact_email,
              contact_phone: formData.contact_phone,
              address_line1: formData.address_line1,
              address_line2: formData.address_line2 || null,
              city: formData.city,
              state: formData.state,
              postal_code: formData.postal_code,
              assigned_office: formData.assigned_office || null,
            };

        await institutionsApi.update(institutionToEdit.id, payload);
      } else {
        await institutionsApi.create({
          code: formData.code.trim().toUpperCase(),
          legal_name: formData.legal_name.trim(),
          display_name: formData.display_name.trim() || undefined,
          institution_type: formData.institution_type,
          contact_name: formData.contact_name.trim(),
          contact_email: formData.contact_email.trim(),
          contact_phone: formData.contact_phone.trim(),
          address_line1: formData.address_line1.trim(),
          address_line2: formData.address_line2.trim() || undefined,
          city: formData.city.trim(),
          state: formData.state.trim(),
          postal_code: formData.postal_code.trim(),
          assigned_office: formData.assigned_office.trim() || undefined,
          is_active: true,
        });
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.message || err?.message || 'Operation failed. Please try again.';
      setApiError(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sentinel-100 text-sentinel-700 flex items-center justify-center font-bold">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                {isEditing
                  ? isInstitutionUser
                    ? 'Update Contact & Nodal Details'
                    : 'Edit Registered Institution'
                  : 'Register New Institution'}
              </h2>
              <p className="text-xs text-slate-500">
                {isInstitutionUser
                  ? 'Update verified administrative and contact addresses for regulatory notices'
                  : 'Establish a new institutional entity under AICTE Regulation Bureau oversight'}
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
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Action Failed</p>
                <p className="text-[11px] mt-0.5">{apiError}</p>
              </div>
            </div>
          )}

          {/* Section: Identifiers */}
          <div>
            <h3 className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider mb-2">
              Entity Identity & Taxonomy
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Institution Code / Permanent ID <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  disabled={isEditing}
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. 1-10924811"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 font-mono focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.code ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                  } ${isEditing ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''}`}
                />
                {errors.code && <p className="text-rose-600 mt-1">{errors.code}</p>}
                {isEditing && (
                  <p className="text-[10px] text-slate-400 mt-0.5">Permanent identifiers cannot be changed.</p>
                )}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Institution Classification <span className="text-rose-500">*</span>
                </label>
                <select
                  disabled={isInstitutionUser}
                  value={formData.institution_type}
                  onChange={(e) => setFormData({ ...formData, institution_type: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 border-slate-300 ${
                    isInstitutionUser ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''
                  }`}
                >
                  {INSTITUTION_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">
                  Registered Legal Entity Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  disabled={isInstitutionUser}
                  value={formData.legal_name}
                  onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
                  placeholder="e.g. Delhi Technological University"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.legal_name ? 'border-rose-400' : 'border-slate-300'
                  } ${isInstitutionUser ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''}`}
                />
                {errors.legal_name && <p className="text-rose-600 mt-1">{errors.legal_name}</p>}
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">
                  Common Display / Operating Name (Optional)
                </label>
                <input
                  type="text"
                  disabled={isInstitutionUser}
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  placeholder="e.g. DTU Delhi"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 border-slate-300 ${
                    isInstitutionUser ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''
                  }`}
                />
              </div>
            </div>
          </div>

          {/* Section: Contact & Nodal */}
          <div className="pt-2 border-t border-slate-200">
            <h3 className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider mb-2">
              Nodal Contact & Official Communication
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Nodal Officer / Registrar <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.contact_name}
                  onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                  placeholder="e.g. Dr. Rajesh Sharma"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.contact_name ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {errors.contact_name && <p className="text-rose-600 mt-1">{errors.contact_name}</p>}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Official Contact Email <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  value={formData.contact_email}
                  onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                  placeholder="registrar@dtu.ac.in"
                  className={`w-full px-3 py-2 border rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    errors.contact_email ? 'border-rose-400' : 'border-slate-300'
                  }`}
                />
                {errors.contact_email && <p className="text-rose-600 mt-1">{errors.contact_email}</p>}
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Official Contact Phone <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.contact_phone}
                  onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                  placeholder="+91-11-27871018"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>
            </div>
          </div>

          {/* Section: Physical Address & Jurisdiction */}
          <div className="pt-2 border-t border-slate-200">
            <h3 className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider mb-2">
              Registered Address & Jurisdiction
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">
                  Address Line 1 <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.address_line1}
                  onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
                  placeholder="Shahbad Daulatpur, Main Bawana Road"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  City <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="New Delhi"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  State / Territory <span className="text-rose-500">*</span>
                </label>
                <select
                  value={formData.state}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                >
                  {INDIAN_STATES.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Postal PIN Code <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.postal_code}
                  onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                  placeholder="110042"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Assigned Regional AICTE Office
                </label>
                <input
                  type="text"
                  disabled={isInstitutionUser}
                  value={formData.assigned_office}
                  onChange={(e) => setFormData({ ...formData, assigned_office: e.target.value })}
                  placeholder="Northern Regional Office (NRO)"
                  className={`w-full px-3 py-2 border border-slate-300 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sentinel-500 ${
                    isInstitutionUser ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''
                  }`}
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
                  <span>Submitting...</span>
                </>
              ) : (
                <span>{isEditing ? 'Save Changes' : 'Register Institution'}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
