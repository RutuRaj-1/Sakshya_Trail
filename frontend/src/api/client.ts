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

  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  let headers: Record<string, string> = {};

  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (options.headers) {
    if (typeof Headers !== 'undefined' && options.headers instanceof Headers) {
      options.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(options.headers)) {
      for (const [key, value] of options.headers) {
        headers[key] = value;
      }
    } else {
      headers = { ...headers, ...(options.headers as Record<string, string>) };
    }
  }

  if (isFormData) {
    // If body is FormData, delete any manually passed Content-Type header so that
    // fetch/browser generates the proper multipart boundary automatically.
    for (const key of Object.keys(headers)) {
      if (key.toLowerCase() === 'content-type') {
        delete headers[key];
      }
    }
  }

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

  post: <T>(endpoint: string, body?: any, options?: RequestInit) => {
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
    return request<T>(endpoint, {
      method: 'POST',
      body: isFormData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
      ...options,
    });
  },

  put: <T>(endpoint: string, body?: any, options?: RequestInit) => {
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
    return request<T>(endpoint, {
      method: 'PUT',
      body: isFormData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
      ...options,
    });
  },

  patch: <T>(endpoint: string, body?: any, options?: RequestInit) => {
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
    return request<T>(endpoint, {
      method: 'PATCH',
      body: isFormData ? body : (body !== undefined ? JSON.stringify(body) : undefined),
      ...options,
    });
  },

  delete: <T>(endpoint: string, options?: RequestInit) =>
    request<T>(endpoint, { method: 'DELETE', ...options }),

  getBaseUrl: () => API_BASE_URL,
};
