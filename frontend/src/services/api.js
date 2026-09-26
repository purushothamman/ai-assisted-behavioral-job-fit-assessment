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

// ── Dimensions endpoints ──────────────────────────────────────────────────────
export const dimensionsApi = {
  list:   ()   => api.get('/api/dimensions'),
  get:    (id) => api.get(`/api/dimensions/${id}`),
};

// ── Analysis endpoints (Phase 3) ──────────────────────────────────────────────
export const analysisApi = {
  analyze:          (jobId)                   => api.post(`/api/jobs/${jobId}/analyze`),
  listRequirements: (jobId)                   => api.get(`/api/jobs/${jobId}/requirements`),
  updateRequirement:(jobId, reqId, payload)   => api.patch(`/api/jobs/${jobId}/requirements/${reqId}`, payload),
};

// ── Questions endpoints (Phase 4) ─────────────────────────────────────────────
export const questionsApi = {
  generate: (jobId)                      => api.post(`/api/jobs/${jobId}/questions/generate`),
  list:     (jobId)                      => api.get(`/api/jobs/${jobId}/questions`),
  update:   (questionId, jobId, payload) => api.patch(`/api/questions/${questionId}?job_id=${jobId}`, payload),
  delete:   (questionId, jobId)          => api.delete(`/api/questions/${questionId}?job_id=${jobId}`),
};

// ── Sessions endpoints (Phase 5) ──────────────────────────────────────────────
export const sessionsApi = {
  create:  (jobId, payload)  => api.post(`/api/jobs/${jobId}/sessions`, payload),
  list:    (jobId)           => api.get(`/api/jobs/${jobId}/sessions`),
  // Public — no auth required
  getByToken:      (token)   => request('GET',  `/api/sessions/${token}`),
  submitResponses: (token, payload) => request('POST', `/api/sessions/${token}/responses`, payload),
};

// ── Scoring endpoints (Phase 6) ──────────────────────────────────────────────
export const scoringApi = {
  scoreSession: (sessionId) => api.post(`/api/sessions/${sessionId}/score`),
  getScores:    (sessionId) => api.get(`/api/sessions/${sessionId}/scores`),
};

// ── Alignment endpoints (Phase 7) ─────────────────────────────────────────────
export const alignmentApi = {
  calculate:  (sessionId) => api.post(`/api/sessions/${sessionId}/alignment`),
  get:        (sessionId) => api.get(`/api/sessions/${sessionId}/alignment`),
  listForJob: (jobId)     => api.get(`/api/jobs/${jobId}/alignments`),
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
