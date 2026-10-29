/**
 * Centralized API Client
 * Configured with environment-based base URL and typed error handling.
 */

const RAW_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim();

function resolveApiUrl(endpoint: string): string {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  if (!RAW_BASE_URL) {
    return `/api/v1${cleanEndpoint}`;
  }
  const trimmed = RAW_BASE_URL.replace(/\/+$/, '');
  if (trimmed.endsWith('/api/v1')) {
    return `${trimmed}${cleanEndpoint}`;
  }
  return `${trimmed}/api/v1${cleanEndpoint}`;
}

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

const TOKEN_KEY = 'fdr_token';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = resolveApiUrl(endpoint);

  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  let headers: Record<string, string> = {};

  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  // Inject Bearer token from localStorage for seamless cross-domain authentication (Vercel -> Render)
  if (typeof window !== 'undefined') {
    const savedToken = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
    if (savedToken && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${savedToken}`;
    }
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

  getBaseUrl: () => resolveApiUrl(''),
  setToken: (token: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(TOKEN_KEY, token);
    }
  },
  clearToken: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(TOKEN_KEY);
    }
  },
};
