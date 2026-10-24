import { useState, useEffect, useCallback } from 'react';
import { healthApi } from '@/api/endpoints';
import { SystemHealth, ReadinessState } from '@/types';

export function useHealth(pollIntervalMs = 15000) {
  const [liveness, setLiveness] = useState<SystemHealth | null>(null);
  const [readiness, setReadiness] = useState<ReadinessState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const [liveRes, readyRes] = await Promise.allSettled([
        healthApi.getLiveness(),
        healthApi.getReadiness(),
      ]);

      if (liveRes.status === 'fulfilled') {
        setLiveness(liveRes.value);
        setError(null);
      } else {
        setLiveness(null);
        setError(liveRes.reason?.message || 'Backend unreachable');
      }

      if (readyRes.status === 'fulfilled') {
        setReadiness(readyRes.value);
      } else {
        // Readiness can be degraded (503) if DB is not yet running
        const errorData = (readyRes.reason as any)?.data;
        if (errorData) {
          setReadiness(errorData);
        } else {
          setReadiness(null);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Health probe failed');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, pollIntervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, pollIntervalMs]);

  return {
    liveness,
    readiness,
    isLoading,
    error,
    refresh: checkHealth,
  };
}
