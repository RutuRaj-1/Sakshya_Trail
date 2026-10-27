import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SystemAdminWorkspace } from '@/features/dashboard/workspaces/SystemAdminWorkspace';
import { lifecycleApi, usersApi, institutionsApi, healthApi } from '@/api/endpoints';

vi.mock('@/api/endpoints', () => ({
  usersApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
  institutionsApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
  healthApi: {
    getLiveness: vi.fn().mockResolvedValue({ status: 'HEALTHY' }),
    getReadiness: vi.fn().mockResolvedValue({ status: 'READY', components: { database: { status: 'CONNECTED' } } }),
  },
  lifecycleApi: {
    listFailedNotifications: vi.fn(),
    getAdminOversightFeed: vi.fn().mockResolvedValue({
      total_count: 1,
      items: [
        {
          id: 'notif-oversight-1',
          event_type: 'INSTRUMENT_SUBMITTED_ADMIN_OVERSIGHT',
          title: 'Operational Oversight: Instrument Submitted',
          message: 'Actor: Test User | Entity: INSTRUMENT FDR-2026-TEST',
          recipient_role: 'SYSTEM_ADMIN',
          created_at: '2026-10-27T10:00:00Z',
          payload_metadata_json: JSON.stringify({
            actor: { name: 'Apex Principal', role: 'INSTITUTION_USER' },
            entity: { reference: 'FDR-2026-TEST' },
            safe_link: '/instruments/ins-1',
          }),
        },
      ],
    }),
  },
}));

describe('Prompt 6 — Notification Contract & Delivery Reliability UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('correctly handles NotificationListResponse object contract with items and total_count', async () => {
    vi.mocked(lifecycleApi.listFailedNotifications).mockResolvedValue({
      total_count: 3,
      page: 1,
      limit: 10,
      items: [
        {
          id: 'failed-1',
          instrument_id: 'ins-101',
          event_type: 'NOTIFICATION_DELIVERY_FAILED',
          channel: 'EMAIL',
          status: 'FAILED',
          failure_category: 'INVALID_RECIPIENT',
          failure_reason: 'Malformed email address',
          created_at: '2026-10-27T10:00:00Z',
        } as any,
        {
          id: 'failed-2',
          instrument_id: 'ins-102',
          event_type: 'NOTIFICATION_DELIVERY_FAILED',
          channel: 'EMAIL',
          status: 'FAILED',
          failure_category: 'PROVIDER_UNAVAILABLE',
          failure_reason: 'Connection timed out',
          created_at: '2026-10-27T10:05:00Z',
        } as any,
      ],
    });

    render(
      <MemoryRouter>
        <SystemAdminWorkspace />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Failed Dispatches card should display total_count (3)
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('Failed Dispatches')).toBeInTheDocument();
    });

    // Verify operational oversight feed items are displayed
    await waitFor(() => {
      expect(screen.getByText(/Operational Oversight Feed/i)).toBeInTheDocument();
      expect(screen.getByText('Operational Oversight: Instrument Submitted')).toBeInTheDocument();
      expect(screen.getByText('FDR-2026-TEST')).toBeInTheDocument();
    });
  });

  it('gracefully handles empty failed notifications list response', async () => {
    vi.mocked(lifecycleApi.listFailedNotifications).mockResolvedValue({
      total_count: 0,
      page: 1,
      limit: 10,
      items: [],
    });

    render(
      <MemoryRouter>
        <SystemAdminWorkspace />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Failed Dispatches')).toBeInTheDocument();
      const zeroes = screen.getAllByText('0');
      expect(zeroes.length).toBeGreaterThan(0);
    });
  });

  it('gracefully handles API network error for failed notifications without breaking workspace', async () => {
    vi.mocked(lifecycleApi.listFailedNotifications).mockRejectedValue(new Error('Network error'));

    render(
      <MemoryRouter>
        <SystemAdminWorkspace />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Workspace renders safely with default 0 without crashing
      expect(screen.getByText('Failed Dispatches')).toBeInTheDocument();
      expect(screen.getByText('Platform Governance & Security Administration')).toBeInTheDocument();
    });
  });
});
