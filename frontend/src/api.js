const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export function getApiBase() {
  return API_BASE;
}

export function getToken() {
  return localStorage.getItem('ooh_token');
}

export function setSession(token, user) {
  localStorage.setItem('ooh_token', token);
  localStorage.setItem('ooh_user', JSON.stringify(user));
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('ooh_user'));
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem('ooh_token');
  localStorage.removeItem('ooh_user');
}

export async function apiFetch(path, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = 'Request failed';
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  return response;
}
