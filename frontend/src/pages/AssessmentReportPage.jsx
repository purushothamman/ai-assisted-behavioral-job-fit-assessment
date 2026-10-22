// src/pages/AssessmentReportPage.jsx
// Comprehensive candidate behavioral assessment report for recruiters.
import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { reportsApi } from '../services/api'

const DIM_META = {
  communication:     { icon: '💬', label: 'Communication',      color: '#6366f1' },
  teamwork:          { icon: '🤝', label: 'Teamwork',           color: '#22d3ee' },
  adaptability:      { icon: '🔄', label: 'Adaptability',       color: '#34d399' },
  decision_making:   { icon: '🧠', label: 'Decision Making',    color: '#fbbf24' },
  leadership:        { icon: '🎯', label: 'Leadership',         color: '#f472b6' },
  stress_management: { icon: '⚖️', label: 'Stress Management',  color: '#a78bfa' },
}

function getScoreColor(score) {
  if (score >= 75) return '#34d399'
  if (score >= 50) return '#fbbf24'
  return '#f87171'
}

export default function AssessmentReportPage() {
  const { jobId, sessionId } = useParams()
  const navigate = useNavigate()

  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedQuestions, setExpandedQuestions] = useState({})

  // Recruiter review form state (Phase D: OV-4, OV-5, OV-6)
  const [reviewAction, setReviewAction] = useState('reviewed')
  const [recruiterNotes, setRecruiterNotes] = useState('')
  const [overrideScore, setOverrideScore] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)
  const [reviewSuccessMsg, setReviewSuccessMsg] = useState('')
  const [reviewErrorMsg, setReviewErrorMsg] = useState('')

  useEffect(() => {
    if (!sessionId) return
    setLoading(true)
    reportsApi.getReport(sessionId)
      .then(res => {
        setReport(res.data)
        // Expand first two questions by default
        if (res.data?.questions_evidence) {
          const initial = {}
          res.data.questions_evidence.slice(0, 2).forEach(q => {
            initial[q.question_id] = true
          })
          setExpandedQuestions(initial)
        }
        // Sync recruiter review fields if previously reviewed
        if (res.data?.recruiter_review) {
          if (res.data.recruiter_review.review_action) {
            setReviewAction(res.data.recruiter_review.review_action)
          }
          if (res.data.recruiter_review.recruiter_notes) {
            setRecruiterNotes(res.data.recruiter_review.recruiter_notes)
          }
          if (res.data.recruiter_review.override_score !== null && res.data.recruiter_review.override_score !== undefined) {
            setOverrideScore(res.data.recruiter_review.override_score)
          }
        }
      })
      .catch(err => {
        setError(err.message || 'Failed to generate assessment report.')
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  const toggleQuestion = (qid) => {
    setExpandedQuestions(prev => ({ ...prev, [qid]: !prev[qid] }))
  }

  const handlePrint = () => {
    window.print()
  }

  const handleReviewSubmit = async (e) => {
    e.preventDefault()
    setSubmittingReview(true)
    setReviewSuccessMsg('')
    setReviewErrorMsg('')

    try {
      const payload = {
        action: reviewAction,
        notes: recruiterNotes.trim() || null,
        override_score: overrideScore !== '' && overrideScore !== null ? Number(overrideScore) : null,
      }
      const res = await reportsApi.submitReview(sessionId, payload)
      setReviewSuccessMsg('Recruiter review recorded and auditable event logged.')
      // Update local report state with review confirmation
      setReport(prev => ({
        ...prev,
        recruiter_review: {
          reviewed_at: res.data?.reviewed_at || new Date().toISOString(),
          reviewed_by: res.data?.reviewed_by,
          review_action: res.data?.review_action || reviewAction,
          recruiter_notes: res.data?.recruiter_notes || recruiterNotes,
          override_score: res.data?.override_score ?? (overrideScore !== '' ? Number(overrideScore) : null),
        }
      }))
    } catch (err) {
      setReviewErrorMsg(err.message || 'Failed to submit recruiter review.')
    } finally {
      setSubmittingReview(false)
    }
  }

  if (loading) {
    return (
      <div style={{ maxWidth: '960px', margin: '40px auto', padding: '0 24px', textAlign: 'center', color: 'var(--color-muted)' }}>
        <p style={{ fontSize: '18px', marginBottom: '8px' }}>⏳</p>
        <p style={{ fontSize: '14px' }}>Compiling candidate assessment report…</p>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div style={{ maxWidth: '960px', margin: '40px auto', padding: '0 24px' }}>
        <button
          onClick={() => navigate(`/jobs/${jobId}`)}
          style={{ background: 'none', border: 'none', color: 'var(--color-muted)', cursor: 'pointer', fontSize: '13px', marginBottom: '16px', padding: 0 }}
        >
          ← Back to Job
        </button>
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', padding: '24px', borderRadius: '12px', textAlign: 'center' }}>
          <p style={{ color: 'var(--color-danger)', fontSize: '16px', fontWeight: 600, margin: '0 0 8px' }}>
            Report Unavailable
          </p>
          <p style={{ color: 'var(--color-muted)', fontSize: '13px', margin: '0 0 16px' }}>
            {error || 'The requested assessment report could not be found.'}
          </p>
          <Link
            to={`/jobs/${jobId}`}
            style={{ display: 'inline-block', background: 'var(--color-surface-2)', color: 'var(--color-text)', padding: '8px 16px', borderRadius: '8px', textDecoration: 'none', fontSize: '13px', fontWeight: 500 }}
          >
            Return to Job Overview
          </Link>
        </div>
      </div>
    )
  }

  const {
    candidate_name,
    candidate_email,
    job_title,
    status,
    submitted_at,
    created_at,
    executive_summary,
    dimension_breakdown = [],
    questions_evidence = [],
    compliance_notice,
    generated_at,
  } = report

  const overallScore = executive_summary?.overall_alignment_score ?? 0
  const scoreColor = getScoreColor(overallScore)
  const isComplete = executive_summary?.is_complete ?? false

  return (
    <div className="report-container" style={{ maxWidth: '980px', margin: '0 auto', padding: '32px 24px 80px' }}>
      {/* Navigation bar (hidden on print) */}
      <div className="no-print" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', gap: '16px', flexWrap: 'wrap' }}>
        <button
          onClick={() => navigate(`/jobs/${jobId}`)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-muted)',
            cursor: 'pointer',
            fontSize: '13px',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>←</span> Back to Job: <strong>{job_title}</strong>
        </button>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handlePrint}
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              color: '#fff',
              border: 'none',
              padding: '8px 18px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 12px rgba(99,102,241,0.2)',
            }}
          >
            <span>🖨️</span> Print / Save PDF
          </button>
        </div>
      </div>

      {/* Report Header Card */}
      <div
        style={{
          background: 'var(--color-surface, #1e2230)',
          border: '1px solid var(--color-border, #2d3748)',
          borderRadius: '16px',
          padding: '28px',
          marginBottom: '24px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span style={{ fontSize: '24px' }}>📋</span>
              <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 800, color: 'var(--color-text, #f8fafc)' }}>
                Candidate Behavioral Assessment Report
              </h1>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '15px', color: 'var(--color-muted, #94a3b8)' }}>
              Candidate: <strong style={{ color: 'var(--color-text, #f8fafc)' }}>{candidate_name}</strong>
              {candidate_email && ` (${candidate_email})`}
            </p>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
              Role Evaluated: <strong style={{ color: 'var(--color-text, #f8fafc)' }}>{job_title}</strong>
              {submitted_at && ` · Completed: ${new Date(submitted_at).toLocaleDateString()}`}
            </p>
            {report.metadata?.framework_version && (
              <div style={{ marginTop: '8px' }}>
                <span style={{ fontSize: '11px', color: '#a5b4fc', background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)', padding: '2px 8px', borderRadius: '6px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <span>🔒</span> Framework Snapshot: {report.metadata.framework_version}
                </span>
              </div>
            )}
          </div>

          <div style={{ textAlign: 'right' }}>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                padding: '4px 12px',
                borderRadius: '99px',
                background: isComplete ? 'rgba(52,211,153,0.15)' : 'rgba(251,191,36,0.15)',
                color: isComplete ? '#34d399' : '#fbbf24',
                display: 'inline-block',
                marginBottom: '6px',
              }}
            >
              {status}
            </span>
            <p style={{ margin: 0, fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
              Report Generated: {new Date(generated_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Executive Summary Metrics */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginTop: '24px',
            paddingTop: '20px',
            borderTop: '1px solid var(--color-border, #2d3748)',
          }}
        >
          {/* Overall Alignment Score */}
          <div
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: `1px solid ${scoreColor}44`,
              borderRadius: '12px',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Overall Fit Score
              </span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '2px' }}>
                <span style={{ fontSize: '32px', fontWeight: 800, color: scoreColor }}>
                  {overallScore}
                </span>
                <span style={{ fontSize: '14px', color: 'var(--color-muted, #94a3b8)' }}>/ 100</span>
              </div>
              {report.recruiter_review?.override_score !== null && report.recruiter_review?.override_score !== undefined && (
                <div style={{ marginTop: '4px' }}>
                  <span style={{ fontSize: '11px', color: '#f59e0b', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                    Human Override: {report.recruiter_review.override_score} / 100
                  </span>
                </div>
              )}
            </div>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                border: `3px solid ${scoreColor}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                fontWeight: 800,
                color: scoreColor,
                background: `${scoreColor}15`,
              }}
            >
              {Math.round(overallScore)}%
            </div>
          </div>

          {/* Competency Requirements Assessed */}
          <div
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--color-border, #2d3748)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Competencies Assessed
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontSize: '28px', fontWeight: 800, color: 'var(--color-text, #f8fafc)' }}>
                {executive_summary?.assessed_dimensions_count ?? 0}
              </span>
              <span style={{ fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
                of {executive_summary?.total_dimensions_count ?? 0} required
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
              Total Weight: {executive_summary?.total_job_weight ?? 0} pts
            </p>
          </div>

          {/* Evaluation Confidence */}
          <div
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--color-border, #2d3748)',
              borderRadius: '12px',
              padding: '16px',
            }}
          >
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Evaluation Confidence
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontSize: '28px', fontWeight: 800, color: '#818cf8' }}>
                {Math.round((executive_summary?.average_confidence ?? 0) * 100)}%
              </span>
              <span style={{ fontSize: '11px', color: '#a5b4fc', background: 'rgba(99,102,241,0.12)', padding: '2px 8px', borderRadius: '99px', fontWeight: 600 }}>
                Deterministic
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
              Pure rubric & embedding similarity
            </p>
          </div>
        </div>
      </div>

      {/* Assessment Notices & Fairness Caveats (Phase D: OV-1) */}
      {report.warnings && report.warnings.length > 0 && (
        <div
          style={{
            background: 'rgba(251,191,36,0.06)',
            border: '1px solid rgba(251,191,36,0.3)',
            borderRadius: '16px',
            padding: '20px 24px',
            marginBottom: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <span style={{ fontSize: '18px' }}>⚠️</span>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#fbbf24' }}>
              Assessment Notices & Fairness Caveats
            </h3>
          </div>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#e2e8f0', fontSize: '13px', lineHeight: 1.6 }}>
            {report.warnings.map((w, idx) => (
              <li key={idx} style={{ marginBottom: idx === report.warnings.length - 1 ? 0 : '6px' }}>
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recruiter Oversight & Audit Trail Card (Phase D: OV-4, OV-5, OV-6) */}
      <div
        style={{
          background: 'var(--color-surface, #1e2230)',
          border: '1px solid var(--color-border, #2d3748)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '24px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '20px' }}>🛡️</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-text, #f8fafc)' }}>
                Recruiter Oversight & Review
              </h2>
              <p style={{ margin: '3px 0 0', fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
                Human review, qualitative evaluation notes, and auditable hiring decisions. Original scores are preserved.
              </p>
            </div>
          </div>
          {report.recruiter_review?.reviewed_at && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  padding: '3px 10px',
                  borderRadius: '99px',
                  background: 'rgba(99,102,241,0.18)',
                  color: '#a5b4fc',
                }}
              >
                Action: {report.recruiter_review.review_action}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                Reviewed: {new Date(report.recruiter_review.reviewed_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>

        {/* Existing Review Record if reviewed */}
        {report.recruiter_review?.reviewed_at && (
          <div
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--color-border, #2d3748)',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '12px' }}>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase' }}>Review Action</span>
                <p style={{ margin: '2px 0 0', fontSize: '13px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                  {report.recruiter_review.review_action}
                </p>
              </div>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase' }}>Reviewed By</span>
                <p style={{ margin: '2px 0 0', fontSize: '13px', fontFamily: 'monospace', color: '#94a3b8' }}>
                  {report.recruiter_review.reviewed_by ? String(report.recruiter_review.reviewed_by).slice(0, 8) + '...' : 'Recruiter'}
                </p>
              </div>
              {report.recruiter_review.override_score !== null && report.recruiter_review.override_score !== undefined && (
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase' }}>Score Override</span>
                  <p style={{ margin: '2px 0 0', fontSize: '13px', fontWeight: 700, color: '#f59e0b' }}>
                    {report.recruiter_review.override_score} / 100 <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--color-muted, #94a3b8)' }}>(Original: {overallScore})</span>
                  </p>
                </div>
              )}
            </div>
            {report.recruiter_review.recruiter_notes && (
              <div>
                <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase' }}>Recruiter Notes</span>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#e2e8f0', lineHeight: 1.5, background: 'rgba(0,0,0,0.15)', padding: '10px 12px', borderRadius: '8px', whiteSpace: 'pre-wrap' }}>
                  {report.recruiter_review.recruiter_notes}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Review Form */}
        <form onSubmit={handleReviewSubmit} className="no-print">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--color-text, #f8fafc)', marginBottom: '6px' }}>
                Oversight Review Action *
              </label>
              <select
                value={reviewAction}
                onChange={(e) => setReviewAction(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--color-border, #2d3748)',
                  background: 'var(--color-surface-2, #111827)',
                  color: 'var(--color-text, #f8fafc)',
                  fontSize: '13px',
                }}
              >
                <option value="reviewed">Standard Review Completed</option>
                <option value="flagged_for_interview">Flag for Live Behavioral Interview</option>
                <option value="request_reassessment">Request Candidate Reassessment</option>
                <option value="overridden">Override Score / Decision</option>
                <option value="completed">Candidate Review Finalized</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--color-text, #f8fafc)', marginBottom: '6px' }}>
                Score Override (Optional, 0–100)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                placeholder={`Leave blank to keep deterministic score (${overallScore})`}
                value={overrideScore}
                onChange={(e) => setOverrideScore(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--color-border, #2d3748)',
                  background: 'var(--color-surface-2, #111827)',
                  color: 'var(--color-text, #f8fafc)',
                  fontSize: '13px',
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--color-text, #f8fafc)', marginBottom: '6px' }}>
              Qualitative Recruiter Notes & Observations
            </label>
            <textarea
              rows="3"
              placeholder="Document behavioral observations, context for override, interview inquiries, or candidate feedback..."
              value={recruiterNotes}
              onChange={(e) => setRecruiterNotes(e.target.value)}
              maxLength={4000}
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1px solid var(--color-border, #2d3748)',
                background: 'var(--color-surface-2, #111827)',
                color: 'var(--color-text, #f8fafc)',
                fontSize: '13px',
                lineHeight: 1.5,
                resize: 'vertical',
              }}
            />
          </div>

          {reviewSuccessMsg && (
            <div style={{ background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.3)', borderRadius: '8px', padding: '10px 14px', marginBottom: '14px', color: '#34d399', fontSize: '13px' }}>
              ✓ {reviewSuccessMsg}
            </div>
          )}

          {reviewErrorMsg && (
            <div style={{ background: 'rgba(248,113,113,0.12)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '8px', padding: '10px 14px', marginBottom: '14px', color: '#f87171', fontSize: '13px' }}>
              ✕ {reviewErrorMsg}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="submit"
              disabled={submittingReview}
              style={{
                background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                color: '#fff',
                border: 'none',
                padding: '9px 20px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: submittingReview ? 'not-allowed' : 'pointer',
                opacity: submittingReview ? 0.7 : 1,
                boxShadow: '0 2px 8px rgba(99,102,241,0.25)',
              }}
            >
              {submittingReview ? 'Submitting Review...' : (report.recruiter_review?.reviewed_at ? 'Update Recruiter Review' : 'Save Recruiter Review')}
            </button>
          </div>
        </form>
      </div>

      {/* Side-by-Side Visual Benchmark Comparison Matrix */}
      <div
        style={{
          background: 'var(--color-surface, #1e2230)',
          border: '1px solid var(--color-border, #2d3748)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-text, #f8fafc)' }}>
              Behavioral Competency Benchmark Comparison
            </h2>
            <p style={{ margin: '3px 0 0', fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
              Candidate evaluated score versus role benchmark importance weight.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '14px', fontSize: '11px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--color-text, #f8fafc)' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#34d399' }} /> Candidate Score
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--color-muted, #94a3b8)' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'rgba(255,255,255,0.2)' }} /> Job Benchmark Weight
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gap: '12px' }}>
          {dimension_breakdown.map((dim) => {
            const meta = DIM_META[dim.dimension_name] ?? {
              icon: '•',
              label: dim.dimension_label || dim.dimension_name,
              color: '#94a3b8',
            }
            const isMissing = dim.status === 'missing'
            const dimScoreColor = isMissing ? '#f87171' : getScoreColor(dim.candidate_score)
            const gap = dim.benchmark_gap

            return (
              <div
                key={dim.dimension_name}
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--color-border, #2d3748)',
                  borderRadius: '12px',
                  padding: '16px 20px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '20px' }}>{meta.icon}</span>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                          {meta.label}
                        </span>
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            padding: '2px 8px',
                            borderRadius: '99px',
                            background: isMissing ? 'rgba(248,113,113,0.15)' : 'rgba(52,211,153,0.15)',
                            color: isMissing ? '#f87171' : '#34d399',
                          }}
                        >
                          {dim.status}
                        </span>
                      </div>
                      <span style={{ fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
                        Job Priority: <strong>{dim.job_weight} pts</strong> ({dim.weight_percentage}%)
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
                    <div>
                      <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-muted, #94a3b8)', textAlign: 'right' }}>
                        Candidate Performance
                      </span>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: dimScoreColor, display: 'block', textAlign: 'right' }}>
                        {isMissing ? 'Not Assessed' : `${dim.candidate_score} / 100`}
                      </span>
                    </div>

                    <div style={{ minWidth: '75px', textAlign: 'right', borderLeft: '1px solid var(--color-border, #2d3748)', paddingLeft: '14px' }}>
                      <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                        Contribution
                      </span>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: '#818cf8', display: 'block' }}>
                        +{dim.contribution} pts
                      </span>
                    </div>

                    {!isMissing && (
                      <div style={{ minWidth: '65px', textAlign: 'right' }}>
                        <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                          Gap
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: gap >= 0 ? '#34d399' : '#fbbf24' }}>
                          {gap >= 0 ? `+${gap}` : gap}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Comparison Bar */}
                {!isMissing ? (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ height: '8px', background: 'var(--color-surface-2, #2d3748)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
                      {/* Candidate score fill */}
                      <div
                        style={{
                          height: '100%',
                          width: `${dim.candidate_score}%`,
                          background: dimScoreColor,
                          borderRadius: '4px',
                          transition: 'width 0.4s ease',
                        }}
                      />
                      {/* Job Benchmark Marker */}
                      <div
                        title={`Job benchmark weight: ${dim.job_weight}`}
                        style={{
                          position: 'absolute',
                          top: 0,
                          bottom: 0,
                          left: `${dim.job_weight}%`,
                          width: '3px',
                          background: '#fff',
                          boxShadow: '0 0 4px rgba(0,0,0,0.8)',
                          zIndex: 2,
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <p style={{ margin: '6px 0 0', fontSize: '12px', color: '#f87171', fontStyle: 'italic' }}>
                    ⚠ This required competency was not evaluated in candidate responses. Contribution to overall score is 0.
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Strengths & Areas for Review Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Key Strengths */}
        <div
          style={{
            background: 'var(--color-surface, #1e2230)',
            border: '1px solid rgba(52,211,153,0.25)',
            borderRadius: '16px',
            padding: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span style={{ fontSize: '18px' }}>✨</span>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-text, #f8fafc)' }}>
              Demonstrated Strengths
            </h2>
          </div>
          <div style={{ display: 'grid', gap: '10px' }}>
            {executive_summary?.strengths?.map((str, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(52,211,153,0.04)',
                  border: '1px solid rgba(52,211,153,0.15)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  fontSize: '13px',
                  color: '#e2e8f0',
                  lineHeight: 1.5,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                }}
              >
                <span style={{ color: '#34d399', fontWeight: 700, marginTop: '1px' }}>✓</span>
                <span>{str}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Areas for Review */}
        <div
          style={{
            background: 'var(--color-surface, #1e2230)',
            border: '1px solid rgba(251,191,36,0.25)',
            borderRadius: '16px',
            padding: '24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <span style={{ fontSize: '18px' }}>🔍</span>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-text, #f8fafc)' }}>
              Areas for Recruiter Review
            </h2>
          </div>
          <div style={{ display: 'grid', gap: '10px' }}>
            {executive_summary?.areas_for_review?.map((area, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(251,191,36,0.04)',
                  border: '1px solid rgba(251,191,36,0.15)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  fontSize: '13px',
                  color: '#e2e8f0',
                  lineHeight: 1.5,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                }}
              >
                <span style={{ color: '#fbbf24', fontWeight: 700, marginTop: '1px' }}>•</span>
                <span>{area}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recruiter Live Interview Inquiry Prompts */}
      <div
        style={{
          background: 'var(--color-surface, #1e2230)',
          border: '1px solid rgba(99,102,241,0.25)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <span style={{ fontSize: '18px' }}>💬</span>
          <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-text, #f8fafc)' }}>
            Targeted Interview Inquiry Prompts
          </h2>
        </div>
        <p style={{ margin: '0 0 16px', fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
          Recommended conversational questions for recruiters to explore during live interviews based on the evaluated responses.
        </p>

        <div style={{ display: 'grid', gap: '10px' }}>
          {executive_summary?.inquiry_prompts?.map((prompt, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(99,102,241,0.04)',
                border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: '10px',
                padding: '12px 16px',
                fontSize: '13px',
                color: '#e2e8f0',
                lineHeight: 1.5,
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
              }}
            >
              <span style={{ color: '#818cf8', fontWeight: 700, marginTop: '1px' }}>💬</span>
              <span>{prompt}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Question-by-Question Response & Behavioral Evidence Transcript */}
      <div
        style={{
          background: 'var(--color-surface, #1e2230)',
          border: '1px solid var(--color-border, #2d3748)',
          borderRadius: '16px',
          padding: '24px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--color-text, #f8fafc)' }}>
              Interview Question & Behavioral Evidence Transcript
            </h2>
            <p style={{ margin: '3px 0 0', fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
              Candidate responses, normalized scores, detected indicators, and extracted evidence snippets.
            </p>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
            {questions_evidence.length} questions
          </span>
        </div>

        <div style={{ display: 'grid', gap: '14px' }}>
          {questions_evidence.map((q, qIdx) => {
            const isExpanded = !!expandedQuestions[q.question_id]
            const qScoreColor = q.response_score != null ? getScoreColor(q.response_score) : '#94a3b8'

            return (
              <div
                key={q.question_id}
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--color-border, #2d3748)',
                  borderRadius: '12px',
                  overflow: 'hidden',
                }}
              >
                {/* Header */}
                <div
                  onClick={() => toggleQuestion(q.question_id)}
                  style={{
                    padding: '16px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '14px',
                    cursor: 'pointer',
                    background: isExpanded ? 'rgba(255,255,255,0.02)' : 'transparent',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-primary-h, #818cf8)' }}>
                        Q{qIdx + 1}
                      </span>
                      <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '99px', background: 'rgba(99,102,241,0.12)', color: '#818cf8', fontWeight: 600 }}>
                        {q.dimension_label}
                      </span>
                      <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '99px', background: 'rgba(255,255,255,0.05)', color: 'var(--color-muted, #94a3b8)', textTransform: 'capitalize' }}>
                        {q.question_type} · {q.difficulty}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)', lineHeight: 1.4 }}>
                      {q.question_text}
                    </p>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexShrink: 0 }}>
                    {q.response_score != null ? (
                      <span
                        style={{
                          fontSize: '13px',
                          fontWeight: 700,
                          color: qScoreColor,
                          background: `${qScoreColor}15`,
                          padding: '4px 10px',
                          borderRadius: '6px',
                        }}
                      >
                        {q.response_score} / 100
                      </span>
                    ) : (
                      <span style={{ fontSize: '12px', color: 'var(--color-muted, #94a3b8)', fontStyle: 'italic' }}>
                        Unscored
                      </span>
                    )}
                    <span style={{ color: 'var(--color-muted, #94a3b8)', fontSize: '12px' }}>
                      {isExpanded ? '▲' : '▼'}
                    </span>
                  </div>
                </div>

                {/* Details */}
                {isExpanded && (
                  <div style={{ padding: '16px 20px', borderTop: '1px solid var(--color-border, #2d3748)', background: 'rgba(0,0,0,0.1)' }}>
                    {/* Response text */}
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Candidate Response ({q.word_count} words)
                        </span>
                        {q.confidence > 0 && (
                          <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                            NLP Confidence: <strong>{Math.round(q.confidence * 100)}%</strong>
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          background: 'var(--color-surface, #1e2230)',
                          border: '1px solid var(--color-border, #2d3748)',
                          borderRadius: '8px',
                          padding: '12px 16px',
                          fontSize: '13px',
                          lineHeight: 1.6,
                          color: '#e2e8f0',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {q.candidate_response || 'No response recorded.'}
                      </div>
                    </div>

                    {/* Behavioral Evidence Matches */}
                    {q.evidence && q.evidence.length > 0 && (
                      <div>
                        <span style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                          Behavioral Indicator Evidence
                        </span>
                        <div style={{ display: 'grid', gap: '8px' }}>
                          {q.evidence.map((ev, evIdx) => {
                            const levelBadge = {
                              strong:  { label: 'Strong Match (2 pts)', bg: 'rgba(52,211,153,0.15)', color: '#34d399' },
                              partial: { label: 'Partial Match (1 pt)',  bg: 'rgba(251,191,36,0.15)', color: '#fbbf24' },
                              none:    { label: 'No Evidence (0 pts)',     bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' },
                            }[ev.level] ?? { label: ev.level, bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' }

                            return (
                              <div
                                key={evIdx}
                                style={{
                                  background: 'var(--color-surface, #1e2230)',
                                  border: '1px solid var(--color-border, #2d3748)',
                                  borderRadius: '8px',
                                  padding: '10px 14px',
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
                                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                                    {ev.indicator_name}
                                  </span>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span style={{ fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                                      Similarity: {Math.round(ev.similarity * 100)}%
                                    </span>
                                    <span
                                      style={{
                                        fontSize: '11px',
                                        fontWeight: 600,
                                        padding: '2px 8px',
                                        borderRadius: '99px',
                                        background: levelBadge.bg,
                                        color: levelBadge.color,
                                      }}
                                    >
                                      {levelBadge.label}
                                    </span>
                                  </div>
                                </div>
                                {ev.evidence_text && (
                                  <p
                                    style={{
                                      margin: '6px 0 0',
                                      fontSize: '12px',
                                      color: '#cbd5e1',
                                      fontStyle: 'italic',
                                      background: 'rgba(255,255,255,0.03)',
                                      padding: '6px 10px',
                                      borderRadius: '4px',
                                      borderLeft: `2px solid ${levelBadge.color}`,
                                    }}
                                  >
                                    "{ev.evidence_text}"
                                  </p>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Compliance Disclaimer Footer */}
      <div
        style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid var(--color-border, #2d3748)',
          borderRadius: '12px',
          padding: '16px 20px',
          fontSize: '12px',
          color: 'var(--color-muted, #94a3b8)',
          lineHeight: 1.5,
        }}
      >
        <strong>Legal & Ethical Compliance Notice:</strong> {compliance_notice}
      </div>

      {/* Print Stylesheet */}
      <style>{`
        @media print {
          .no-print {
            display: none !important;
          }
          body {
            background: #fff !important;
            color: #000 !important;
          }
          .report-container {
            max-width: 100% !important;
            padding: 0 !important;
          }
        }
      `}</style>
    </div>
  )
}
