// src/pages/CandidatePage.jsx
// Phase 5 -- Public candidate assessment page.
// Accessed via /assess/:token -- no auth required.
// Fetches session + approved questions, collects STAR answers, submits all at once.
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { sessionsApi } from '../services/api'

// -- Constants -----------------------------------------------------------------
const MIN_ANSWER_LEN = 10   // mirrors backend ResponseCreate min_length

const DIFFICULTY_META = {
  easy:   { label: 'Easy',   color: '#34d399', bg: 'rgba(52,211,153,.12)' },
  medium: { label: 'Medium', color: '#fbbf24', bg: 'rgba(251,191,36,.12)' },
  hard:   { label: 'Hard',   color: '#f87171', bg: 'rgba(248,113,113,.12)' },
}

const TYPE_META = {
  behavioral:  { label: 'Behavioral',  color: '#818cf8', bg: 'rgba(99,102,241,.12)' },
  situational: { label: 'Situational', color: '#22d3ee', bg: 'rgba(34,211,238,.12)' },
  competency:  { label: 'Competency',  color: '#f472b6', bg: 'rgba(244,114,182,.12)' },
}

const STAR_STEPS = [
  { label: 'S - Situation', hint: 'Describe the context and background.' },
  { label: 'T - Task',      hint: 'What was your specific responsibility?' },
  { label: 'A - Action',    hint: 'What steps did YOU take?' },
  { label: 'R - Result',    hint: 'What was the outcome? Use numbers where possible.' },
]

// -- Helpers -------------------------------------------------------------------
function Badge({ label, color, bg }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 99,
      color, background: bg, flexShrink: 0,
    }}>
      {label}
    </span>
  )
}

function Card({ children, style }) {
  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderRadius: 14,
      ...(style || {}),
    }}>
      {children}
    </div>
  )
}

// -- Spinner -------------------------------------------------------------------
function Spinner() {
  return (
    <div style={{
      width: 36, height: 36, borderRadius: '50%',
      border: '3px solid var(--color-border)',
      borderTopColor: 'var(--color-primary)',
      animation: 'spin 0.8s linear infinite',
    }} />
  )
}

// -- Layout wrapper ------------------------------------------------------------
function PageShell({ children }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-bg)', padding: '40px 16px 80px' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        {children}
      </div>
    </div>
  )
}

