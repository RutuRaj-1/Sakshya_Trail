import { useState, useEffect } from 'react';
import { findingsApi } from '@/api/endpoints';
import { commandCenterApi } from '@/api/commandCenter';
import { releaseApi } from '@/api/release';
import { useAuth } from '@/features/auth/AuthContext';

export interface NavBadges {
  reviewQueueCount?: number;
  verificationQueueCount?: number;
  releaseCasesCount?: number;
}

export function useNavBadges(): NavBadges {
  const { user } = useAuth();
  const [badges, setBadges] = useState<NavBadges>({});

  useEffect(() => {
    if (!user) return;

    let isMounted = true;

    async function loadCounts() {
      const isInternal = [
        'SYSTEM_ADMIN',
        'SCRUTINY_OFFICER',
        'BRANCH_HEAD',
        'COMPETENT_AUTHORITY',
        'FINANCE_OFFICER',
        'AUDITOR',
      ].includes(user?.role || '');

      const promises: Promise<any>[] = [];

      // 1. Scrutiny Queue count (internal bureau roles)
      if (isInternal) {
        promises.push(
          findingsApi
            .getQueue({ status: ['OPEN', 'INVESTIGATING'], limit: 1 })
            .then((res) => ({ reviewQueueCount: res.total }))
            .catch(() => ({ reviewQueueCount: undefined }))
        );
      } else {
        promises.push(Promise.resolve({ reviewQueueCount: undefined }));
      }

      // 2. Verification Queue count (internal bureau roles)
      if (isInternal) {
        promises.push(
          commandCenterApi
            .getVerificationQueue({ limit: 1 })
            .then((res) => ({ verificationQueueCount: res.total_outstanding }))
            .catch(() => ({ verificationQueueCount: undefined }))
        );
      } else {
        promises.push(Promise.resolve({ verificationQueueCount: undefined }));
      }

      // 3. Release requests count
      promises.push(
        releaseApi
          .list({ limit: 50 })
          .then((res) => {
            const pending = res.filter((r) =>
              ['SUBMITTED', 'UNDER_REVIEW', 'READY_FOR_AUTHORITY'].includes(r.workflow_status)
            );
            return { releaseCasesCount: pending.length };
          })
          .catch(() => ({ releaseCasesCount: undefined }))
      );

      const results = await Promise.allSettled(promises);
      if (!isMounted) return;

      const merged: NavBadges = {};
      results.forEach((r) => {
        if (r.status === 'fulfilled' && r.value) {
          Object.assign(merged, r.value);
        }
      });

      setBadges(merged);
    }

    loadCounts();
    // Refresh periodically every 45s
    const interval = setInterval(loadCounts, 45000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [user]);

  return badges;
}
