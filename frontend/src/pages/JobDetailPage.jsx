// src/pages/JobDetailPage.jsx
// View and edit a single job.
// Phase 3: Behavioral Requirements panel (Groq analysis, confirm/edit per dimension).
// Phase 4: Interview Questions panel (generate, approve/edit/delete per question).
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { jobsApi, analysisApi, questionsApi } from '../services/api'

// ── Styling helpers ──────────────────────────────────────────────────────────
const inputStyle = {
  background: 'var(--color-surface-2)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
}

const STATUS_OPTS = ['draft', 'analyzed', 'questions_generated', 'active', 'closed']

const DIM_META = {
  communication:     { icon: '💬', color: '#6366f1' },
  teamwork:          { icon: '🤝', color: '#22d3ee' },
  adaptability:      { icon: '🔄', color: '#34d399' },
  decision_making:   { icon: '🧠', color: '#fbbf24' },
  leadership:        { icon: '🎯', color: '#f472b6' },
  stress_management: { icon: '⚖️', color: '#a78bfa' },
}

const IMPORTANCE_LABEL = (n) => {
  if (n >= 80) return { text: 'Critical',  color: '#f87171' }
  if (n >= 50) return { text: 'Important', color: '#fbbf24' }
  return              { text: 'Secondary', color: '#94a3b8' }
}

const DIFFICULTY_COLOR = {
  easy:   { bg: 'rgba(52,211,153,.15)',  color: '#34d399' },
  medium: { bg: 'rgba(251,191,36,.15)',  color: '#fbbf24' },
  hard:   { bg: 'rgba(248,113,113,.15)', color: '#f87171' },
}

