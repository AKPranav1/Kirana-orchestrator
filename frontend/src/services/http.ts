/** Shared transport. Credentials are supplied by the operator, never bundled. */
export const apiFetch: typeof fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
  const headers = new Headers(init.headers);
  if (typeof window !== 'undefined') {
    const key = sessionStorage.getItem('kirana_operator_token');
    if (key) headers.set('X-API-Key', key);
  }
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401 && typeof window !== 'undefined') {
    window.dispatchEvent(new Event('kirana-auth-required'));
  }
  if (!response.ok && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('kirana-api-error', { detail: `Request failed (${response.status}). Some information may be unavailable; check the backend and retry.` }));
  }
  return response;
};

export async function checkedJson(response: Response) {
  const body = await response.json();
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : 'Invalid request; check the entered fields';
    throw new Error(detail);
  }
  return body;
}
