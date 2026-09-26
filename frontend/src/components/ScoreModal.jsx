// src/components/ScoreModal.jsx
// Displays detailed NLP behavioral scoring results for a candidate session.
import React, { useState } from 'react'

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

export default function ScoreModal({ data, onClose, onRescore, isRescoring }) {
  const [expandedId, setExpandedId] = useState(null)

  if (!data) return null

  const {
    candidate_name,
    job_title,
    average_score,
    total_responses,
    scored_responses,
    scores = [],
    scored_at,
  } = data

  const avgConfidence = scores.length > 0
    ? Math.round(
        (scores.reduce((acc, s) => acc + (s.confidence ?? 0), 0) / scores.length) * 100
      )
    : 0

  const scoreColor = getScoreColor(average_score)

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
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '820px',
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
              <span style={{ fontSize: '18px' }}>📊</span>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                Candidate Assessment Results
              </h2>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
              <strong style={{ color: 'var(--color-text, #f8fafc)' }}>{candidate_name || 'Candidate'}</strong>
              {job_title && ` · ${job_title}`}
              {scored_at && ` · Scored on ${new Date(scored_at).toLocaleDateString()}`}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {onRescore && (
              <button
                onClick={onRescore}
                disabled={isRescoring}
                style={{
                  background: 'rgba(99, 102, 241, 0.15)',
                  color: '#818cf8',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  padding: '6px 12px',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: isRescoring ? 'not-allowed' : 'pointer',
                }}
              >
                {isRescoring ? '⏳ Re-scoring…' : '🔄 Re-Score'}
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
          {scores.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <span style={{ fontSize: '42px', display: 'block', marginBottom: '12px' }}>⚡</span>
              <h3 style={{ margin: '0 0 6px', fontSize: '16px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                No Scores Generated Yet
              </h3>
              <p style={{ margin: '0 0 16px', fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
                Click "Run Scoring" to evaluate candidate responses against behavioral indicators.
              </p>
              {onRescore && (
                <button
                  onClick={onRescore}
                  disabled={isRescoring}
                  style={{
                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 20px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: isRescoring ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isRescoring ? 'Running Scoring…' : '⚡ Run Scoring Now'}
                </button>
              )}
            </div>
          ) : (
            <>
              {/* Summary Stats Cards */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '16px',
                  marginBottom: '24px',
                }}
              >
                {/* Overall Score */}
                <div
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--color-border, #2d3748)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Overall Fit Score
                    </span>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '4px' }}>
                      <span style={{ fontSize: '28px', fontWeight: 800, color: scoreColor }}>
                        {average_score}
                      </span>
                      <span style={{ fontSize: '14px', color: 'var(--color-muted, #94a3b8)' }}>/ 100</span>
                    </div>
                  </div>
                  <div
                    style={{
                      width: '46px',
                      height: '46px',
                      borderRadius: '50%',
                      border: `3px solid ${scoreColor}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '14px',
                      fontWeight: 700,
                      color: scoreColor,
                      background: `${scoreColor}15`,
                    }}
                  >
                    {Math.round(average_score)}%
                  </div>
                </div>

                {/* Scored Responses */}
                <div
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--color-border, #2d3748)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                  }}
                >
                  <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Questions Analyzed
                  </span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
                    <span style={{ fontSize: '28px', fontWeight: 800, color: 'var(--color-text, #f8fafc)' }}>
                      {scored_responses}
                    </span>
                    <span style={{ fontSize: '14px', color: 'var(--color-muted, #94a3b8)' }}>
                      of {total_responses} responses
                    </span>
                  </div>
                </div>

                {/* NLP Confidence */}
                <div
                  style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--color-border, #2d3748)',
                    borderRadius: '12px',
                    padding: '16px 20px',
                  }}
                >
                  <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-muted, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Analysis Confidence
                  </span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
                    <span style={{ fontSize: '28px', fontWeight: 800, color: '#818cf8' }}>
                      {avgConfidence}%
                    </span>
                    <span style={{ fontSize: '12px', color: '#a5b4fc', background: 'rgba(99,102,241,0.12)', padding: '2px 8px', borderRadius: '99px', fontWeight: 600 }}>
                      High Accuracy
                    </span>
                  </div>
                </div>
              </div>

              {/* Dimension Scores Breakdown */}
              <div style={{ marginBottom: '24px' }}>
                <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                  Dimension Breakdown
                </h4>
                <div style={{ display: 'grid', gap: '10px' }}>
                  {scores.map(s => {
                    const meta = DIM_META[s.dimension_name] ?? {
                      icon: '•',
                      label: s.dimension_name.replace(/_/g, ' '),
                      color: '#94a3b8',
                    }
                    const dimScoreColor = getScoreColor(s.normalized_score)
                    return (
                      <div
                        key={s.id}
                        style={{
                          background: 'rgba(255,255,255,0.02)',
                          border: '1px solid var(--color-border, #2d3748)',
                          borderRadius: '10px',
                          padding: '12px 16px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '14px',
                        }}
                      >
                        <span style={{ fontSize: '20px' }}>{meta.icon}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                              {meta.label}
                            </span>
                            <span style={{ fontSize: '13px', fontWeight: 700, color: dimScoreColor }}>
                              {s.normalized_score} / 100
                            </span>
                          </div>
                          <div style={{ height: '6px', background: 'var(--color-surface-2, #2d3748)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${s.normalized_score}%`,
                                background: dimScoreColor,
                                borderRadius: '3px',
                                transition: 'width 0.5s ease',
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Detailed Evidence Cards */}
              <div>
                <h4 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                  Behavioral Evidence & Rubric Details
                </h4>

                <div style={{ display: 'grid', gap: '12px' }}>
                  {scores.map((score, idx) => {
                    const isExpanded = expandedId === score.id || (expandedId === null && idx === 0)
                    const meta = DIM_META[score.dimension_name] ?? {
                      icon: '•',
                      label: score.dimension_name.replace(/_/g, ' '),
                      color: '#94a3b8',
                    }
                    const dimScoreColor = getScoreColor(score.normalized_score)

                    return (
                      <div
                        key={score.id}
                        style={{
                          background: 'rgba(255,255,255,0.02)',
                          border: '1px solid var(--color-border, #2d3748)',
                          borderRadius: '12px',
                          overflow: 'hidden',
                        }}
                      >
                        {/* Header bar */}
                        <div
                          onClick={() => setExpandedId(isExpanded ? '__none__' : score.id)}
                          style={{
                            padding: '14px 18px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            cursor: 'pointer',
                            background: isExpanded ? 'rgba(255,255,255,0.02)' : 'transparent',
                            gap: '12px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                            <span style={{ fontSize: '18px' }}>{meta.icon}</span>
                            <div>
                              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                                {meta.label}
                              </span>
                              <span
                                style={{
                                  marginLeft: '8px',
                                  fontSize: '11px',
                                  padding: '2px 8px',
                                  borderRadius: '99px',
                                  background: score.status === 'scored' ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.12)',
                                  color: score.status === 'scored' ? '#34d399' : '#f87171',
                                  fontWeight: 600,
                                }}
                              >
                                {score.status}
                              </span>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
                            <span style={{ fontSize: '12px', color: 'var(--color-muted, #94a3b8)' }}>
                              Confidence: <strong>{Math.round(score.confidence * 100)}%</strong>
                            </span>
                            <span
                              style={{
                                fontSize: '13px',
                                fontWeight: 700,
                                color: dimScoreColor,
                                padding: '4px 10px',
                                borderRadius: '6px',
                                background: `${dimScoreColor}15`,
                              }}
                            >
                              {score.normalized_score} / 100
                            </span>
                            <span style={{ color: 'var(--color-muted, #94a3b8)', fontSize: '12px' }}>
                              {isExpanded ? '▲' : '▼'}
                            </span>
                          </div>
                        </div>

                        {/* Expanded details */}
                        {isExpanded && (
                          <div style={{ padding: '16px 18px', borderTop: '1px solid var(--color-border, #2d3748)', background: 'rgba(0,0,0,0.15)' }}>
                            {/* Indicators & Evidence */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                              {score.evidence && score.evidence.length > 0 ? (
                                score.evidence.map((ev, ei) => {
                                  const levelBadge = {
                                    strong:  { label: 'Strong Evidence (2 pts)', bg: 'rgba(52,211,153,0.15)', color: '#34d399' },
                                    partial: { label: 'Partial Evidence (1 pt)',  bg: 'rgba(251,191,36,0.15)', color: '#fbbf24' },
                                    none:    { label: 'No Evidence (0 pts)',     bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' },
                                  }[ev.level] ?? { label: ev.level, bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' }

                                  return (
                                    <div
                                      key={ei}
                                      style={{
                                        background: 'var(--color-surface, #1e2230)',
                                        border: '1px solid var(--color-border, #2d3748)',
                                        borderRadius: '8px',
                                        padding: '12px 14px',
                                      }}
                                    >
                                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '6px' }}>
                                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text, #f8fafc)' }}>
                                          {ev.indicator}
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

                                      {ev.evidence_text ? (
                                        <div
                                          style={{
                                            fontSize: '12px',
                                            lineHeight: 1.5,
                                            color: '#cbd5e1',
                                            background: 'rgba(255,255,255,0.03)',
                                            padding: '8px 12px',
                                            borderRadius: '6px',
                                            borderLeft: `3px solid ${levelBadge.color}`,
                                            marginTop: '6px',
                                          }}
                                        >
                                          "{ev.evidence_text}"
                                        </div>
                                      ) : (
                                        <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--color-muted, #94a3b8)', fontStyle: 'italic' }}>
                                          No clear textual evidence extracted for this indicator.
                                        </p>
                                      )}
                                    </div>
                                  )
                                })
                              ) : (
                                <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-muted, #94a3b8)' }}>
                                  No indicator details recorded.
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}
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
            Evaluated via deterministic NLP rubrics & semantic embeddings.
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'var(--color-surface-2, #2d3748)',
              color: 'var(--color-text, #f8fafc)',
              border: 'none',
              padding: '8px 18px',
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