const TYPE_COLOR = {
  behavioral:  { bg: 'rgba(99,102,241,.15)',  color: '#818cf8' },
  situational: { bg: 'rgba(34,211,238,.15)',  color: '#22d3ee' },
  competency:  { bg: 'rgba(244,114,182,.15)', color: '#f472b6' },
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
  const [reqs, setReqs]               = useState([])
  const [reqsLoading, setReqsLoading] = useState(false)
  const [analyzing, setAnalyzing]     = useState(false)
  const [analyzeError, setAnalyzeError] = useState('')
  const [editingReqId, setEditingReqId] = useState(null)
  const [reqForm, setReqForm]         = useState({})
  const [savingReq, setSavingReq]     = useState(false)

  // Questions state
  const [questions, setQuestions]           = useState([])
  const [questionsLoading, setQuestionsLoading] = useState(false)
  const [generating, setGenerating]         = useState(false)
  const [generateError, setGenerateError]   = useState('')
  const [editingQId, setEditingQId]         = useState(null)
  const [qForm, setQForm]                   = useState({})
  const [savingQ, setSavingQ]               = useState(false)
  const [deletingQId, setDeletingQId]       = useState(null)

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
      .catch(() => {})
      .finally(() => setReqsLoading(false))
  }, [id])

  // Load questions when job is ready
  const loadQuestions = useCallback(() => {
    if (!id) return
    setQuestionsLoading(true)
    questionsApi.list(id)
      .then(r => setQuestions(r.data ?? []))
      .catch(() => {})
      .finally(() => setQuestionsLoading(false))
  }, [id])

  useEffect(() => {
    if (job) {
      loadRequirements()
      loadQuestions()
    }
  }, [job, loadRequirements, loadQuestions])

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

  // ── Question generation ──────────────────────────────────────────────────
  const handleGenerateQuestions = async () => {
    setGenerating(true); setGenerateError('')
    try {
      const res = await questionsApi.generate(id)
      setQuestions(res.data ?? [])
      const updated = await jobsApi.get(id)
      setJob(updated.data); setForm(updated.data)
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  // ── Question edit / approve ──────────────────────────────────────────────
  const startEditQ = (q) => {
    setEditingQId(q.id)
    setQForm({
      question: q.question,
      type: q.type,
      difficulty: q.difficulty,
      indicators: (q.indicators ?? []).join('\n'),
    })
  }

  const handleSaveQ = async (qId) => {
    setSavingQ(true)
    try {
      const payload = {
        question:   qForm.question,
        type:       qForm.type,
        difficulty: qForm.difficulty,
        indicators: qForm.indicators.split('\n').map(s => s.trim()).filter(Boolean),
        approved:   true,
      }
      const res = await questionsApi.update(qId, id, payload)
      setQuestions(prev => prev.map(q => q.id === qId ? res.data : q))
      setEditingQId(null)
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setSavingQ(false)
    }
  }

  const handleApproveQ = async (qId) => {
    try {
      const res = await questionsApi.update(qId, id, { approved: true })
      setQuestions(prev => prev.map(q => q.id === qId ? res.data : q))
    } catch (err) {
      setGenerateError(err.message)
    }
  }

  const handleDeleteQ = async (qId) => {
    if (!confirm('Delete this question?')) return
    setDeletingQId(qId)
    try {
      await questionsApi.delete(qId, id)
      setQuestions(prev => prev.filter(q => q.id !== qId))
    } catch (err) {
      setGenerateError(err.message)
    } finally {
      setDeletingQId(null)
    }
  }

  const handleApproveAllQ = async () => {
    const unapproved = questions.filter(q => !q.approved)
    for (const q of unapproved) {
      await questionsApi.update(q.id, id, { approved: true })
    }
    loadQuestions()
  }

  // ── Guards ───────────────────────────────────────────────────────────────
  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-muted)' }}>Loading…</div>
  if (!job)    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-danger)' }}>Job not found.</div>

  const allConfirmed    = reqs.length > 0 && reqs.every(r => r.confirmed)
  const confirmedCount  = reqs.filter(r => r.confirmed).length
  const approvedCount   = questions.filter(q => q.approved).length
  const allApproved     = questions.length > 0 && questions.every(q => q.approved)

  // Group questions by dimension for display
  const questionsByDim = questions.reduce((acc, q) => {
    const dim = q.dimension_name ?? 'unknown'
    if (!acc[dim]) acc[dim] = []
    acc[dim].push(q)
    return acc
  }, {})

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

      {/* ── Behavioral Requirements ──────────────────────────────────────── */}
      <div style={{ borderRadius: 12, background: 'var(--color-surface)', border: '1px solid var(--color-border)', overflow: 'hidden', marginBottom: 16 }}>
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

        {analyzeError && (
          <div style={{ padding: '12px 24px', background: 'rgba(248,113,113,.08)', borderBottom: '1px solid var(--color-border)' }}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--color-danger)' }}>{analyzeError}</p>
          </div>
        )}

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

      {/* ── Interview Questions ──────────────────────────────────────────── */}
      <div style={{ borderRadius: 12, background: 'var(--color-surface)', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
        {/* Panel header */}
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--color-text)' }}>
              Interview Questions
            </h2>
            <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--color-muted)' }}>
              {questions.length === 0
                ? 'Confirm requirements above, then generate STAR-format questions.'
                : `${approvedCount}/${questions.length} approved`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {questions.length > 0 && !allApproved && (
              <button
                id="btn-approve-all-questions"
                onClick={handleApproveAllQ}
                style={btnStyle('rgba(52,211,153,.12)', 'var(--color-success)', '11px')}
              >
                Approve All
              </button>
            )}
            <button
              id="btn-generate-questions"
              onClick={handleGenerateQuestions}
              disabled={generating || confirmedCount === 0}
              title={confirmedCount === 0 ? 'Confirm at least one requirement first' : undefined}
              style={btnStyle(
                generating || confirmedCount === 0 ? 'var(--color-border)' : '#7c3aed',
                '#fff', '12px'
              )}
            >
              {generating ? '⏳ Generating…' : questions.length > 0 ? '🔄 Re-generate' : '❓ Generate Questions'}
            </button>
          </div>
        </div>

        {/* Generate error */}
        {generateError && (
          <div style={{ padding: '12px 24px', background: 'rgba(248,113,113,.08)', borderBottom: '1px solid var(--color-border)' }}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--color-danger)' }}>{generateError}</p>
          </div>
        )}

        {/* Confirm hint */}
        {confirmedCount === 0 && reqs.length > 0 && (
          <div style={{ padding: '10px 24px', background: 'rgba(251,191,36,.08)', borderBottom: '1px solid var(--color-border)' }}>
            <p style={{ margin: 0, fontSize: 12, color: '#fbbf24' }}>
              ⚠ Confirm at least one behavioral requirement above to enable question generation.
            </p>
          </div>
        )}

        {/* Questions list */}
        <div style={{ padding: questionsLoading || questions.length === 0 ? 24 : 0 }}>
          {questionsLoading ? (
            <p style={{ margin: 0, color: 'var(--color-muted)', fontSize: 13 }}>Loading questions…</p>
          ) : questions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <p style={{ margin: 0, fontSize: 32 }}>❓</p>
              <p style={{ margin: '8px 0 0', color: 'var(--color-muted)', fontSize: 13 }}>
                {confirmedCount > 0
                  ? 'Click "Generate Questions" to create STAR-format interview questions.'
                  : 'Confirm behavioral requirements above first.'}
              </p>
            </div>
          ) : (
            Object.entries(questionsByDim).map(([dimName, dimQuestions], gi) => {
              const meta = DIM_META[dimName] ?? { icon: '•', color: 'var(--color-muted)' }
              const dimLabel = dimName.replace(/_/g, ' ')

              return (
                <div key={dimName}>
                  {/* Dimension group header */}
                  <div style={{
                    padding: '12px 24px 8px',
                    borderTop: gi === 0 ? 'none' : '1px solid var(--color-border)',
                    display: 'flex', alignItems: 'center', gap: 8,
                    background: 'var(--color-surface-2)',
                  }}>
                    <span style={{ fontSize: 16 }}>{meta.icon}</span>
                    <span style={{
                      fontSize: 12, fontWeight: 700, textTransform: 'capitalize',
                      color: meta.color, letterSpacing: '0.04em',
                    }}>
                      {dimLabel}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                      · {dimQuestions.filter(q => q.approved).length}/{dimQuestions.length} approved
                    </span>
                  </div>

                  {/* Questions in this dimension */}
                  {dimQuestions.map((q, qi) => {
                    const isEditQ = editingQId === q.id
                    const diffStyle = DIFFICULTY_COLOR[q.difficulty] ?? { bg: 'transparent', color: 'var(--color-muted)' }
                    const typeStyle = TYPE_COLOR[q.type] ?? { bg: 'transparent', color: 'var(--color-muted)' }

                    return (
                      <div key={q.id} style={{
                        padding: '16px 24px',
                        borderTop: '1px solid var(--color-border)',
                        background: q.approved ? 'rgba(52,211,153,0.03)' : 'transparent',
                        transition: 'background 0.2s',
                      }}>
                        {isEditQ ? (
                          /* Edit mode */
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <Field label="Question">
                              <textarea
                                rows={3}
                                value={qForm.question}
                                onChange={e => setQForm(f => ({ ...f, question: e.target.value }))}
                                style={{ ...inputStyle, width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }}
                              />
                            </Field>
                            <div style={{ display: 'flex', gap: 12 }}>
                              <Field label="Type">
                                <select
                                  value={qForm.type}
                                  onChange={e => setQForm(f => ({ ...f, type: e.target.value }))}
                                  style={{ ...inputStyle, padding: '6px 10px', borderRadius: 8, fontSize: 13 }}
                                >
                                  {['behavioral', 'situational', 'competency'].map(t => <option key={t} value={t}>{t}</option>)}
                                </select>
                              </Field>
                              <Field label="Difficulty">
                                <select
                                  value={qForm.difficulty}
                                  onChange={e => setQForm(f => ({ ...f, difficulty: e.target.value }))}
                                  style={{ ...inputStyle, padding: '6px 10px', borderRadius: 8, fontSize: 13 }}
                                >
                                  {['easy', 'medium', 'hard'].map(d => <option key={d} value={d}>{d}</option>)}
                                </select>
                              </Field>
                            </div>
                            <Field label="Success Indicators (one per line)">
                              <textarea
                                rows={3}
                                value={qForm.indicators}
                                onChange={e => setQForm(f => ({ ...f, indicators: e.target.value }))}
                                style={{ ...inputStyle, width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }}
                              />
                            </Field>
                            <div style={{ display: 'flex', gap: 8 }}>
                              <button onClick={() => setEditingQId(null)} style={btnStyle('var(--color-surface-2)', 'var(--color-muted)', '11px')}>Cancel</button>
                              <button
                                onClick={() => handleSaveQ(q.id)}
                                disabled={savingQ}
                                style={btnStyle('#7c3aed', '#fff', '11px')}
                              >
                                {savingQ ? 'Saving…' : 'Save & Approve'}
                              </button>
                            </div>
                          </div>
                        ) : (
                          /* View mode */
                          <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                            <div style={{ flex: 1 }}>
                              {/* Badges row */}
                              <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                                <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99, background: typeStyle.bg, color: typeStyle.color }}>
                                  {q.type}
                                </span>
                                <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99, background: diffStyle.bg, color: diffStyle.color }}>
                                  {q.difficulty}
                                </span>
                                {q.approved && (
                                  <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99, background: 'rgba(52,211,153,.15)', color: 'var(--color-success)' }}>
                                    ✓ Approved
                                  </span>
                                )}
                                <span style={{ fontSize: 10, color: 'var(--color-muted)' }}>Q{qi + 1}</span>
                              </div>

                              {/* Question text */}
                              <p style={{ margin: '0 0 10px', fontSize: 14, color: 'var(--color-text)', lineHeight: 1.55 }}>
                                {q.question}
                              </p>

                              {/* Indicators */}
                              {q.indicators?.length > 0 && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                  {q.indicators.map((ind, ii) => (
                                    <span key={ii} style={{
                                      fontSize: 11, padding: '3px 10px', borderRadius: 99,
                                      background: 'var(--color-surface-2)', color: 'var(--color-muted)',
                                      border: '1px solid var(--color-border)',
                                    }}>
                                      {ind}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>

                            {/* Action buttons */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
                              {!q.approved && (
                                <button
                                  id={`btn-approve-q-${q.id}`}
                                  onClick={() => handleApproveQ(q.id)}
                                  style={btnStyle('rgba(52,211,153,.15)', 'var(--color-success)', '11px')}
                                >
                                  ✓ Approve
                                </button>
                              )}
                              <button
                                id={`btn-edit-q-${q.id}`}
                                onClick={() => startEditQ(q)}
                                style={btnStyle('var(--color-surface-2)', 'var(--color-muted)', '11px')}
                              >
                                Edit
                              </button>
                              <button
                                id={`btn-delete-q-${q.id}`}
                                onClick={() => handleDeleteQ(q.id)}
                                disabled={deletingQId === q.id}
                                style={btnStyle('rgba(248,113,113,.1)', 'var(--color-danger)', '11px')}
                              >
                                {deletingQId === q.id ? '…' : 'Delete'}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )
            })
          )}
        </div>
      </div>
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
  const colors = {
    draft: '#94a3b8', analyzed: '#6366f1',
    questions_generated: '#7c3aed', active: '#34d399', closed: '#f87171'
  }
  return (
    <span style={{ fontSize: 11, fontWeight: 600, color: colors[status] ?? '#94a3b8', textTransform: 'capitalize' }}>
      {status?.replace(/_/g, ' ')}
    </span>
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
