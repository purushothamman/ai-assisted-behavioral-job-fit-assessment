// src/services/api.js
// Centralised API client.
// All calls go through this module so the base URL is configured in one place.
// Auth token is read from localStorage (set by Supabase Auth after login).

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getAuthHeaders() {
  const session = JSON.parse(localStorage.getItem("sb-session") || "{}");
  const token = session?.access_token;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: getAuthHeaders(),
  };
  if (body !== null) {
    opts.body = JSON.stringify(body);
  }

  const res = await fetch(`${BASE_URL}${path}`, opts);

  if (res.status === 204) return null;

  const data = await res.json();

  if (!res.ok) {
    const msg = data?.detail || data?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }

  return data;
}

// ── Convenience wrappers ─────────────────────────────────────────────────────
export const api = {
  get:    (path)         => request("GET",    path),
  post:   (path, body)   => request("POST",   path, body),
  patch:  (path, body)   => request("PATCH",  path, body),
  delete: (path)         => request("DELETE", path),
};

// ── Job endpoints ─────────────────────────────────────────────────────────────
export const jobsApi = {
  list:   ()              => api.get("/api/jobs"),
  get:    (id)            => api.get(`/api/jobs/${id}`),
  create: (payload)       => api.post("/api/jobs", payload),
  update: (id, payload)   => api.patch(`/api/jobs/${id}`, payload),
  delete: (id)            => api.delete(`/api/jobs/${id}`),
};

// ── Auth endpoints ────────────────────────────────────────────────────────────
export const authApi = {
  me:            ()        => api.get("/api/auth/me"),
  updateProfile: (payload) => api.patch("/api/auth/profile", payload),
};

// ── Health ────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => api.get("/health"),
  db:    () => api.get("/health/db"),
};
