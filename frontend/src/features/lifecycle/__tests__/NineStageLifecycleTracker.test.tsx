import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
  NineStageLifecycleTracker,
  evaluateInstrumentLifecycleStage,
} from '../components/NineStageLifecycleTracker';
import type { Instrument } from '@/types';

const mockInstrument: Instrument = {
  id: 'inst-123',
  institution_id: 'inst-alpha',
  instrument_type: 'FDR',
  reference_number: 'FDR-SBI-TEST-001',
  bank_name: 'State Bank of India',
  branch: 'Main Branch',
  amount: '500000.00',
  currency: 'INR',
  issue_date: '2025-01-01',
  maturity_date: '2026-01-01',
  maturity_indicator: 'ACTIVE',
  status: 'REGISTERED',
  trust_level: 'L1_DOCUMENT_CONSISTENT',
  verification_level: 'L1_DOCUMENT_CONSISTENT',
  joint_with_aicte: true,
  lien_marked: true,
  is_synthetic: false,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

describe('evaluateInstrumentLifecycleStage Helper', () => {
  it('evaluates Stage 1 for DRAFT without documents', () => {
    const inst = { ...mockInstrument, status: 'DRAFT' as const };
    const evalRes = evaluateInstrumentLifecycleStage(inst, null);
    expect(evalRes.currentStageNumber).toBe(1);
    expect(evalRes.statusSummary).toMatch(/Initial FDR details recorded/i);
  });

  it('evaluates Stage 2 for DRAFT with uploaded documents', () => {
    const inst = { ...mockInstrument, status: 'DRAFT' as const };
    const snapshot = {
      instrument: inst,
      documents: [{ id: 'doc-1', file_name: 'scan.pdf' }] as any,
      findings: [],
      verification_requests: [],
      release_cases: [],
      lifecycle_events: [],
    };
    const evalRes = evaluateInstrumentLifecycleStage(inst, snapshot as any);
    expect(evalRes.currentStageNumber).toBe(2);
    expect(evalRes.statusSummary).toMatch(/Evidence uploaded; pending final submission/i);
  });

  it('evaluates Stage 3 for SUBMITTED or UNDER_SCRUTINY status', () => {
    const inst = { ...mockInstrument, status: 'UNDER_SCRUTINY' as const };
    const snapshot = {
      instrument: inst,
      documents: [{ id: 'doc-1' }],
      observations: [{ id: 'obs-1', status: 'RECORDED' }],
      findings: [],
      verification_requests: [],
      release_cases: [],
      lifecycle_events: [],
    };
    const evalRes = evaluateInstrumentLifecycleStage(inst, snapshot as any);
    expect(evalRes.currentStageNumber).toBe(3);
    expect(evalRes.stageStatus).toBe('WARNING');
    expect(evalRes.statusSummary).toMatch(/1 scrutiny observation/i);
  });

  it('evaluates Stage 4 for REGISTERED with L0_DECLARED trust', () => {
    const inst = { ...mockInstrument, status: 'REGISTERED' as const, trust_level: 'L0_DECLARED' as const };
    const evalRes = evaluateInstrumentLifecycleStage(inst, null);
    expect(evalRes.currentStageNumber).toBe(4);
    expect(evalRes.statusSummary).toMatch(/Declared status; pending officer attestation/i);
  });

  it('evaluates Stage 5 for active compliant instruments', () => {
    const inst = { ...mockInstrument, status: 'REGISTERED' as const, trust_level: 'L1_DOCUMENT_CONSISTENT' as const };
    const evalRes = evaluateInstrumentLifecycleStage(inst, null);
    expect(evalRes.currentStageNumber).toBe(5);
    expect(evalRes.statusSummary).toMatch(/Active compliance/i);
  });

  it('evaluates Stage 6 for RENEWED instruments', () => {
    const inst = { ...mockInstrument, status: 'RENEWED' as const };
    const evalRes = evaluateInstrumentLifecycleStage(inst, null);
    expect(evalRes.currentStageNumber).toBe(6);
    expect(evalRes.stageStatus).toBe('COMPLETED');
  });

  it('evaluates Stage 9 for RELEASED instruments', () => {
    const inst = { ...mockInstrument, status: 'RELEASED' as const };
    const evalRes = evaluateInstrumentLifecycleStage(inst, null);
    expect(evalRes.currentStageNumber).toBe(9);
    expect(evalRes.stageStatus).toBe('COMPLETED');
    expect(evalRes.statusSummary).toMatch(/Deposit discharged/i);
  });
});

describe('NineStageLifecycleTracker Component', () => {
  it('renders Portfolio Matrix Mode with all 9 stages', () => {
    render(
      <MemoryRouter>
        <NineStageLifecycleTracker
          mode="portfolio"
          stageCounts={{
            STAGE_1_REGISTER: 12,
            STAGE_2_SUBMIT_ATTACH: 5,
            STAGE_3_VALIDATE: 3,
            STAGE_4_VERIFY: 4,
            STAGE_5_MONITOR: 42,
            STAGE_6_RENEW_REPLACE: 6,
            STAGE_7_RELEASE_GATE: 2,
            STAGE_8_AUTHORIZE: 1,
            STAGE_9_CLOSE_AUDIT: 18,
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/Nine-Stage FDR Lifecycle Triage Matrix/i)).toBeInTheDocument();
    expect(screen.getByText('FDR Submission & Registration')).toBeInTheDocument();
    expect(screen.getByText('Document Upload & Evidence')).toBeInTheDocument();
    expect(screen.getByText('Validation & Discrepancy Detection')).toBeInTheDocument();
    expect(screen.getByText('Scrutiny & Review')).toBeInTheDocument();
    expect(screen.getByText('Bank Verification & Trust')).toBeInTheDocument();
    expect(screen.getByText('Lifecycle Monitoring')).toBeInTheDocument();
    expect(screen.getByText('Renewal & Successor Lineage')).toBeInTheDocument();
    expect(screen.getByText('Release Readiness')).toBeInTheDocument();
    expect(screen.getByText('Maker-Checker Decision & Closure')).toBeInTheDocument();

    // Check count displays
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
  });

  it('renders Instrument Mode with stepper timeline and tab navigation callback', () => {
    const handleNavigateTab = vi.fn();

    render(
      <MemoryRouter>
        <NineStageLifecycleTracker
          mode="instrument"
          instrument={mockInstrument}
          onNavigateTab={handleNavigateTab}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('Statutory Lifecycle Progress')).toBeInTheDocument();
    expect(screen.getByText(/Active compliance: statutory lien marked and valid/i)).toBeInTheDocument();

    // Lineage continuity button
    const lineageBtn = screen.getByText('View Lineage Continuity');
    expect(lineageBtn).toBeInTheDocument();
    fireEvent.click(lineageBtn);
    expect(handleNavigateTab).toHaveBeenCalledWith('lineage');
  });
});
