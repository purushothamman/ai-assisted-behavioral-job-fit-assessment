// src/pages/JobDetailPage.jsx
// View and edit a single job.
// Phase 3: shows a live Behavioral Requirements panel — recruiter can trigger
// Groq analysis, then review + confirm/adjust each dimension requirement.
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { jobsApi, dimensionsApi } from '../services/api'

// ── analysisApi — thin wrappers (not yet in api.js, defined inline here) ──
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getAuthHeaders() {
  const session = JSON.parse(localStorage.getItem('sb-session') || '{}')
  const token = session?.access_token
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function apiFetch(method, path, body = null) {
  const opts = { method, headers: getAuthHeaders() }
  if (body !== null) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE_URL}${path}`, opts)
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) throw new Error(data?.detail || data?.message || `Error ${res.status}`)
  return data
}

const analysisApi = {
  analyze:         (jobId)                  => apiFetch('POST',  `/api/jobs/${jobId}/analyze`),
  listRequirements:(jobId)                  => apiFetch('GET',   `/api/jobs/${jobId}/requirements`),
  updateRequirement:(jobId, reqId, payload) => apiFetch('PATCH', `/api/jobs/${jobId}/requirements/${reqId}`, payload),
}

// ── Styling helpers ──────────────────────────────────────────────────────────
const inputStyle = {
  background: 'var(--color-surface-2)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
}

const STATUS_OPTS = ['draft', 'analyzed', 'active', 'closed']

const DIM_META = {
  communication:     { icon: '💬', color: '#6366f1' },
  teamwork:          { icon: '🤝', color: '#22d3ee' },
  adaptability:      { icon: '🔄', color: '#34d399' },
  decision_making:   { icon: '🧠', color: '#fbbf24' },
  leadership:        { icon: '🎯', color: '#f472b6' },
  stress_management: { icon: '⚖️', color: '#a78bfa' },
}

const IMPORTANCE_LABEL = (n) => {
  if (n >= 80) return { text: 'Critical',   color: '#f87171' }
  if (n >= 50) return { text: 'Important',  color: '#fbbf24' }
  return              { text: 'Secondary',  color: '#94a3b8' }
}

// ── Main component ────────────────────────────────────────────────────────────
export default function JobDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  // Job state
  const [job, setJob]         = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm]       = useState({})
  const [error, setError]     = useState('')
  const [saved, setSaved]     = useState(false)

  // Requirements state
  const [reqs, setReqs]             = useState([])
  const [reqsLoading, setReqsLoading] = useState(false)
  const [analyzing, setAnalyzing]   = useState(false)
  const [analyzeError, setAnalyzeError] = useState('')
  const [editingReqId, setEditingReqId] = useState(null)
  const [reqForm, setReqForm]       = useState({})
  const [savingReq, setSavingReq]   = useState(false)

  // Load job
  useEffect(() => {
    jobsApi.get(id)
      .then(r => { setJob(r.data); setForm(r.data) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  // Load requirements when job is ready
  const loadRequirements = useCallback(() => {
    if (!id) return
    setReqsLoading(true)
    analysisApi.listRequirements(id)
      .then(r => setReqs(r.data ?? []))
      .catch(() => {})   // silent — no reqs yet is fine
      .finally(() => setReqsLoading(false))
  }, [id])

  useEffect(() => { if (job) loadRequirements() }, [job, loadRequirements])

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }))

  // ── Job save / delete ────────────────────────────────────────────────────
  const handleSave = async () => {
    setSaving(true); setError(''); setSaved(false)
    try {
      const res = await jobsApi.update(id, {
        title: form.title, description: form.description,
        responsibilities: form.responsibilities, requirements: form.requirements,
        status: form.status,
      })
      setJob(res.data); setEditing(false); setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete this job? This cannot be undone.')) return
    setDeleting(true)
    try {
      await jobsApi.delete(id); navigate('/jobs')
    } catch (err) {
      setError(err.message); setDeleting(false)
    }
  }

  // ── Groq analysis ────────────────────────────────────────────────────────
  const handleAnalyze = async () => {
    setAnalyzing(true); setAnalyzeError('')
    try {
      const res = await analysisApi.analyze(id)
      setReqs(res.data ?? [])
      // Refresh job to pick up status→'analyzed'
      const updated = await jobsApi.get(id)
      setJob(updated.data); setForm(updated.data)
    } catch (err) {
      setAnalyzeError(err.message)
    } finally {
      setAnalyzing(false)
    }
  }

  // ── Requirement confirm/edit ─────────────────────────────────────────────
  const startEditReq = (req) => {
    setEditingReqId(req.id)
    setReqForm({ importance: req.importance, reason: req.reason, confirmed: req.confirmed })
  }

  const handleSaveReq = async (reqId) => {
    setSavingReq(true)
    try {
      const res = await analysisApi.updateRequirement(id, reqId, reqForm)
      setReqs(prev => prev.map(r => r.id === reqId ? res.data : r))
      setEditingReqId(null)
    } catch (err) {
      setAnalyzeError(err.message)
    } finally {
      setSavingReq(false)
    }
  }

  const handleConfirmAll = async () => {
    const unconfirmed = reqs.filter(r => !r.confirmed)
    for (const req of unconfirmed) {
      await analysisApi.updateRequirement(id, req.id, { confirmed: true })
    }
    loadRequirements()
  }

  // ── Guards ───────────────────────────────────────────────────────────────
  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-muted)' }}>Loading…</div>
  if (!job)    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-danger)' }}>Job not found.</div>

  const allConfirmed = reqs.length > 0 && reqs.every(r => r.confirmed)
  const confirmedCount = reqs.filter(r => r.confirmed).length

  return (
    <div style={{ maxWidth: 780, margin: '0 auto', padding: '40px 24px 80px' }}>
      {/* Back */}
      <button onClick={() => navigate('/jobs')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-muted)', fontSize: 13, marginBottom: 24, padding: 0 }}>
        ← Back to Jobs
      </button>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: 'var(--color-text)' }}>{job.title}</h1>
          <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--color-muted)' }}>
            Created {new Date(job.created_at).toLocaleDateString()}
            {' · '}
            <StatusBadge status={job.status} />
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {!editing && (
            <button onClick={() => setEditing(true)} style={btnStyle('var(--color-surface-2)', 'var(--color-text)')}>Edit</button>
          )}
          <button onClick={handleDelete} disabled={deleting} style={btnStyle('rgba(248,113,113,.15)', 'var(--color-danger)')}>
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && <Alert type="error" msg={error} />}
      {saved && <Alert type="success" msg="Saved successfully." />}

      {/* Job detail card */}
      <div style={{ borderRadius: 12, padding: 24, marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 20, background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        {editing ? (
          <>
            <Field label="Title">
              <input value={form.title} onChange={set('title')} style={{ ...inputStyle, ...fieldInput }} />
            </Field>
            <Field label="Status">
              <select value={form.status} onChange={set('status')} style={{ ...inputStyle, ...fieldInput }}>
                {STATUS_OPTS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Description">
              <textarea rows={5} value={form.description || ''} onChange={set('description')} style={{ ...inputStyle, ...fieldInput, resize: 'vertical' }} />
            </Field>
            <Field label="Responsibilities">
              <textarea rows={4} value={form.responsibilities || ''} onChange={set('responsibilities')} style={{ ...inputStyle, ...fieldInput, resize: 'vertical' }} />
            </Field>
            <Field label="Requirements">
              <textarea rows={4} value={form.requirements || ''} onChange={set('requirements')} style={{ ...inputStyle, ...fieldInput, resize: 'vertical' }} />
            </Field>
            <div style={{ display: 'flex', gap: 12 }}>
              <button onClick={() => { setEditing(false); setForm(job) }} style={{ ...btnStyle('var(--color-surface-2)', 'var(--color-muted)'), flex: 1, padding: '10px 0' }}>Cancel</button>
              <button onClick={handleSave} disabled={saving} style={{ ...btnStyle(saving ? 'var(--color-border)' : 'var(--color-primary)', '#fff'), flex: 1, padding: '10px 0', fontWeight: 600 }}>
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </>
        ) : (
          <>
            <Section label="Description"      value={job.description} />
            <Section label="Responsibilities" value={job.responsibilities} />
            <Section label="Requirements"     value={job.requirements} />
          </>
        )}
      </div>

      {/* ── Behavioral Requirements ────────────────────────────────────── */}
      <div style={{ borderRadius: 12, background: 'var(--color-surface)', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
        {/* Panel header */}
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--color-text)' }}>
              Behavioral Requirements
            </h2>
            <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--color-muted)' }}>
              {reqs.length === 0
                ? 'Run Groq analysis to extract dimensions from the job description.'
                : `${confirmedCount}/${reqs.length} confirmed`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {reqs.length > 0 && !allConfirmed && (
              <button onClick={handleConfirmAll} style={btnStyle('rgba(52,211,153,.12)', 'var(--color-success)', '11px')}>
                Confirm All
              </button>
            )}
            <button
              id="btn-analyze-job"
              onClick={handleAnalyze}
              disabled={analyzing}
              style={btnStyle(
                analyzing ? 'var(--color-border)' : 'var(--color-primary)',
                '#fff', '12px'
              )}
            >
              {analyzing ? '⏳ Analyzing…' : reqs.length > 0 ? '🔄 Re-analyze' : '🤖 Analyze with AI'}
            </button>
          </div>
        </div>

        {/* Error */}
        {analyzeError && (
          <div style={{ padding: '12px 24px', background: 'rgba(248,113,113,.08)', borderBottom: '1px solid var(--color-border)' }}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--color-danger)' }}>{analyzeError}</p>
          </div>
        )}

        {/* Requirements list */}
        <div style={{ padding: reqsLoading || reqs.length === 0 ? 24 : 0 }}>
          {reqsLoading ? (
            <p style={{ margin: 0, color: 'var(--color-muted)', fontSize: 13 }}>Loading requirements…</p>
          ) : reqs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <p style={{ margin: 0, fontSize: 32 }}>🧠</p>
              <p style={{ margin: '8px 0 0', color: 'var(--color-muted)', fontSize: 13 }}>
                Click "Analyze with AI" to extract behavioral requirements.
              </p>
            </div>
          ) : (
            reqs.map((req, i) => {
              const meta   = DIM_META[req.dimension_name] ?? { icon: '•', color: 'var(--color-muted)' }
              const label  = IMPORTANCE_LABEL(req.importance)
              const isEdit = editingReqId === req.id
              const dimLabel = req.dimension_name?.replace(/_/g, ' ') ?? '—'

              return (
                <div key={req.id} style={{
                  padding: '18px 24px',
                  borderTop: i === 0 ? 'none' : '1px solid var(--color-border)',
                  background: req.confirmed ? 'rgba(52,211,153,0.04)' : 'transparent',
                }}>
                  {isEdit ? (
                    /* Edit mode */
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 20 }}>{meta.icon}</span>
                        <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text)', textTransform: 'capitalize' }}>{dimLabel}</span>
                      </div>
                      <Field label={`Importance (${reqForm.importance})`}>
                        <input
                          type="range" min={0} max={100}
                          value={reqForm.importance}
                          onChange={e => setReqForm(f => ({ ...f, importance: Number(e.target.value) }))}
                          style={{ width: '100%', accentColor: meta.color }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--color-muted)', marginTop: 2 }}>
                          <span>0 — Not needed</span><span>50 — Important</span><span>100 — Critical</span>
                        </div>
                      </Field>
                      <Field label="Reason">
                        <textarea
                          rows={3}
                          value={reqForm.reason}
                          onChange={e => setReqForm(f => ({ ...f, reason: e.target.value }))}
                          style={{ ...inputStyle, width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }}
                        />
                      </Field>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => setEditingReqId(null)} style={btnStyle('var(--color-surface-2)', 'var(--color-muted)', '11px')}>Cancel</button>
                        <button
                          onClick={() => { setReqForm(f => ({ ...f, confirmed: true })); handleSaveReq(req.id) }}
                          disabled={savingReq}
                          style={btnStyle('var(--color-primary)', '#fff', '11px')}
                        >
                          {savingReq ? 'Saving…' : 'Save & Confirm'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* View mode */
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                      <div style={{ fontSize: 24, flexShrink: 0, marginTop: 2 }}>{meta.icon}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--color-text)', textTransform: 'capitalize' }}>{dimLabel}</span>
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 99, fontWeight: 600, background: `${label.color}22`, color: label.color }}>
                            {label.text} — {req.importance}
                          </span>
                          {req.confirmed && (
                            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 99, background: 'rgba(52,211,153,.15)', color: 'var(--color-success)', fontWeight: 600 }}>
                              ✓ Confirmed
                            </span>
                          )}
                        </div>
                        {/* Importance bar */}
                        <div style={{ height: 4, borderRadius: 2, background: 'var(--color-border)', marginBottom: 8, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${req.importance}%`, background: meta.color, borderRadius: 2, transition: 'width 0.4s ease' }} />
                        </div>
                        <p style={{ margin: 0, fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.5 }}>{req.reason}</p>
                      </div>
                      <button
                        onClick={() => startEditReq(req)}
                        style={{ ...btnStyle('var(--color-surface-2)', 'var(--color-muted)', '11px'), flexShrink: 0 }}
                      >
                        {req.confirmed ? 'Edit' : 'Review'}
                      </button>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Phase 4 placeholder */}
      <PlaceholderSection title="Assessment Questions" phase="Phase 4" description="Role-specific behavioral questions will be generated from confirmed requirements." />
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Section({ label, value }) {
  if (!value) return null
  return (
    <div>
      <p style={{ margin: '0 0 4px', fontSize: 12, fontWeight: 500, color: 'var(--color-muted)' }}>{label}</p>
      <p style={{ margin: 0, fontSize: 14, color: 'var(--color-text)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{value}</p>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--color-muted)', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}

function Alert({ type, msg }) {
  const colors = type === 'error'
    ? { color: 'var(--color-danger)', bg: 'rgba(248,113,113,.1)' }
    : { color: 'var(--color-success)', bg: 'rgba(52,211,153,.1)' }
  return (
    <p style={{ fontSize: 13, marginBottom: 12, padding: '10px 14px', borderRadius: 8, color: colors.color, background: colors.bg }}>
      {msg}
    </p>
  )
}

function StatusBadge({ status }) {
  const colors = { draft: '#94a3b8', analyzed: '#6366f1', active: '#34d399', closed: '#f87171' }
  return (
    <span style={{ fontSize: 11, fontWeight: 600, color: colors[status] ?? '#94a3b8', textTransform: 'capitalize' }}>
      {status}
    </span>
  )
}

function PlaceholderSection({ title, phase, description }) {
  return (
    <div style={{ borderRadius: 12, padding: 20, marginTop: 16, background: 'var(--color-surface)', border: '1px dashed var(--color-border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 99, background: 'rgba(99,102,241,.15)', color: 'var(--color-primary-h)', fontWeight: 600 }}>{phase}</span>
        <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: 'var(--color-text)' }}>{title}</p>
      </div>
      <p style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)' }}>{description}</p>
    </div>
  )
}

// ── Style helpers ─────────────────────────────────────────────────────────────
const fieldInput = { width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box' }

function btnStyle(bg, color, fontSize = '13px') {
  return {
    background: bg, color, fontSize,
    padding: '6px 14px', borderRadius: 8,
    border: 'none', cursor: 'pointer',
    fontWeight: 500, lineHeight: 1.4,
    transition: 'opacity 0.15s',
  }
}
