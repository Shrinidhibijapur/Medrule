/**
 * MedRule API Client
 * - Enforces credentials: 'include' for HttpOnly SameSite session cookies
 * - Automatically attaches X-CSRF-Token on state-mutating requests (POST, PATCH, PUT, DELETE)
 * - Never stores tokens or passwords in localStorage
 */

let inMemoryCsrfToken: string | null = null;

export const setCsrfToken = (token: string | null): void => {
  inMemoryCsrfToken = token;
};

export const getCsrfToken = (): string | null => {
  if (inMemoryCsrfToken) return inMemoryCsrfToken;
  // Fallback to reading cookie if exposed as non-httponly
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|;\s*)medrule_csrf=([^;]+)/);
    if (match) {
      inMemoryCsrfToken = decodeURIComponent(match[1]);
      return inMemoryCsrfToken;
    }
  }
  return null;
};

export const apiFetch = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> => {
  const options: RequestInit = {
    ...init,
    credentials: 'include', // Always send and accept HttpOnly session cookies
  };

  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  // For state-changing requests, ensure CSRF header is attached
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf && !headers.has('X-CSRF-Token') && !headers.has('x-csrf-token')) {
      headers.set('X-CSRF-Token', csrf);
    }
  }

  options.headers = headers;

  const response = await fetch(input, options);

  // If unauthorized or expired session, dispatch an auth event
  if (response.status === 401 && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('medrule:unauthorized'));
  }

  return response;
};
