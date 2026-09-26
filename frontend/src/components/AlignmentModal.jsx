// src/components/AlignmentModal.jsx
// Displays deterministic job-candidate behavioral alignment results.
import React, { useEffect } from 'react'

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

export default function AlignmentModal({ data, onClose, onRecalculate, isCalculating }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!data) return null

  const {
    candidate_name,
    job_title,
    overall_score = 0,
    total_weight = 0,
    assessed_dimensions_count = 0,
    total_dimensions_count = 0,
    average_confidence = 0,
    dimension_alignments = [],
    strengths = [],
    areas_for_review = [],
    calculated_at,
  } = data

  const scoreColor = getScoreColor(overall_score)

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '860px',
          maxHeight: '90vh',
          backgroundColor: 'var(--color-surface, #1e2230)',
          border: '1px solid var(--color-border, #2d3748)',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.05)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--color-border, #2d3748)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255, 255, 255, 0.02)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>🎯</span>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                Job-Candidate Behavioral Alignment
              </h2>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
              Candidate: <strong style={{ color: 'var(--color-text, #f8fafc)' }}>{candidate_name || 'Candidate'}</strong>
              {job_title && ` · Role: ${job_title}`}
              {calculated_at && ` · Calculated: ${new Date(calculated_at).toLocaleDateString()}`}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {onRecalculate && (
              <button
                onClick={onRecalculate}
                disabled={isCalculating}
                style={{
                  background: 'rgba(99, 102, 241, 0.15)',
                  color: '#818cf8',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  padding: '6px 14px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: isCalculating ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {isCalculating ? '⏳ Calculating…' : '🔄 Recalculate'}
              </button>
            )}
            <button
              onClick={onClose}
              style={{
                background: 'var(--color-surface-2, #2d3748)',
                color: 'var(--color-muted, #94a3b8)',
                border: 'none',
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                fontSize: '16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Scrollable Body */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {/* Top Summary Banner */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '16px',
              marginBottom: '24px',
            }}
          >
            {/* Overall Alignment Score Card */}
            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: `1px solid ${scoreColor}44`,
                borderRadius: '12px',
                padding: '18px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Weighted Alignment Score
                </span>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '4px' }}>
                  <span style={{ fontSize: '32px', fontWeight: 800, color: scoreColor }}>
                    {overall_score}
                  </span>
                  <span style={{ fontSize: '14px', color: 'var(--color-muted, #94a3b8)' }}>/ 100</span>
                </div>
                <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                  ∑(Score × Weight) / ∑Weights
                </p>
              </div>
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '50%',
                  border: `3px solid ${scoreColor}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '15px',
                  fontWeight: 800,
                  color: scoreColor,
                  background: `${scoreColor}15`,
                }}
              >
                {Math.round(overall_score)}%
              </div>
            </div>

            {/* Dimensions Evaluated */}
            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--color-border, #2d3748)',
                borderRadius: '12px',
                padding: '18px 20px',
              }}
            >
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Requirements Assessed
              </span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
                <span style={{ fontSize: '30px', fontWeight: 800, color: 'var(--color-text, #f8fafc)' }}>
                  {assessed_dimensions_count}
                </span>
                <span style={{ fontSize: '14px', color: 'var(--color-muted, #94a3b8)' }}>
                  of {total_dimensions_count} required dimensions
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                Total Job Weight: <strong>{total_weight} pts</strong>
              </p>
            </div>

            {/* Assessment Confidence */}
            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--color-border, #2d3748)',
                borderRadius: '12px',
                padding: '18px 20px',
              }}
            >
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Evaluation Confidence
              </span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
                <span style={{ fontSize: '30px', fontWeight: 800, color: '#818cf8' }}>
                  {Math.round(average_confidence * 100)}%
                </span>
                <span style={{ fontSize: '12px', color: '#a5b4fc', background: 'rgba(99,102,241,0.12)', padding: '2px 8px', borderRadius: '99px', fontWeight: 600 }}>
                  Deterministic
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                Direct rubric calculation
              </p>
            </div>
          </div>

          {/* Dimension-Level Alignment Table */}
          <div style={{ marginBottom: '28px' }}>
            <h3 style={{ margin: '0 0 14px', fontSize: '15px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
              Dimension Alignment Breakdown
            </h3>

            <div style={{ display: 'grid', gap: '12px' }}>
              {dimension_alignments.map((dim) => {
                const meta = DIM_META[dim.dimension_name] ?? {
                  icon: '•',
                  label: dim.dimension_label || dim.dimension_name,
                  color: '#94a3b8',
                }
                const scoreClr = getScoreColor(dim.candidate_score)
                const isMissing = dim.status === 'missing'

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
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '10px' }}>
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
                                letterSpacing: '0.4px',
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
                            Job Weight: <strong>{dim.job_weight}</strong> ({dim.weight_percentage}% priority)
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                        <div>
                          <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-muted, #94a3b8)', textAlign: 'right' }}>
                            Candidate Score
                          </span>
                          <span style={{ fontSize: '14px', fontWeight: 700, color: isMissing ? '#f87171' : scoreClr, display: 'block', textAlign: 'right' }}>
                            {isMissing ? 'Not Assessed' : `${dim.candidate_score} / 100`}
                          </span>
                        </div>

                        <div style={{ minWidth: '90px', textAlign: 'right', borderLeft: '1px solid var(--color-border, #2d3748)', paddingLeft: '14px' }}>
                          <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-muted, #94a3b8)' }}>
                            Contribution
                          </span>
                          <span style={{ fontSize: '14px', fontWeight: 700, color: '#818cf8', display: 'block' }}>
                            +{dim.contribution} pts
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Comparative Visual Bars */}
                    {!isMissing ? (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-muted, #94a3b8)', marginBottom: '4px' }}>
                          <span>Candidate Evaluated: <strong>{dim.candidate_score}%</strong></span>
                          <span>Job Benchmark Weight: <strong>{dim.job_weight}</strong></span>
                        </div>
                        <div style={{ height: '6px', background: 'var(--color-surface-2, #2d3748)', borderRadius: '3px', overflow: 'hidden', display: 'flex' }}>
                          <div
                            style={{
                              height: '100%',
                              width: `${dim.candidate_score}%`,
                              background: scoreClr,
                              borderRadius: '3px',
                              transition: 'width 0.4s ease',
                            }}
                          />
                        </div>
                      </div>
                    ) : (
                      <p style={{ margin: 0, fontSize: '12px', color: '#f87171', fontStyle: 'italic' }}>
                        ⚠ No questions evaluated for this required competency. Contribution is 0 pts.
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Key Strengths Section */}
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>✨</span> Key Behavioral Strengths
            </h3>
            <div style={{ display: 'grid', gap: '8px' }}>
              {strengths.map((str, i) => (
                <div
                  key={i}
                  style={{
                    background: 'rgba(52, 211, 153, 0.05)',
                    border: '1px solid rgba(52, 211, 153, 0.2)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    fontSize: '13px',
                    color: '#e2e8f0',
                    lineHeight: 1.5,
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                  }}
                >
                  <span style={{ color: '#34d399', fontSize: '14px', marginTop: '1px' }}>✓</span>
                  <span>{str}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Areas for Recruiter Review Section */}
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>🔍</span> Areas for Recruiter Review
            </h3>
            <div style={{ display: 'grid', gap: '8px' }}>
              {areas_for_review.map((area, i) => (
                <div
                  key={i}
                  style={{
                    background: 'rgba(251, 191, 36, 0.05)',
                    border: '1px solid rgba(251, 191, 36, 0.2)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    fontSize: '13px',
                    color: '#e2e8f0',
                    lineHeight: 1.5,
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                  }}
                >
                  <span style={{ color: '#fbbf24', fontSize: '14px', marginTop: '1px' }}>•</span>
                  <span>{area}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Compliance & Decision-Support Notice */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--color-border, #2d3748)',
              fontSize: '12px',
              color: 'var(--color-muted, #94a3b8)',
              lineHeight: 1.5,
            }}
          >
            <strong>Note for Recruiters:</strong> This evaluation is generated via deterministic weighted scoring of candidate behavioral responses against recruiter-defined job requirements. Antigravity does not generate automated hiring or rejection recommendations; all employment decisions remain with the recruiting team.
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--color-border, #2d3748)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255, 255, 255, 0.02)',
          }}
        >
          <span style={{ fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
            Deterministic weighted alignment · Phase 7
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'var(--color-surface-2, #2d3748)',
              color: 'var(--color-text, #f8fafc)',
              border: 'none',
              padding: '8px 20px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
