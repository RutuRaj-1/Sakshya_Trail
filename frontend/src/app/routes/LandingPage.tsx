import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { Button } from '@/components/common/Button';
import {
  ShieldCheck,
  FileCheck2,
  FileText,
  Clock,
  RefreshCw,
  Lock,
  SlidersHorizontal,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Users,
  Database,
  ArrowRight,
  History,
  Menu,
  X,
  Scale,
  Sparkles,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const toggleFaq = (index: number) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  const navLinks = [
    { name: 'Overview', href: '#overview' },
    { name: 'How It Works', href: '#how-it-works' },
    { name: 'Trust Ledger', href: '#trust-ledger' },
    { name: 'Capabilities', href: '#capabilities' },
    { name: 'Security', href: '#security' },
    { name: 'Command Center', href: '#command-center-preview' },
    { name: 'FAQ', href: '#faq' },
  ];

  return (
    <div className="min-h-screen bg-[#F4F7FA] text-[#243447] font-sans selection:bg-teal-500 selection:text-white flex flex-col">
      {/* =========================================================================
          SECTION A: TOP NAVIGATION BAR
         ========================================================================= */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-[#DCE4EB] shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Logo & Brand Wordmark */}
          <Link to="/" className="flex items-center gap-3 group focus:outline-none focus:ring-2 focus:ring-[#0D9488] rounded-xl p-1">
            <img
              src="/logo.png"
              alt="SakshyaTrail Logo"
              className="h-12 w-auto object-contain transition-transform group-hover:scale-105 drop-shadow-xs"
            />
            <div className="hidden sm:block">
              <div className="flex items-center gap-1.5">
                <span className="text-xl font-extrabold tracking-tight text-[#0B253A]">
                  Sakshya<span className="text-[#0D9488]">Trail</span>
                </span>
                <span className="text-[10px] font-mono font-semibold uppercase bg-teal-50 text-[#0D9488] border border-teal-200 px-1.5 py-0.5 rounded">
                  SIH 26265
                </span>
              </div>
              <p className="text-[11px] font-medium text-[#607080] leading-tight">
                Security Deposit & FDR Lifecycle Integrity Platform
              </p>
            </div>
          </Link>

          {/* Center Navigation Links (Desktop) */}
          <nav className="hidden lg:flex items-center gap-1 text-sm font-medium text-[#607080]">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="px-3 py-1.5 rounded-lg hover:text-[#0B253A] hover:bg-slate-100/80 transition-colors"
              >
                {link.name}
              </a>
            ))}
          </nav>

          {/* Right Action: Sign In or Access Dashboard */}
          <div className="hidden sm:flex items-center gap-3">
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-[#607080] hidden md:inline">
                  Signed in as <strong className="text-[#0B253A] font-mono">{user?.role}</strong>
                </span>
                <Link to="/dashboard">
                  <Button
                    size="sm"
                    className="bg-[#123C5A] hover:bg-[#0B253A] text-white font-semibold shadow-sm"
                  >
                    <SlidersHorizontal className="w-3.5 h-3.5 mr-1.5" /> Access Dashboard
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-[#DCE4EB] text-[#123C5A] hover:bg-slate-100 font-medium"
                  >
                    Sign In
                  </Button>
                </Link>
                <Link to="/login">
                  <Button
                    size="sm"
                    className="bg-[#0D9488] hover:bg-teal-700 text-white font-semibold shadow-xs"
                  >
                    Access Portal <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Hamburger Toggle */}
          <div className="flex lg:hidden items-center gap-2">
            <Link to="/login" className="sm:hidden">
              <Button size="sm" className="bg-[#123C5A] text-white text-xs px-2.5 py-1">
                Sign In
              </Button>
            </Link>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              aria-label="Toggle mobile menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-[#DCE4EB] bg-white px-4 pt-3 pb-6 space-y-3 shadow-lg">
            <div className="grid grid-cols-2 gap-2 text-sm font-medium">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-[#607080] hover:text-[#0B253A] hover:bg-slate-100 transition-colors"
                >
                  {link.name}
                </a>
              ))}
            </div>
            <div className="pt-3 border-t border-slate-100 flex flex-col gap-2">
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button className="w-full bg-[#123C5A] hover:bg-[#0B253A] text-white font-semibold">
                  Sign In to SakshyaTrail
                </Button>
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* =========================================================================
          SECTION B: HERO SECTION & SYNTHETIC APPLICATION PREVIEW
         ========================================================================= */}
      <section id="overview" className="relative pt-12 pb-20 md:pt-16 md:pb-28 overflow-hidden bg-linear-to-b from-white to-[#F4F7FA]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-4xl mx-auto space-y-5">
            {/* Eyebrow Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-[#0D9488] text-xs font-semibold uppercase tracking-wider shadow-2xs">
              <Sparkles className="w-3.5 h-3.5" />
              SMART AUTOMATION · EVIDENCE-FIRST GOVERNANCE
            </div>

            {/* Headline */}
            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-[#0B253A] tracking-tight leading-[1.15]">
              From FDR Submission to Release —{' '}
              <span className="text-[#0D9488] underline decoration-teal-300 decoration-wavy underline-offset-8">
                Every Step Accountable.
              </span>
            </h1>

            {/* Supporting Paragraph */}
            <p className="text-base sm:text-lg text-[#607080] max-w-3xl mx-auto leading-relaxed">
              SakshyaTrail brings security deposit and FDR records, evidence provenance, verification workflows,
              maturity monitoring and authorized release tracking into one traceable lifecycle.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link to="/login" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  className="w-full sm:w-auto bg-[#123C5A] hover:bg-[#0B253A] text-white font-bold px-8 shadow-md shadow-[#123C5A]/25 gap-2"
                >
                  Access SakshyaTrail <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <a href="#how-it-works" className="w-full sm:w-auto">
                <Button
                  variant="outline"
                  size="lg"
                  className="w-full sm:w-auto border-[#DCE4EB] bg-white hover:bg-slate-50 text-[#243447] font-semibold px-6"
                >
                  Explore How It Works
                </Button>
              </a>
            </div>
          </div>

          {/* Interactive Synthetic Application Visual Preview */}
          <div className="mt-14 max-w-5xl mx-auto">
            <div className="bg-[#0B253A] rounded-2xl p-2 sm:p-3 shadow-2xl border border-slate-700/60 ring-1 ring-slate-800">
              {/* Window Bar Header */}
              <div className="flex items-center justify-between px-3 py-2 bg-slate-900/80 rounded-xl mb-3 text-xs text-slate-400 font-mono">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                    <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                    <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-[11px] text-slate-300 ml-2">sakshyatrail-command-center.internal/v1</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  SHA-256 Ledger: CHAIN INTACT (PASS)
                </div>
              </div>

              {/* Cockpit Card Container */}
              <div className="bg-white rounded-xl p-4 sm:p-6 text-slate-800 space-y-4">
                {/* Simulated Metrics Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Active Deposit Value</span>
                    <span className="text-lg font-bold text-[#0B253A] font-mono">₹ 37,50,00,000</span>
                    <span className="text-[10px] text-emerald-700 block mt-0.5">37 Validated FDRs</span>
                  </div>
                  <div className="bg-amber-50/60 p-3 rounded-xl border border-amber-200">
                    <span className="text-[10px] font-semibold text-amber-800 uppercase tracking-wider block">Upcoming Maturities</span>
                    <span className="text-lg font-bold text-amber-900 font-mono">4 Instruments</span>
                    <span className="text-[10px] text-amber-700 block mt-0.5">Within 90-day window</span>
                  </div>
                  <div className="bg-teal-50/60 p-3 rounded-xl border border-teal-200">
                    <span className="text-[10px] font-semibold text-teal-800 uppercase tracking-wider block">Trust Level Breakdown</span>
                    <span className="text-lg font-bold text-teal-900 font-mono">L2 Verified (28)</span>
                    <span className="text-[10px] text-teal-700 block mt-0.5">L3 Bank Confirmed: 6</span>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                    <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Release Gate Lock</span>
                    <span className="text-lg font-bold text-[#C62828] font-mono">2 Cases Blocked</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">Maker-checker active</span>
                  </div>
                </div>

                {/* Synthetic Record Row Sample */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 font-mono text-xs space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="bg-teal-100 text-teal-800 font-bold px-2 py-0.5 rounded text-[11px]">
                        FDR-SBI-2026-9041
                      </span>
                      <span className="font-semibold text-slate-800 font-sans">IIT Delhi Campus Development Security Deposit</span>
                    </div>
                    <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded text-[11px] self-start sm:self-auto">
                      TRUST: L2_OFFICER_VERIFIED
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-600 text-[11px]">
                    <div>Bank: <strong className="text-slate-800">State Bank of India</strong></div>
                    <div>Deposit: <strong className="text-slate-800">₹ 25,00,000.00</strong></div>
                    <div>Maturity: <strong className="text-slate-800">2027-04-15</strong></div>
                    <div>Doc Hash: <strong className="text-slate-800">sha256:7c8b9d...</strong></div>
                  </div>
                </div>

                {/* Simulated Audit Hash Chain Footnote */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 font-mono">
                  <span>Cryptographic Block: #42 · Digest: 86cd8157c91e... · Appended via append-only DB trigger</span>
                  <span className="text-teal-700 font-semibold font-sans">Tamper-evident regulatory ledger</span>
                </div>
              </div>
            </div>

            {/* Illustrative Notice Disclaimer */}
            <p className="text-center text-xs text-[#607080] mt-3 font-medium">
              * Illustrative preview — synthetic regulatory data. Not connected to external live bank servers.
            </p>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION C: TRUST PRINCIPLES STRIP
         ========================================================================= */}
      <section className="bg-white border-y border-[#DCE4EB] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center shrink-0">
                <Scale className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#0B253A]">Declared ≠ Confirmed</h2>
                <p className="text-xs text-[#607080] mt-0.5">
                  Self-reported institution metadata remains strictly unverified until backed by reviewed evidence.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center shrink-0">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#0B253A]">Evidence Before Trust</h2>
                <p className="text-xs text-[#607080] mt-0.5">
                  Tiered progression (L0 to L3) ensures trust elevations require qualifying certificates and audits.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center shrink-0">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#0B253A]">Human-Authorized Decisions</h2>
                <p className="text-xs text-[#607080] mt-0.5">
                  Automated heuristics advise; designated statutory authorities make all binding release decisions.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center shrink-0">
                <History className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-[#0B253A]">Traceable Lifecycle Events</h2>
                <p className="text-xs text-[#607080] mt-0.5">
                  Every status shift, document revision, and release approval writes to an append-only hash chain.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION D: THE PROBLEM & SAKSHYATRAIL SOLUTION
         ========================================================================= */}
      <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
            Institutional Governance Gap
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
            Why Security Deposit & FDR Portals Require Lifecycle Integrity
          </h2>
          <p className="text-sm sm:text-base text-[#607080] mt-3">
            Statutory Fixed Deposit Receipts represent substantial financial commitments guaranteeing regulatory compliance.
            Fragmented records and manual oversight introduce significant operational vulnerabilities.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
          {/* Column 1: Conventional Vulnerabilities */}
          <div className="bg-white rounded-2xl p-6 sm:p-8 border border-rose-200/80 shadow-xs space-y-4">
            <div className="flex items-center gap-2 text-[#C62828] font-bold text-base">
              <AlertTriangle className="w-5 h-5" /> Conventional Record Vulnerabilities
            </div>
            <ul className="space-y-3.5 text-sm text-[#607080]">
              <li className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                <span><strong>Fragmented Silos:</strong> FDR receipts, bank confirmations, and renewal drafts scattered across paper files and disconnected spreadsheets.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                <span><strong>Silent Calendar Expiration:</strong> Lack of automated 30/60/90-day alerting causes missed renewal deadlines and unmanaged maturity risks.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                <span><strong>Unchecked Discrepancies:</strong> Minor mismatches between certificates and portal entries require tedious manual reconciliation.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                <span><strong>Premature Release Risk:</strong> Security deposits refunded or discharged before all compliance checklist requirements are satisfied.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0" />
                <span><strong>Opaque Accountability:</strong> Inability to reconstruct who reviewed what evidence, when an observation was made, and who authorized discharge.</span>
              </li>
            </ul>
          </div>

          {/* Column 2: The SakshyaTrail Advantage */}
          <div className="bg-white rounded-2xl p-6 sm:p-8 border border-teal-200 shadow-xs space-y-4">
            <div className="flex items-center gap-2 text-[#0D9488] font-bold text-base">
              <ShieldCheck className="w-5 h-5" /> The SakshyaTrail Architecture
            </div>
            <ul className="space-y-3.5 text-sm text-[#243447]">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#0D9488] mt-0.5 shrink-0" />
                <span><strong>Centralized Registry:</strong> Single authoritative database binding institutions, bank references, precise decimal sums, and document versions.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#0D9488] mt-0.5 shrink-0" />
                <span><strong>Automated Maturity Engine:</strong> Deterministic calendar evaluations with regional workload distribution and automated reminder tracking.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#0D9488] mt-0.5 shrink-0" />
                <span><strong>Explainable Validation:</strong> Rule-based discrepancy detection providing specific error codes, severity flags, and audit reconciliation.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#0D9488] mt-0.5 shrink-0" />
                <span><strong>Release Gate Enforcement:</strong> Automated blocker evaluations that strictly forbid refund routing without full checklist satisfaction.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#0D9488] mt-0.5 shrink-0" />
                <span><strong>Tamper-Evident Hash Chains:</strong> SHA-256 cryptographic sequence storage with database triggers preventing deletion or in-place alterations.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Position Statement Banner */}
        <div className="mt-8 p-4 rounded-xl bg-slate-100/80 border border-[#DCE4EB] text-center text-xs text-[#607080] max-w-3xl mx-auto">
          <strong className="text-[#0B253A]">Architectural Position:</strong> SakshyaTrail is designed as a specialized <strong>complementary lifecycle-integrity layer</strong> to operate alongside existing regulatory frameworks and portal architectures.
        </div>
      </section>

      {/* =========================================================================
          SECTION E: HOW IT WORKS — END-TO-END LIFECYCLE (9 STAGES)
         ========================================================================= */}
      <section id="how-it-works" className="py-16 md:py-24 bg-white border-y border-[#DCE4EB]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
              End-to-End Workflow
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
              Nine Stages of Accountable FDR Governance
            </h2>
            <p className="text-sm sm:text-base text-[#607080] mt-3">
              From the moment an institution submits an instrument through to authorized closure,
              every state transition is structured, verified, and preserved.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Stage 1 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">01</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <Building2 className="w-5 h-5 text-[#0D9488]" /> 1. Submit
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Institution registers deposit details, certificate reference numbers, issuing bank branch, and term dates.
              </p>
            </div>

            {/* Stage 2 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">02</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <FileText className="w-5 h-5 text-[#0D9488]" /> 2. Upload
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Secure document intake computes deterministic SHA-256 file digests, creates immutable version history, and blocks unverified files.
              </p>
            </div>

            {/* Stage 3 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">03</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <FileCheck2 className="w-5 h-5 text-[#0D9488]" /> 3. Validate
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Deterministic rule engine verifies minimum deposit thresholds, valid date order, and flags mismatches with explainable findings.
              </p>
            </div>

            {/* Stage 4 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">04</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <ShieldCheck className="w-5 h-5 text-[#0D9488]" /> 4. Verify
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Authorized officers inspect evidence; bank verification requests tracked across simulated or authenticated API channels.
              </p>
            </div>

            {/* Stage 5 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">05</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <Clock className="w-5 h-5 text-[#0D9488]" /> 5. Monitor
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Automated scheduler evaluates daily calendar maturity windows (30/60/90 days), triggering reminders and supervisor escalations.
              </p>
            </div>

            {/* Stage 6 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">06</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <RefreshCw className="w-5 h-5 text-[#0D9488]" /> 6. Renew
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Renewal successor instruments are linked to predecessor records without mutating or overwriting historical provenance.
              </p>
            </div>

            {/* Stage 7 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">07</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <Lock className="w-5 h-5 text-[#0D9488]" /> 7. Release Gate
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Release Gate evaluates mandatory checklist criteria; active blockers forbid routing to Competent Authority for approval.
              </p>
            </div>

            {/* Stage 8 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">08</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <Scale className="w-5 h-5 text-[#0D9488]" /> 8. Approve
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Strict maker-checker segregation: reviewers cannot approve; release approval strictly reserved for Competent Authority.
              </p>
            </div>

            {/* Stage 9 */}
            <div className="bg-[#F4F7FA] rounded-2xl p-6 border border-[#DCE4EB] hover:border-teal-300 transition-colors space-y-3 relative">
              <span className="text-2xl font-black text-teal-600/40 font-mono block">09</span>
              <div className="flex items-center gap-2 font-bold text-[#0B253A] text-base">
                <History className="w-5 h-5 text-[#0D9488]" /> 9. Audit & Report
              </div>
              <p className="text-xs text-[#607080] leading-relaxed">
                Append-only SHA-256 hash-chaining records every action; authorized officers generate streaming CSV and tamper-evident PDF reports.
              </p>
            </div>
          </div>

          <p className="text-center text-xs text-[#607080] mt-8">
            * Bank verification can be pending, simulated, or unavailable depending on participating bank support. Live automated confirmation is not assumed for every record.
          </p>
        </div>
      </section>

      {/* =========================================================================
          SECTION F: TRUST LEDGER: L0 TO L3 TIERS
         ========================================================================= */}
      <section id="trust-ledger" className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
            Evidentiary Trust Hierarchy
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
            The 4-Tier Trust Ledger (L0 – L3)
          </h2>
          <p className="text-sm sm:text-base text-[#607080] mt-3">
            SakshyaTrail maintains strict separation between what has merely been entered and what has been verified.
            Trust is earned through evidence, never assumed by declaration.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* L0 Card */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                LEVEL 0
              </span>
              <span className="text-[11px] text-slate-400 font-mono">Baseline</span>
            </div>
            <h3 className="text-base font-bold text-slate-900">L0 — Declared</h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Information entered or uploaded by the institution. No formal officer scrutiny or document cross-check has been completed.
            </p>
            <div className="pt-2 text-[11px] text-slate-400 font-mono">
              Status: Baseline intake
            </div>
          </div>

          {/* L1 Card */}
          <div className="bg-white rounded-2xl p-6 border border-blue-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                LEVEL 1
              </span>
              <span className="text-[11px] text-blue-500 font-mono">Documented</span>
            </div>
            <h3 className="text-base font-bold text-slate-900">L1 — Document-Consistent</h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Information is consistent with scanned receipts and certified uploads. Authenticity of the underlying bank deposit is not yet established.
            </p>
            <div className="pt-2 text-[11px] text-blue-600 font-mono">
              Status: Document matched
            </div>
          </div>

          {/* L2 Card */}
          <div className="bg-white rounded-2xl p-6 border border-teal-200 shadow-xs space-y-3 ring-1 ring-teal-300/50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-teal-50 text-teal-800">
                LEVEL 2
              </span>
              <span className="text-[11px] text-teal-600 font-mono font-semibold">Recommended</span>
            </div>
            <h3 className="text-base font-bold text-slate-900">L2 — Officer-Verified</h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              An authorized scrutiny officer has formally evaluated the supporting evidence, confirmed validity parameters, and signed off observations.
            </p>
            <div className="pt-2 text-[11px] text-teal-700 font-mono font-semibold">
              Status: Human verified
            </div>
          </div>

          {/* L3 Card */}
          <div className="bg-white rounded-2xl p-6 border border-emerald-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800">
                LEVEL 3
              </span>
              <span className="text-[11px] text-emerald-600 font-mono">Confirmed</span>
            </div>
            <h3 className="text-base font-bold text-slate-900">L3 — Bank-Confirmed</h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Supported by a qualifying official verification response from the issuing commercial bank confirming active deposit holding and lien status.
            </p>
            <div className="pt-2 text-[11px] text-emerald-700 font-mono">
              Status: Bank confirmed
            </div>
          </div>
        </div>

        {/* Notice on OCR & AI Limits */}
        <div className="mt-8 p-4 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-3 max-w-3xl mx-auto">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <p>
            <strong>Statutory Guardrail Notice:</strong> OCR text extraction, cryptographic file hashes, and rule checks assist human scrutiny but do not independently prove the authenticity of a financial instrument. Elevated trust requires human officer endorsement or official bank response records.
          </p>
        </div>
      </section>

      {/* =========================================================================
          SECTION G: CORE CAPABILITIES GRID (7 MODULES)
         ========================================================================= */}
      <section id="capabilities" className="py-16 md:py-24 bg-white border-y border-[#DCE4EB]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
              Platform Modules
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
              Seven Integrated Regulatory Capabilities
            </h2>
            <p className="text-sm sm:text-base text-[#607080] mt-3">
              A comprehensive architecture built to handle statutory security deposit governance from intake to closure.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Capability 1 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <Building2 className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">1. Institution & Instrument Registry</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                Centralized registry capturing FDR reference numbers, precise decimal amounts, branch codes, and institutional ownership with multi-tenant row-level security.
              </p>
            </div>

            {/* Capability 2 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">2. Document Intake & Evidence Vault</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                Multi-version document management with cryptographic SHA-256 digests, MIME verification, and tamper-resistant storage for certified deposit receipts.
              </p>
            </div>

            {/* Capability 3 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">3. Validation & Discrepancy Detection</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                Deterministic rule catalog evaluating date chronologies, minimum regulatory sums, and generating explainable finding codes with severity classifications.
              </p>
            </div>

            {/* Capability 4 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">4. Trust Ledger & Verification Desk</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                4-tier evidentiary provenance tracking with electronic verification dispatch, response logging, and officer certification sign-off.
              </p>
            </div>

            {/* Capability 5 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <RefreshCw className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">5. Lifecycle Monitoring & Lineage</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                Automated 30/60/90-day maturity evaluations, reminder dispatches, and predecessor-successor renewal linkage without historical mutation.
              </p>
            </div>

            {/* Capability 6 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">6. Release Gate & Case Management</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                Enforces comprehensive checklist evaluations and maker-checker segregation. Blocks release requests from routing to authority while mandatory conditions remain unmet.
              </p>
            </div>

            {/* Capability 7 */}
            <div className="bg-[#F4F7FA] p-6 rounded-2xl border border-[#DCE4EB] space-y-3 md:col-span-2 lg:col-span-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 text-[#0D9488] flex items-center justify-center">
                <SlidersHorizontal className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0B253A]">7. Command Center, Search, Reporting & Verifiable Audit</h3>
              <p className="text-xs text-[#607080] leading-relaxed">
                Central administrative cockpit featuring status distributions, an explainable 0–100 triage queue, unified multi-attribute search, operational CSV/PDF exports, and cryptographic SHA-256 hash-chain verification with tamper detection.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION H: SECURITY, GOVERNANCE & RESPONSIBLE AUTOMATION
         ========================================================================= */}
      <section id="security" className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
            Institutional Trust Architecture
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
            Security, Governance & Responsible Automation
          </h2>
          <p className="text-sm sm:text-base text-[#607080] mt-3">
            Designed for high-assurance public compliance workflows with defense-in-depth principles.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] shadow-xs space-y-2">
            <div className="text-[#123C5A] font-bold text-sm flex items-center gap-2">
              <Lock className="w-4 h-4 text-[#0D9488]" /> Role-Based Access & Tenant Isolation
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Strict isolation ensures institution users only access their own deposits. Officers, Branch Heads, Authorities, and Auditors operate within mathematically defined permission bounds.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] shadow-xs space-y-2">
            <div className="text-[#123C5A] font-bold text-sm flex items-center gap-2">
              <History className="w-4 h-4 text-[#0D9488]" /> Append-Only Tamper-Evident Ledger
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Every material event incorporates the parent block's SHA-256 digest. Database triggers reject direct SQL UPDATE or DELETE commands, making unauthorized tampering immediately detectable.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] shadow-xs space-y-2">
            <div className="text-[#123C5A] font-bold text-sm flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#0D9488]" /> Maker-Checker Segregation
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              The officer recommending a release cannot approve it. System Administrators cannot authorize releases. Approval authority is strictly reserved for the Competent Authority.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] shadow-xs space-y-2">
            <div className="text-[#123C5A] font-bold text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#0D9488]" /> Release Gate Lock
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Refunds and encashments cannot be advanced while mandatory checklist criteria—such as uncertified renewals or open discrepancies—remain unsatisfied.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] shadow-xs space-y-2">
            <div className="text-[#123C5A] font-bold text-sm flex items-center gap-2">
              <Users className="w-4 h-4 text-[#0D9488]" /> Read-Only Compliance Auditor
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              Dedicated Auditor role has broad inspection rights and chain verification powers, but is strictly prohibited from mutating business records or approving transactions.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] shadow-xs space-y-2">
            <div className="text-[#123C5A] font-bold text-sm flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#0D9488]" /> Advisory AI Boundaries
            </div>
            <p className="text-xs text-[#607080] leading-relaxed">
              AI text and document heuristics serve solely as advisory aids for triage. Machine learning models cannot approve releases, alter trust levels, or execute money transfers.
            </p>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION I: COMMAND CENTER PREVIEW
         ========================================================================= */}
      <section id="command-center-preview" className="py-16 md:py-24 bg-white border-y border-[#DCE4EB]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
              Administrative Command Center
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
              Real-Time Operational Visibility
            </h2>
            <p className="text-sm sm:text-base text-[#607080] mt-3">
              Explore the administrative interface powering regulatory oversight, operational triage, and audit verification.
            </p>
          </div>

          <div className="bg-slate-900 rounded-2xl p-4 sm:p-8 text-white space-y-6 border border-slate-800 shadow-xl">
            {/* Top Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <SlidersHorizontal className="w-5 h-5 text-teal-400" /> Operational Overview Cockpit
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Real-time aggregation across 37 registered institutional deposits
                </p>
              </div>
              <span className="text-xs font-mono bg-slate-800 text-teal-400 border border-teal-500/30 px-2.5 py-1 rounded-full self-start sm:self-auto">
                ILLUSTRATIVE PREVIEW — SYNTHETIC DATA
              </span>
            </div>

            {/* Dashboard Widgets */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Active FDRs</span>
                <span className="text-xl font-bold text-white font-mono">15</span>
              </div>
              <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                <span className="text-[10px] text-amber-400 uppercase tracking-wider block">Expiring &lt;90d</span>
                <span className="text-xl font-bold text-amber-300 font-mono">4</span>
              </div>
              <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Matured</span>
                <span className="text-xl font-bold text-slate-300 font-mono">3</span>
              </div>
              <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                <span className="text-[10px] text-teal-400 uppercase tracking-wider block">Renewed</span>
                <span className="text-xl font-bold text-teal-300 font-mono">5</span>
              </div>
              <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                <span className="text-[10px] text-emerald-400 uppercase tracking-wider block">Released</span>
                <span className="text-xl font-bold text-emerald-300 font-mono">8</span>
              </div>
              <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700">
                <span className="text-[10px] text-rose-400 uppercase tracking-wider block">Blocked Releases</span>
                <span className="text-xl font-bold text-rose-300 font-mono">2</span>
              </div>
            </div>

            {/* Triage Priority Queue Row Preview */}
            <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-700/80 pb-2">
                <span className="font-semibold text-slate-200">Explainable Triage Priority Queue (Top Action Item)</span>
                <span className="font-mono text-teal-400">Score: 82.5 / 100</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-2 pt-1 font-mono">
                <div>
                  <span className="text-slate-300 font-bold">FDR-SBI-2026-001</span> · Alpha Engineering College
                </div>
                <div className="text-slate-400 text-[11px]">
                  Urgency: 75% · Discrepancy: 50% · Overdue: 100%
                </div>
              </div>
            </div>

            {/* Footer action to sign in */}
            <div className="text-center pt-2">
              <Link to="/login">
                <Button className="bg-[#0D9488] hover:bg-teal-700 text-white font-semibold text-xs px-5 py-2">
                  Sign In to Access Real Command Center <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION J: BENEFITS BY STAKEHOLDER
         ========================================================================= */}
      <section className="py-16 md:py-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
            Multi-Stakeholder Value
          </span>
          <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
            Designed for Every Governance Participant
          </h2>
          <p className="text-sm sm:text-base text-[#607080] mt-3">
            Streamlining communication and eliminating ambiguity across regulatory desks.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] space-y-2">
            <h3 className="font-bold text-[#0B253A] text-sm flex items-center gap-2">
              <Building2 className="w-4 h-4 text-[#0D9488]" /> Submitting Institutions
            </h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Real-time submission status, clear discrepancy feedback, automated renewal alerts, and self-service document intake.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] space-y-2">
            <h3 className="font-bold text-[#0B253A] text-sm flex items-center gap-2">
              <FileCheck2 className="w-4 h-4 text-[#0D9488]" /> Scrutiny Officers
            </h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Prioritized triage queue, deterministic rule findings, evidence reconciliation desk, and structured observation logging.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] space-y-2">
            <h3 className="font-bold text-[#0B253A] text-sm flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-[#0D9488]" /> Regional Branch Heads
            </h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Workload distribution across officers, SLA escalation monitoring, and regional maturity exposure aggregation.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] space-y-2">
            <h3 className="font-bold text-[#0B253A] text-sm flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#0D9488]" /> Competent Authorities
            </h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Objective Release Gate validation, maker-checker enforcement, and legally defensible release order records.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] space-y-2">
            <h3 className="font-bold text-[#0B253A] text-sm flex items-center gap-2">
              <Database className="w-4 h-4 text-[#0D9488]" /> Finance Officials
            </h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Deterministic tracking of deposit discharge orders without financial transaction risks or payment liabilities.
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE4EB] space-y-2">
            <h3 className="font-bold text-[#0B253A] text-sm flex items-center gap-2">
              <History className="w-4 h-4 text-[#0D9488]" /> Regulatory Auditors
            </h3>
            <p className="text-xs text-[#607080] leading-relaxed">
              Cryptographic SHA-256 hash-chain verification, replayable integrity audits, and structured operational exports.
            </p>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION K: FAQ ACCORDION
         ========================================================================= */}
      <section id="faq" className="py-16 md:py-24 bg-white border-y border-[#DCE4EB]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <span className="text-xs font-bold text-[#0D9488] uppercase tracking-wider block mb-2">
              Frequently Asked Questions
            </span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-[#0B253A] tracking-tight">
              Clear Answers About SakshyaTrail
            </h2>
            <p className="text-sm text-[#607080] mt-2">
              Honest technical specifications matching the actual prototype architecture.
            </p>
          </div>

          <div className="space-y-3">
            {[
              {
                q: 'What is SakshyaTrail?',
                a: 'SakshyaTrail is a centralized, evidence-first software prototype for tracking security deposits and Fixed Deposit Receipts (FDRs) through submission, scrutiny, verification, maturity, renewal, and authorized release, with tamper-evident audit trails at every stage.',
              },
              {
                q: 'Does SakshyaTrail replace existing AICTE portal systems?',
                a: 'No. SakshyaTrail is designed as a complementary lifecycle-integrity layer that integrates alongside existing institutional platforms to provide specialized evidence verification, maturity tracking, and auditability.',
              },
              {
                q: 'Does the system directly verify every FDR with commercial banks?',
                a: 'No. While the architecture supports electronic verification adapters, the prototype implements a simulated banking channel. Live commercial bank confirmation is not assumed for every record.',
              },
              {
                q: 'What do the L0 through L3 Trust Levels mean?',
                a: 'L0 means Declared (unverified submission). L1 means Document-Consistent (matches uploaded scan). L2 means Officer-Verified (human officer reviewed evidence). L3 means Bank-Confirmed (authenticated financial institution confirmation record).',
              },
              {
                q: 'Can automated AI or rule algorithms approve a deposit release?',
                a: 'Strictly no. Automated validation checks and AI document heuristics remain solely advisory. Final release decisions require human authorization by the designated Competent Authority under maker-checker separation.',
              },
              {
                q: 'Does SakshyaTrail process financial payments or money transfers?',
                a: 'No. SakshyaTrail is an evidentiary tracking and administrative authorization system. It does not transfer funds, move money, or integrate with payment gateways.',
              },
              {
                q: 'How are documents and lifecycle changes tracked?',
                a: 'Uploaded files are hashed with SHA-256 and stored in an immutable version catalog. Every status change, scrutiny observation, and release sanction is appended to a cryptographic SHA-256 hash-chain ledger protected by database-level triggers.',
              },
            ].map((item, index) => (
              <div
                key={index}
                className="border border-[#DCE4EB] rounded-xl overflow-hidden transition-all bg-[#F4F7FA]"
              >
                <button
                  onClick={() => toggleFaq(index)}
                  className="w-full px-5 py-4 text-left flex items-center justify-between text-sm font-bold text-[#0B253A] hover:text-[#0D9488] transition-colors focus:outline-none"
                >
                  <span>{item.q}</span>
                  <ChevronDown
                    className={`w-4 h-4 text-slate-500 transition-transform duration-200 shrink-0 ml-2 ${
                      openFaq === index ? 'rotate-180 text-teal-600' : ''
                    }`}
                  />
                </button>
                {openFaq === index && (
                  <div className="px-5 pb-4 pt-1 text-xs text-[#607080] leading-relaxed border-t border-slate-200/60 bg-white">
                    {item.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* =========================================================================
          SECTION L: FINAL CTA & COMPREHENSIVE FOOTER
         ========================================================================= */}
      <section className="py-16 md:py-20 bg-linear-to-br from-[#123C5A] to-[#0B253A] text-white text-center relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 space-y-5">
          <span className="text-xs font-mono font-semibold uppercase tracking-widest text-teal-300 bg-teal-500/10 px-3 py-1 rounded-full border border-teal-400/20">
            INTEGRITY · ACCOUNTABILITY · COMPLIANCE
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Bring Every FDR Lifecycle Into Clear View.
          </h2>
          <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Track the evidence, monitor the deadlines and preserve the trail behind every authorized decision.
          </p>
          <div className="pt-2">
            <Link to="/login">
              <Button
                size="lg"
                className="bg-[#0D9488] hover:bg-teal-500 text-white font-bold px-8 shadow-lg shadow-teal-900/30 gap-2"
              >
                Sign In to SakshyaTrail <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Public Footer */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-8 border-b border-slate-800">
            {/* Wordmark */}
            <div className="flex items-center gap-3">
              <img
                src="/logo.png"
                alt="SakshyaTrail Logo"
                className="h-11 w-auto object-contain bg-white/95 p-1 rounded-lg"
              />
              <div>
                <span className="text-base font-extrabold text-white tracking-tight">
                  Sakshya<span className="text-teal-400">Trail</span>
                </span>
                <p className="text-[11px] text-slate-400">
                  Security Deposit & FDR Lifecycle Integrity Platform
                </p>
              </div>
            </div>

            {/* Quick Links */}
            <div className="flex flex-wrap gap-4 text-xs font-medium text-slate-400">
              <a href="#overview" className="hover:text-white transition-colors">Overview</a>
              <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
              <a href="#trust-ledger" className="hover:text-white transition-colors">Trust Ledger</a>
              <a href="#capabilities" className="hover:text-white transition-colors">Capabilities</a>
              <a href="#security" className="hover:text-white transition-colors">Security</a>
              <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
              <Link to="/login" className="text-teal-400 hover:text-teal-300 font-semibold">Sign In →</Link>
            </div>
          </div>

          {/* Prototype Notice */}
          <div className="space-y-2 text-[11px] text-slate-500 leading-relaxed max-w-4xl">
            <p>
              <strong>Academic & Hackathon Notice:</strong> SakshyaTrail was developed for the Smart India Hackathon (SIH 2026), Problem Statement ID 26265: “Streamline of Security Deposit/FDR Portal.”
            </p>
            <p>
              This application is an educational prototype and demonstration of evidence-first financial governance architecture. It is not an officially endorsed AICTE portal service, does not process real monetary transactions, and does not maintain live connections to commercial bank databases.
            </p>
          </div>

          <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500">
            <span>© 2026 SakshyaTrail. All rights reserved.</span>
            <span className="font-mono text-slate-600">Problem Statement ID: 26265</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
