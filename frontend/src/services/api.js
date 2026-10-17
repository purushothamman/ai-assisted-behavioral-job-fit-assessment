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
    // Pydantic validation errors come back as detail: [{msg, loc, ...}]
    let msg;
    if (Array.isArray(data?.detail)) {
      msg = data.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join('; ');
    } else {
      msg = data?.detail || data?.message || `Request failed (${res.status})`;
    }
    throw new Error(msg);
  }

  return data;
}

// ── Convenience wrappers ─────────────────────────────────────────────────────
export const api = {
  get:    (path)         => request("GET",    path),
  post:   (path, body)   => request("POST",   path, body),
  put:    (path, body)   => request("PUT",    path, body),
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
  retryEmail: (sessionId)    => api.post(`/api/sessions/${sessionId}/retry-email`),
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

// ── Reports endpoints (Phase 8) ──────────────────────────────────────────────
export const reportsApi = {
  getReport:     (sessionId) => api.get(`/api/sessions/${sessionId}/report`),
  getJobSummary: (jobId)     => api.get(`/api/jobs/${jobId}/reports/summary`),
};


// ── Admin Framework endpoints (Phase 11) ──────────────────────────────────
export const adminFrameworkApi = {
  listVersions:       ()                  => api.get('/api/admin/framework/versions'),
  getCurrentVersion:  ()                  => api.get('/api/admin/framework/current'),
  validateFramework:  ()                  => api.post('/api/admin/framework/validate'),
  publishVersion:     (payload)           => api.post('/api/admin/framework/publish', payload),
  listDimensions:     (includeArchived = true) =>
    api.get(`/api/admin/dimensions${includeArchived ? '?include_archived=true' : '?include_archived=false'}`),
  getDimension:       (id)                => api.get(`/api/admin/dimensions/${id}`),
  createDimension:    (payload)           => api.post('/api/admin/dimensions', payload),
  updateDimension:    (id, payload)       => api.put(`/api/admin/dimensions/${id}`, payload),
  archiveDimension:   (id)                => api.delete(`/api/admin/dimensions/${id}`),
  reorderDimensions:  (items)             => api.patch('/api/admin/dimensions/reorder', { items }),
  addIndicator:       (dimId, payload)    => api.post(`/api/admin/dimensions/${dimId}/indicators`, payload),
  updateIndicator:    (indId, payload)    => api.put(`/api/admin/indicators/${indId}`, payload),
  deleteIndicator:    (indId)             => api.delete(`/api/admin/indicators/${indId}`),
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
