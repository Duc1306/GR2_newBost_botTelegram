/**
 * Dashboard API helpers — authenticated fetch wrappers.
 */
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function authHeaders() {
  const token = localStorage.getItem('auth_token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export async function apiGet(path, signal) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders(), signal });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || res.status);
  }
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || res.status);
  }
  return res.json();
}

export async function apiDelete(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE', headers: authHeaders() });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail || res.status);
  }
  return res.json();
}
