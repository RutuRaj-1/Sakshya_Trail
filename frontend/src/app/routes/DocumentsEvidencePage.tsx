import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  UploadCloud,
  Search,
  ShieldCheck,
  Download,
  Copy,
  Check,
  AlertTriangle,
  FileCode,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { instrumentsApi, documentsApi } from '@/api/endpoints';
import type { Instrument } from '@/types';
import type { DocumentItem, DocumentDetail } from '@/api/endpoints';
import { useAuth } from '@/features/auth/AuthContext';
import { canUploadDocument } from '@/features/auth/authUtils';
import { Badge } from '@/components/common/Badge';
import { formatDate, cn } from '@/lib/utils';

export const DocumentsEvidencePage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const isInstitutionUser = user?.role === 'INSTITUTION_USER';
  const canUpload = canUploadDocument(user?.role);

  // Selection state
  const initialInstrumentId = searchParams.get('instrument_id') || '';
  const [selectedInstrumentId, setSelectedInstrumentId] = useState<string>(initialInstrumentId);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocDetail, setSelectedDocDetail] = useState<DocumentDetail | null>(null);

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadCategory, setUploadCategory] = useState('FDR_CERTIFICATE');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Loading & copy states
  const [isLoading, setIsLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Load instruments for picker
  useEffect(() => {
    async function loadInstruments() {
      try {
        const res = await instrumentsApi.list({ limit: 50 });
        setInstruments(res.items);
        if (!selectedInstrumentId && res.items.length > 0) {
          setSelectedInstrumentId(res.items[0].id);
        }
      } catch (err) {
        console.error('Failed to load instruments for evidence hub:', err);
      }
    }
    loadInstruments();
  }, [selectedInstrumentId]);

  // Load documents for selected instrument
  const loadDocuments = useCallback(async () => {
    if (!selectedInstrumentId) return;
    setIsLoading(true);
    try {
      const res = await documentsApi.listByInstrument(selectedInstrumentId);
      setDocuments(res.items);
      if (res.items.length > 0) {
        const detail = await documentsApi.getDetail(res.items[0].id);
        setSelectedDocDetail(detail);
      } else {
        setSelectedDocDetail(null);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
      setDocuments([]);
      setSelectedDocDetail(null);
    } finally {
      setIsLoading(false);
    }
  }, [selectedInstrumentId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleSelectDocument = async (docId: string) => {
    try {
      const detail = await documentsApi.getDetail(docId);
      setSelectedDocDetail(detail);
    } catch (err) {
      console.error('Failed to retrieve document versions:', err);
    }
  };

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInstrumentId || !uploadFile) {
      setUploadError('Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const fd = new FormData();
      fd.append('category', uploadCategory);
      if (uploadTitle.trim()) fd.append('title', uploadTitle.trim());
      if (uploadDescription.trim()) fd.append('description', uploadDescription.trim());
      fd.append('file', uploadFile);

      await documentsApi.upload(selectedInstrumentId, fd);
      setIsUploadOpen(false);
      setUploadTitle('');
      setUploadDescription('');
      setUploadFile(null);
      await loadDocuments();
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || err?.message || 'Upload rejected by security validation.');
    } finally {
      setIsUploading(false);
    }
  };

  const activeInstrument = instruments.find((i) => i.id === selectedInstrumentId);

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans text-xs pb-12">
      {/* Header */}
      <div className="bg-[#0D2538] rounded-[10px] p-6 text-white shadow-[0_1px_3px_rgba(13,37,56,0.08)] border border-[#1e3c54] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="bg-[#123B5D] text-[#8ACEC8] border border-[#0F766E]/40 text-[10px] font-semibold px-2.5 py-0.5 rounded-[4px] uppercase tracking-wider font-mono">
              {isInstitutionUser ? 'Institution Evidence Hub' : 'Module 2 Hub'}
            </span>
            <span className="text-[#8799A9] text-xs font-mono">Evidence Integrity Vault</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            Documents &amp; Certified Evidence Registry
          </h1>
          <p className="text-xs text-[#C9D3DB] leading-relaxed">
            Statutory evidence intake, deterministic SHA-256 byte verification, anti-malware pipeline, and immutable version catalogs.
          </p>
        </div>

        {canUpload && (
          <button
            type="button"
            onClick={() => {
              setUploadError(null);
              setIsUploadOpen(true);
            }}
            disabled={!selectedInstrumentId}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F766E] hover:bg-[#09544E] text-white text-xs font-semibold rounded-[8px] shadow-xs transition disabled:opacity-50 cursor-pointer shrink-0"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Certified Evidence</span>
          </button>
        )}
      </div>

      {/* Main Grid: Selector Column & Document View Column */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: FDR Instrument Selector */}
        <div className="lg:col-span-4 space-y-3">
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider">
                Select FDR Instrument
              </h2>
              <span className="text-[10px] text-[#5D6A75] font-mono">
                {instruments.length} records
              </span>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Filter by ref or bank..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-[6px] border border-[#C9D3DB] focus:outline-none focus:border-[#0F766E]"
              />
            </div>

            <div className="space-y-1.5 max-h-[460px] overflow-y-auto pr-1">
              {instruments
                .filter(
                  (i) =>
                    !searchQuery ||
                    i.reference_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    i.bank_name.toLowerCase().includes(searchQuery.toLowerCase())
                )
                .map((inst) => {
                  const isSelected = inst.id === selectedInstrumentId;
                  return (
                    <div
                      key={inst.id}
                      onClick={() => {
                        setSelectedInstrumentId(inst.id);
                        setSearchParams({ instrument_id: inst.id });
                      }}
                      className={cn(
                        'p-2.5 rounded-[6px] border cursor-pointer transition-all text-xs select-none',
                        isSelected
                          ? 'bg-[#123B5D] text-white border-[#0F766E] shadow-2xs'
                          : 'bg-[#F5F4EF]/50 hover:bg-[#F5F4EF] text-[#253746] border-slate-200'
                      )}
                    >
                      <div className="flex items-center justify-between font-mono font-bold text-[11px]">
                        <span>{inst.reference_number}</span>
                        <span
                          className={cn(
                            'text-[9px] px-1.5 py-0.2 rounded font-normal',
                            isSelected ? 'bg-[#0F766E] text-white' : 'bg-slate-200 text-[#253746]'
                          )}
                        >
                          {inst.status}
                        </span>
                      </div>
                      <div className="text-[11px] truncate mt-0.5 opacity-90">
                        {inst.bank_name}
                      </div>
                      <div className="flex items-center justify-between text-[10px] mt-1 opacity-75">
                        <span>Lien: {inst.joint_with_aicte ? 'Joint AICTE' : 'Sole'}</span>
                        <span className="font-mono">{inst.trust_level}</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>

        {/* Right Column: Versioned Evidence Catalog */}
        <div className="lg:col-span-8 space-y-4">
          {/* Active Instrument Context Bar */}
          {activeInstrument && (
            <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-4 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[10px] font-mono text-[#8799A9] uppercase">Active FDR Context</span>
                <div className="text-sm font-bold text-[#0D2538] flex items-center gap-2">
                  <span>{activeInstrument.reference_number}</span>
                  <span className="text-slate-300">|</span>
                  <span className="font-normal text-xs text-[#5D6A75]">{activeInstrument.bank_name}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/instruments/${activeInstrument.id}`}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-[#F5F4EF] hover:bg-slate-200 text-[#0D2538] border border-[#C9D3DB] transition"
                >
                  <span>FDR Details</span>
                  <ExternalLink className="w-3 h-3 text-[#5D6A75]" />
                </Link>
                <Link
                  to={`/verification/${activeInstrument.id}`}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-purple-50 hover:bg-purple-100 text-purple-900 border border-purple-200 transition"
                >
                  <ShieldCheck className="w-3 h-3 text-purple-600" />
                  <span>Trust Desk</span>
                </Link>
              </div>
            </div>
          )}

          {/* Document List */}
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-5 shadow-2xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h2 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider">
                  Registered Documents ({documents.length})
                </h2>
                <p className="text-[11px] text-[#5D6A75] mt-0.5">
                  Click a document to inspect its full version history, virus scan results, and SHA-256 byte hashes.
                </p>
              </div>
              <button
                type="button"
                onClick={loadDocuments}
                disabled={isLoading}
                className="p-1 text-[#5D6A75] hover:text-[#0D2538] cursor-pointer"
                title="Refresh documents"
              >
                <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
              </button>
            </div>

            {documents.length === 0 ? (
              <div className="py-12 text-center text-[#5D6A75]">
                <FileCode className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="font-semibold text-[#253746]">No evidence documents uploaded yet</p>
                <p className="text-slate-400 text-[11px] max-w-sm mx-auto mt-1">
                  Upload fixed deposit certificates, bank confirmation receipts, or lien letters for this deposit.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => {
                  const isInspected = selectedDocDetail?.id === doc.id;
                  return (
                    <div
                      key={doc.id}
                      onClick={() => handleSelectDocument(doc.id)}
                      className={cn(
                        'p-3 rounded-[8px] border cursor-pointer transition-all flex items-center justify-between',
                        isInspected
                          ? 'border-[#0F766E] bg-teal-50/20 shadow-2xs'
                          : 'border-[#C9D3DB] hover:border-slate-400 bg-white'
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded bg-[#F5F4EF] text-[#123B5D]">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-[#0D2538] text-xs">
                            {doc.title || doc.category}
                          </div>
                          <div className="text-[10px] text-[#5D6A75] flex items-center gap-2 mt-0.5">
                            <span className="font-mono uppercase font-bold text-[#0F766E]">{doc.category}</span>
                            <span>•</span>
                            <span>{doc.version_count} version(s)</span>
                            <span>•</span>
                            <span>Created {formatDate(doc.created_at)}</span>
                          </div>
                        </div>
                      </div>
                      <Badge variant="teal" className="text-[10px] font-mono">
                        v{doc.current_version_number}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Inspected Document Version History & SHA-256 Hashes */}
          {selectedDocDetail && (
            <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="font-bold text-[#0D2538] text-xs uppercase tracking-wider">
                    Immutable Version Catalog &amp; Byte Digests
                  </h3>
                  <p className="text-[10px] text-[#5D6A75] mt-0.5">
                    {selectedDocDetail.title || selectedDocDetail.category} (ID: {selectedDocDetail.id})
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-[#F5F4EF] text-[#5D6A75] uppercase text-[10px] tracking-wider font-semibold border-b border-[#C9D3DB]">
                      <th className="px-3 py-2">Version</th>
                      <th className="px-3 py-2">Filename</th>
                      <th className="px-3 py-2">SHA-256 Byte Hash</th>
                      <th className="px-3 py-2">Scan Status</th>
                      <th className="px-3 py-2">Size</th>
                      <th className="px-3 py-2">Upload Time</th>
                      <th className="px-3 py-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-[11px]">
                    {selectedDocDetail.versions.map((v) => (
                      <tr key={v.id} className="hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono font-bold text-[#123B5D]">v{v.version_number}</td>
                        <td className="px-3 py-2 font-medium text-[#253746] max-w-xs truncate">{v.filename}</td>
                        <td className="px-3 py-2 font-mono text-[10px] text-[#5D6A75]">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate max-w-[140px]" title={v.sha256_hash}>
                              {v.sha256_hash.slice(0, 16)}...
                            </span>
                            <button
                              type="button"
                              onClick={() => handleCopyHash(v.sha256_hash)}
                              className="p-0.5 text-slate-400 hover:text-[#0D2538]"
                              title="Copy SHA-256 digest"
                            >
                              {copiedHash === v.sha256_hash ? (
                                <Check className="w-3 h-3 text-emerald-600" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={cn(
                              'text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold',
                              v.processing_status === 'CLEAN' || v.processing_status === 'COMPLETED'
                                ? 'bg-emerald-100 text-emerald-800'
                                : v.processing_status === 'INFECTED'
                                ? 'bg-rose-100 text-rose-800'
                                : 'bg-amber-100 text-amber-800'
                            )}
                          >
                            {v.processing_status}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-mono text-slate-500">
                          {(v.size_bytes / 1024).toFixed(1)} KB
                        </td>
                        <td className="px-3 py-2 text-slate-500">{formatDate(v.uploaded_at)}</td>
                        <td className="px-3 py-2 text-right">
                          <a
                            href={documentsApi.getDownloadUrl(selectedDocDetail.id, v.id)}
                            download={v.filename}
                            className="inline-flex items-center gap-1 text-[#0F766E] hover:underline font-semibold"
                          >
                            <Download className="w-3 h-3" />
                            <span>Download</span>
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-2xs">
          <div className="bg-white rounded-[10px] border border-[#C9D3DB] p-6 max-w-lg w-full space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="font-bold text-[#0D2538] text-sm flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-[#0F766E]" />
                <span>Upload Certified Deposit Evidence</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsUploadOpen(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            {uploadError && (
              <div className="p-3 rounded bg-rose-50 border border-rose-200 text-rose-800 text-[11px] flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Document Category *
                </label>
                <select
                  value={uploadCategory}
                  onChange={(e) => setUploadCategory(e.target.value)}
                  className="w-full text-xs rounded border border-[#C9D3DB] px-3 py-2 focus:outline-none focus:border-[#0F766E]"
                >
                  <option value="FDR_CERTIFICATE">Fixed Deposit Certificate / Advice Scan</option>
                  <option value="BANK_CONFIRMATION_LETTER">Bank Confirmation Letter</option>
                  <option value="RENEWAL_ADVICE">Renewal / Lineage Rollover Notice</option>
                  <option value="DISCHARGE_SANCTION">Discharge / Release Sanction Order</option>
                  <option value="OTHER_SUPPORTING">Other Supporting Evidence</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Document Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Canara Bank FDR Certificate 2026"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full text-xs rounded border border-[#C9D3DB] px-3 py-2 focus:outline-none focus:border-[#0F766E]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Description / Official Notes
                </label>
                <textarea
                  placeholder="Official observations regarding the uploaded scan or certificate..."
                  rows={2}
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                  className="w-full text-xs rounded border border-[#C9D3DB] px-3 py-2 focus:outline-none focus:border-[#0F766E]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#253746] mb-1">
                  Select File (PDF, PNG, JPG ≤ 10MB) *
                </label>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-xs border border-dashed border-[#C9D3DB] p-3 rounded bg-[#F5F4EF]/50 cursor-pointer"
                  required
                />
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-3 py-1.5 rounded border border-[#C9D3DB] text-[#5D6A75] hover:bg-slate-100 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="px-4 py-1.5 rounded bg-[#0F766E] hover:bg-[#09544E] text-white font-semibold shadow-xs disabled:opacity-50"
                >
                  {isUploading ? 'Computing SHA-256 & Scanning...' : 'Upload & Hash'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