// -- Main component ------------------------------------------------------------
export default function CandidatePage() {
  const { token } = useParams()

  // Session
  const [session, setSession]       = useState(null)
  const [loading, setLoading]       = useState(true)
  const [fetchError, setFetchError] = useState('')   // 'not_found'|'expired'|'completed'|'error'

  // Answers: { [questionId]: string }
  const [answers, setAnswers]   = useState({})
  const [touched, setTouched]   = useState({})

  // Submission
  const [submitting, setSubmitting]   = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [submitted, setSubmitted]     = useState(false)

  // Load session on mount
  useEffect(() => {
    if (!token) { setFetchError('not_found'); setLoading(false); return }

    sessionsApi.getByToken(token)
      .then(res => {
        const data = res.data
        setSession(data)
        const init = {}
        data.questions.forEach(q => { init[q.id] = '' })
        setAnswers(init)
      })
      .catch(err => {
        const msg = (err.message || '').toLowerCase()
        if (msg.includes('expired'))          setFetchError('expired')
        else if (msg.includes('submitted'))   setFetchError('completed')
        else if (msg.includes('not found'))   setFetchError('not_found')
        else                                  setFetchError('error')
      })
      .finally(() => setLoading(false))
  }, [token])

  const setAnswer = (qId, val) => setAnswers(prev => ({ ...prev, [qId]: val }))
  const handleBlur = (qId)     => setTouched(prev => ({ ...prev, [qId]: true }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    const allTouched = {}
    session.questions.forEach(q => { allTouched[q.id] = true })
    setTouched(allTouched)

    const invalid = session.questions.filter(q => (answers[q.id] || '').trim().length < MIN_ANSWER_LEN)
    if (invalid.length > 0) {
      setSubmitError('Please answer all questions (minimum ' + MIN_ANSWER_LEN + ' characters each).')
      return
    }

    setSubmitting(true)
    setSubmitError('')
    try {
      const payload = {
        responses: session.questions.map(q => ({
          question_id: q.id,
          answer: answers[q.id].trim(),
        })),
      }
      await sessionsApi.submitResponses(token, payload)
      setSubmitted(true)
    } catch (err) {
      setSubmitError(err.message || 'Failed to submit. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // -- Loading
  if (loading) {
    return (
      <PageShell>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, paddingTop: 80 }}>
          <Spinner />
          <p style={{ color: 'var(--color-muted)', fontSize: 14, margin: 0 }}>Loading your assessment...</p>
        </div>
      </PageShell>
    )
  }

  // -- Error states
  if (fetchError) {
    const MSGS = {
      not_found: { icon: '🔍', title: 'Assessment Not Found',  body: 'This link is invalid or has been removed. Please contact the recruiter for a new link.' },
      expired:   { icon: '⏰', title: 'Link Expired',          body: 'This assessment link has expired. Please contact the recruiter to request a new invitation.' },
      completed: { icon: '✅', title: 'Already Submitted',     body: 'You have already submitted your responses for this assessment. Thank you!' },
      error:     { icon: '⚠️', title: 'Something Went Wrong', body: 'We could not load your assessment. Please try refreshing the page.' },
    }
    const { icon, title, body } = MSGS[fetchError] ?? MSGS.error
    return (
      <PageShell>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, paddingTop: 80, textAlign: 'center', maxWidth: 440, margin: '0 auto' }}>
          <span style={{ fontSize: 52 }}>{icon}</span>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: 'var(--color-text)' }}>{title}</h1>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--color-muted)', lineHeight: 1.7 }}>{body}</p>
        </div>
      </PageShell>
    )
  }

  // -- Success
  if (submitted) {
    return (
      <PageShell>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, paddingTop: 80, textAlign: 'center', maxWidth: 480, margin: '0 auto' }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: 'rgba(52,211,153,.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 36,
          }}>
            ✓
          </div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: 'var(--color-success)' }}>Assessment Submitted!</h1>
          <p style={{ margin: 0, fontSize: 15, color: 'var(--color-text)', lineHeight: 1.7 }}>
            Thank you, <strong>{session.candidate_name}</strong>. Your responses have been recorded
            and the hiring team will be in touch soon.
          </p>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--color-muted)' }}>You may safely close this window.</p>
        </div>
      </PageShell>
    )
  }

  // -- Assessment form
  const completedCount = session.questions.filter(q => (answers[q.id] || '').trim().length >= MIN_ANSWER_LEN).length
  const totalCount     = session.questions.length
  const allDone        = completedCount === totalCount && totalCount > 0
  const progress       = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  return (
    <PageShell>
      {/* Header */}
      <header style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg,#6366f1,#a78bfa)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
          }}>🎯</div>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>Behavioral Assessment</span>
        </div>

        <Card style={{ padding: '24px 28px' }}>
          <h1 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 700, color: 'var(--color-text)' }}>
            {session.job_title}
          </h1>
          <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--color-muted)' }}>
            Candidate: <strong style={{ color: 'var(--color-text)' }}>{session.candidate_name}</strong>
          </p>

          {session.job_description && (
            <p style={{ margin: '0 0 20px', fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.65, paddingTop: 16, borderTop: '1px solid var(--color-border)' }}>
              {session.job_description}
            </p>
          )}

          <div style={{ padding: '14px 16px', borderRadius: 10, background: 'rgba(99,102,241,.08)', border: '1px solid rgba(99,102,241,.2)' }}>
            <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>
              How to answer (STAR method)
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: '4px 16px' }}>
              {STAR_STEPS.map(s => (
                <p key={s.label} style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'var(--color-text)' }}>{s.label}:</strong> {s.hint}
                </p>
              ))}
            </div>
          </div>
        </Card>
      </header>

      {/* Progress */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>Progress</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: allDone ? 'var(--color-success)' : 'var(--color-muted)' }}>
            {completedCount} / {totalCount} answered
          </span>
        </div>
        <div style={{ height: 6, borderRadius: 99, background: 'var(--color-surface-2)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 99, transition: 'width 0.35s ease',
            background: allDone ? 'var(--color-success)' : 'linear-gradient(90deg,#6366f1,#a78bfa)',
            width: progress + '%',
          }} />
        </div>
      </div>

      {/* Questions */}
      <form onSubmit={handleSubmit} noValidate>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 32 }}>
          {session.questions.map((q, idx) => {
            const answer    = answers[q.id] || ''
            const isTouched = !!touched[q.id]
            const tooShort  = answer.trim().length < MIN_ANSWER_LEN
            const showError = isTouched && tooShort
            const answered  = !tooShort
            const diffMeta  = DIFFICULTY_META[q.difficulty] || { label: q.difficulty, color: '#94a3b8', bg: 'rgba(148,163,184,.12)' }
            const typeMeta  = TYPE_META[q.type]              || { label: q.type,       color: '#94a3b8', bg: 'rgba(148,163,184,.12)' }

            return (
              <Card key={q.id} style={{
                outline: answered ? '1.5px solid rgba(52,211,153,.3)' : showError ? '1.5px solid rgba(248,113,113,.4)' : 'none',
                transition: 'outline 0.2s',
              }}>
                <div style={{ padding: '18px 22px 14px', borderBottom: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 9px', borderRadius: 99, background: 'var(--color-surface-2)', color: 'var(--color-muted)' }}>
                      Q{idx + 1}
                    </span>
                    {q.dimension_name && (
                      <Badge label={q.dimension_name.replace(/_/g, ' ')} color="#818cf8" bg="rgba(99,102,241,.15)" />
                    )}
                    <Badge label={typeMeta.label} color={typeMeta.color} bg={typeMeta.bg} />
                    <Badge label={diffMeta.label} color={diffMeta.color} bg={diffMeta.bg} />
                    {answered && (
                      <span style={{ fontSize: 11, color: 'var(--color-success)', fontWeight: 600, marginLeft: 'auto' }}>
                        Answered
                      </span>
                    )}
                  </div>

                  <p style={{ margin: 0, fontSize: 15, color: 'var(--color-text)', lineHeight: 1.65, fontWeight: 500 }}>
                    {q.question}
                  </p>

                  {q.indicators && q.indicators.length > 0 && (
                    <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                      <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>Look for:</span>
                      {q.indicators.map((ind, ii) => (
                        <span key={ii} style={{ fontSize: 11, padding: '2px 9px', borderRadius: 99, background: 'var(--color-surface-2)', color: 'var(--color-muted)', border: '1px solid var(--color-border)' }}>
                          {ind}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div style={{ padding: '16px 22px' }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--color-muted)', marginBottom: 8 }}>
                    Your answer (STAR format recommended)
                  </label>
                  <textarea
                    id={'answer-' + q.id}
                    value={answer}
                    onChange={e => setAnswer(q.id, e.target.value)}
                    onBlur={() => handleBlur(q.id)}
                    rows={6}
                    placeholder="Describe a specific situation using the STAR method..."
                    style={{
                      width: '100%', boxSizing: 'border-box',
                      background: 'var(--color-surface-2)',
                      color: 'var(--color-text)',
                      border: '1px solid ' + (showError ? 'var(--color-danger)' : answered ? 'rgba(52,211,153,.4)' : 'var(--color-border)'),
                      borderRadius: 8, padding: '10px 12px', fontSize: 14,
                      lineHeight: 1.65, resize: 'vertical', outline: 'none',
                      transition: 'border-color 0.2s', fontFamily: 'inherit',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, alignItems: 'center' }}>
                    {showError
                      ? <p style={{ margin: 0, fontSize: 12, color: 'var(--color-danger)' }}>Please provide a more detailed answer (at least {MIN_ANSWER_LEN} characters).</p>
                      : <span />
                    }
                    <span style={{ fontSize: 11, color: tooShort ? 'var(--color-muted)' : 'var(--color-success)', flexShrink: 0, marginLeft: 8 }}>
                      {answer.trim().length} chars
                    </span>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Submit */}
        <Card style={{ padding: '24px 28px' }}>
          {submitError && (
            <p style={{ margin: '0 0 16px', fontSize: 13, padding: '10px 14px', borderRadius: 8, color: 'var(--color-danger)', background: 'rgba(248,113,113,.1)' }}>
              {submitError}
            </p>
          )}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.6 }}>
              {allDone
                ? 'All questions answered. Review your responses and submit when ready.'
                : (totalCount - completedCount) + ' question' + (totalCount - completedCount !== 1 ? 's' : '') + ' remaining.'}
            </p>
            <button
              id="btn-submit-assessment"
              type="submit"
              disabled={submitting}
              style={{
                padding: '11px 28px', borderRadius: 10, border: 'none',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontSize: 14, fontWeight: 700, fontFamily: 'inherit',
                background: submitting ? 'var(--color-border)' : 'linear-gradient(135deg,#6366f1,#a78bfa)',
                color: '#fff', transition: 'opacity 0.2s', opacity: submitting ? 0.7 : 1, flexShrink: 0,
              }}
            >
              {submitting ? 'Submitting...' : 'Submit Assessment'}
            </button>
          </div>
        </Card>
      </form>

      <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--color-muted)', marginTop: 40, marginBottom: 16 }}>
        All responses are confidential and used only for this assessment.
      </p>
    </PageShell>
  )
}
