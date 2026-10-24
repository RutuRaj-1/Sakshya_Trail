import { apiClient } from './client';
import {
  SystemHealth,
  ReadinessState,
  RoleInfo,
  Institution,
  Instrument,
  InstrumentSummary,
} from '@/types';

export const healthApi = {
  getLiveness: () => apiClient.get<SystemHealth>('/health/live'),
  getReadiness: () => apiClient.get<ReadinessState>('/health/ready'),
};

export const authApi = {
  getRoles: () => apiClient.get<RoleInfo[]>('/auth/roles'),
  getBootstrap: () => apiClient.get<any>('/auth/session/bootstrap'),
};

export const institutionsApi = {
  list: (params?: { state?: string }) => {
    const query = params?.state ? `?state=${encodeURIComponent(params.state)}` : '';
    return apiClient.get<Institution[]>(`/institutions${query}`);
  },
  create: (data: Partial<Institution>) =>
    apiClient.post<Institution>('/institutions', data),
};

export const instrumentsApi = {
  list: (params?: { institution_id?: string; status?: string }) => {
    const sp = new URLSearchParams();
    if (params?.institution_id) sp.append('institution_id', params.institution_id);
    if (params?.status) sp.append('status', params.status);
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiClient.get<Instrument[]>(`/instruments${query}`);
  },
  getSummary: () => apiClient.get<InstrumentSummary>('/instruments/summary'),
  create: (data: Partial<Instrument>) =>
    apiClient.post<Instrument>('/instruments', data),
};
