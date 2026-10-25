import { useState, useCallback } from 'react';
import { releaseApi, ReleaseRequest, ReadinessAssessment } from '@/api/release';

export const useReleaseCase = (requestId?: string) => {
  const [request, setRequest] = useState<ReleaseRequest | null>(null);
  const [readiness, setReadiness] = useState<ReadinessAssessment | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCaseDetails = useCallback(async () => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await releaseApi.getDetail(requestId);
      setRequest(response);
      // Get latest readiness
      if (response.latest_assessment_id) {
        const readinessResponse = await releaseApi.getReadiness(requestId);
        setReadiness(readinessResponse);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch case details';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId]);

  const evaluateReadiness = useCallback(async (force = false) => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await releaseApi.evaluateReadiness(requestId, force);
      setReadiness(response);
      // Refresh case details
      await fetchCaseDetails();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to evaluate readiness';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId, fetchCaseDetails]);

  const startReview = useCallback(async () => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await releaseApi.startReview(requestId);
      setRequest(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start review';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId]);

  const returnForCorrection = useCallback(async (reason: string) => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      await releaseApi.returnForCorrection(requestId, reason);
      await fetchCaseDetails();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to return for correction';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId, fetchCaseDetails]);

  const recommendForAuthority = useCallback(async (reason: string) => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      await releaseApi.recommendForAuthority(requestId, reason);
      await fetchCaseDetails();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to recommend for authority';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId, fetchCaseDetails]);

  const approveRequest = useCallback(async (reason: string) => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      await releaseApi.approve(requestId, reason);
      await fetchCaseDetails();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to approve request';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId, fetchCaseDetails]);

  const rejectRequest = useCallback(async (reason: string) => {
    if (!requestId) return;
    setIsLoading(true);
    setError(null);
    try {
      await releaseApi.reject(requestId, reason);
      await fetchCaseDetails();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reject request';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [requestId, fetchCaseDetails]);

  return {
    request,
    readiness,
    isLoading,
    error,
    fetchCaseDetails,
    evaluateReadiness,
    startReview,
    returnForCorrection,
    recommendForAuthority,
    approveRequest,
    rejectRequest,
  };
};
