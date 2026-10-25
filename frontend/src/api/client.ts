/**
 * Centralized API Client
 * Configured with environment-based base URL and typed error handling.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Ensure endpoint has leading slash
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  try {
    const res = await fetch(url, {
      credentials: 'include',
      ...options,
      headers,
    });

    const rawText = await res.text();
    let parsed: any = null;
    if (rawText) {
      try {
        parsed = JSON.parse(rawText);
      } catch {
        parsed = rawText;
      }
    }

    if (!res.ok) {
      const message =
        (typeof parsed === 'object' && parsed !== null
          ? parsed.error || parsed.detail || parsed.message
          : null) ||
        (typeof parsed === 'string' ? parsed : null) ||
        res.statusText ||
        'API Request failed';
      throw new ApiError(res.status, message, parsed);
    }

    return (parsed ?? ({} as T)) as T;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err.message || 'Network unreachable');
  }
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'GET', ...options }),

  post: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  put: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  patch: <T>(endpoint: string, body?: any, options?: RequestInit) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  delete: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'DELETE', ...options }),

  getBaseUrl: () => API_BASE_URL,
};
