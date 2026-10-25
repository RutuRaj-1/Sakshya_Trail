import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { LandingPage } from '@/app/routes/LandingPage';
import { AuthProvider } from '@/features/auth/AuthContext';

const renderLandingPage = () => {
  return render(
    <AuthProvider>
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    </AuthProvider>
  );
};

describe('SakshyaTrail Landing Page', () => {
  it('renders top navigation with SakshyaTrail wordmark and descriptor', () => {
    renderLandingPage();

    // Wordmark & product identity
    const brandElements = screen.getAllByText(/Sakshya/i);
    expect(brandElements.length).toBeGreaterThan(0);

    const descriptors = screen.getAllByText(/Security Deposit & FDR Lifecycle Integrity Platform/i);
    expect(descriptors.length).toBeGreaterThan(0);

    // Nav links (present in header and footer)
    expect(screen.getAllByRole('link', { name: /^Overview$/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /^How It Works$/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /^Trust Ledger$/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /^Capabilities$/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /^Security$/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('link', { name: /^FAQ$/i }).length).toBeGreaterThanOrEqual(1);
  });

  it('renders hero headline, supporting copy and primary CTA to /login', () => {
    renderLandingPage();

    expect(
      screen.getByRole('heading', {
        name: /From FDR Submission to Release — Every Step Accountable\./i,
      })
    ).toBeInTheDocument();

    expect(
      screen.getByText(/SakshyaTrail brings security deposit and FDR records, evidence provenance/i)
    ).toBeInTheDocument();

    const accessCta = screen.getByRole('link', { name: /Access SakshyaTrail/i });
    expect(accessCta).toHaveAttribute('href', '/login');
  });

  it('renders trust principles strip', () => {
    renderLandingPage();

    expect(screen.getByText('Declared ≠ Confirmed')).toBeInTheDocument();
    expect(screen.getByText('Evidence Before Trust')).toBeInTheDocument();
    expect(screen.getByText('Human-Authorized Decisions')).toBeInTheDocument();
    expect(screen.getByText('Traceable Lifecycle Events')).toBeInTheDocument();
  });

  it('renders 9 lifecycle workflow stages', () => {
    renderLandingPage();

    expect(screen.getByText(/1\. Submit/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Upload/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Validate/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Verify/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Monitor/i)).toBeInTheDocument();
    expect(screen.getByText(/6\. Renew/i)).toBeInTheDocument();
    expect(screen.getByText(/7\. Release Gate/i)).toBeInTheDocument();
    expect(screen.getByText(/8\. Approve/i)).toBeInTheDocument();
    expect(screen.getByText(/9\. Audit & Report/i)).toBeInTheDocument();
  });

  it('renders the 4-tier Trust Ledger (L0–L3) and statutory guardrail notice', () => {
    renderLandingPage();

    expect(screen.getByText('L0 — Declared')).toBeInTheDocument();
    expect(screen.getByText('L1 — Document-Consistent')).toBeInTheDocument();
    expect(screen.getByText('L2 — Officer-Verified')).toBeInTheDocument();
    expect(screen.getByText('L3 — Bank-Confirmed')).toBeInTheDocument();
    expect(screen.getByText(/Statutory Guardrail Notice:/i)).toBeInTheDocument();
  });

  it('renders all 7 core capability modules', () => {
    renderLandingPage();

    expect(screen.getByText(/1\. Institution & Instrument Registry/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Document Intake & Evidence Vault/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Validation & Discrepancy Detection/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Trust Ledger & Verification Desk/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Lifecycle Monitoring & Lineage/i)).toBeInTheDocument();
    expect(screen.getByText(/6\. Release Gate & Case Management/i)).toBeInTheDocument();
    expect(screen.getByText(/7\. Command Center, Search, Reporting & Verifiable Audit/i)).toBeInTheDocument();
  });

  it('renders synthetic command center preview with clear disclaimer', () => {
    renderLandingPage();

    expect(screen.getByText(/Operational Overview Cockpit/i)).toBeInTheDocument();
    expect(screen.getByText(/ILLUSTRATIVE PREVIEW — SYNTHETIC DATA/i)).toBeInTheDocument();
  });

  it('toggles FAQ accordion items', () => {
    renderLandingPage();

    const faqButton = screen.getByRole('button', { name: /What is SakshyaTrail\?/i });
    expect(faqButton).toBeInTheDocument();

    // Initially closed
    expect(screen.queryByText(/centralized, evidence-first software prototype/i)).not.toBeInTheDocument();

    // Click to open
    fireEvent.click(faqButton);
    expect(screen.getByText(/centralized, evidence-first software prototype/i)).toBeInTheDocument();

    // Click to close
    fireEvent.click(faqButton);
    expect(screen.queryByText(/centralized, evidence-first software prototype/i)).not.toBeInTheDocument();
  });

  it('renders footer with SIH Problem Statement ID 26265 and academic disclaimer', () => {
    renderLandingPage();

    expect(screen.getByText(/Problem Statement ID: 26265/i)).toBeInTheDocument();
    expect(screen.getByText(/Academic & Hackathon Notice:/i)).toBeInTheDocument();
  });
});
