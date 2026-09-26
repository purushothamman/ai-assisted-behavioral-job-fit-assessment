// src/pages/DimensionsPage.jsx
// Displays all 6 behavioral dimensions and their observable indicators.
// Recruiters use this to understand the assessment framework before creating jobs.

import { useEffect, useState } from 'react'
import { dimensionsApi } from '../services/api'

// Color palette: one accent color per dimension (cycles if more than 6)
const DIM_COLORS = [
  { ring: '#6366f1', bg: 'rgba(99,102,241,0.08)',  icon: '💬' }, // communication
  { ring: '#22d3ee', bg: 'rgba(34,211,238,0.08)',  icon: '🤝' }, // teamwork
  { ring: '#34d399', bg: 'rgba(52,211,153,0.08)',  icon: '🔄' }, // adaptability
  { ring: '#fbbf24', bg: 'rgba(251,191,36,0.08)',  icon: '🧠' }, // decision_making
  { ring: '#f472b6', bg: 'rgba(244,114,182,0.08)', icon: '🎯' }, // leadership
  { ring: '#a78bfa', bg: 'rgba(167,139,250,0.08)', icon: '⚖️' }, // stress_management
]

const LABEL_MAP = {
  communication:     'Communication',
  teamwork:          'Teamwork',
  adaptability:      'Adaptability',
  decision_making:   'Decision Making',
  leadership:        'Leadership',
  stress_management: 'Stress Management',
}

export default function DimensionsPage() {
  const [dimensions, setDimensions] = useState([])
  const [selected, setSelected]     = useState(null)   // full detail with indicators
  const [loading, setLoading]       = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError]           = useState(null)

  // Load dimension list on mount
  useEffect(() => {
    dimensionsApi.list()
      .then(res => setDimensions(res.data ?? []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  // Load detail when user clicks a card
  const handleSelect = async (dim) => {
    if (selected?.id === dim.id) { setSelected(null); return }
    setDetailLoading(true)
    try {
      const res = await dimensionsApi.get(dim.id)
      setSelected(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setDetailLoading(false)
    }
  }

  // ── Render helpers ────────────────────────────────────────────────────────

  if (loading) return (
    <div style={styles.center}>
      <div style={styles.spinner} />
      <p style={{ color: 'var(--color-muted)', marginTop: 12 }}>Loading dimensions…</p>
    </div>
  )

  if (error) return (
    <div style={styles.center}>
      <p style={{ color: 'var(--color-danger)' }}>Error: {error}</p>
    </div>
  )

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.h1}>Behavioral Framework</h1>
        <p style={styles.subtitle}>
          The six dimensions used to assess candidate suitability.
          Click a dimension to explore its observable indicators.
        </p>
      </div>

      {/* Grid of dimension cards */}
      <div style={styles.grid}>
        {dimensions.map((dim, i) => {
          const palette  = DIM_COLORS[i % DIM_COLORS.length]
          const label    = LABEL_MAP[dim.name] ?? dim.name
          const isOpen   = selected?.id === dim.id

          return (
            <div key={dim.id}>
              {/* Card */}
              <button
                id={`dim-card-${dim.name}`}
                onClick={() => handleSelect(dim)}
                style={{
                  ...styles.card,
                  background: isOpen ? palette.bg : 'var(--color-surface)',
                  borderColor: isOpen ? palette.ring : 'var(--color-border)',
                  boxShadow: isOpen ? `0 0 0 1px ${palette.ring}` : 'none',
                  width: '100%',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => {
                  if (!isOpen) {
                    e.currentTarget.style.borderColor = palette.ring
                    e.currentTarget.style.background  = palette.bg
                  }
                }}
                onMouseLeave={e => {
                  if (!isOpen) {
                    e.currentTarget.style.borderColor = 'var(--color-border)'
                    e.currentTarget.style.background  = 'var(--color-surface)'
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 28 }}>{palette.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--color-text)' }}>
                      {label}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 2 }}>
                      {dim.description}
                    </div>
                  </div>
                  <div style={{ marginLeft: 'auto', fontSize: 18, color: 'var(--color-muted)' }}>
                    {isOpen ? '▲' : '▼'}
                  </div>
                </div>
              </button>

              {/* Expanded indicator panel */}
              {isOpen && (
                <div
                  id={`dim-detail-${dim.name}`}
                  style={{
                    ...styles.detailPanel,
                    borderColor: palette.ring,
                    borderTopColor: 'transparent',
                  }}
                >
                  {detailLoading ? (
                    <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>Loading indicators…</p>
                  ) : selected?.indicators?.length > 0 ? (
                    <>
                      <p style={styles.indicatorHeading}>Observable Indicators</p>
                      <div style={styles.indicatorGrid}>
                        {selected.indicators.map(ind => (
                          <div key={ind.id} style={styles.indicatorChip}>
                            <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-text)' }}>
                              {ind.name.replace(/_/g, ' ')}
                            </div>
                            {ind.description && (
                              <div style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 3 }}>
                                {ind.description}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>No indicators found.</p>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Footer note */}
      <div style={styles.footerNote}>
        <span style={{ marginRight: 6 }}>ℹ️</span>
        These dimensions are seeded from the system's behavioral library and are
        used throughout the assessment pipeline — from job analysis to candidate scoring.
      </div>
    </div>
  )
}

// ── Inline styles ─────────────────────────────────────────────────────────────
const styles = {
  page: {
    maxWidth: 860,
    margin: '0 auto',
    padding: '40px 24px 80px',
  },
  header: {
    marginBottom: 36,
  },
  h1: {
    margin: 0,
    fontSize: 28,
    fontWeight: 700,
    color: 'var(--color-text)',
    letterSpacing: '-0.5px',
  },
  subtitle: {
    marginTop: 8,
    fontSize: 14,
    color: 'var(--color-muted)',
    lineHeight: 1.6,
  },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  card: {
    padding: '18px 20px',
    borderRadius: 12,
    border: '1px solid var(--color-border)',
    outline: 'none',
  },
  detailPanel: {
    background: 'var(--color-surface)',
    border: '1px solid',
    borderTop: 'none',
    borderRadius: '0 0 12px 12px',
    padding: '20px 24px',
    marginTop: -2,
    animation: 'fadeIn 0.15s ease',
  },
  indicatorHeading: {
    margin: '0 0 14px',
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'var(--color-muted)',
  },
  indicatorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 10,
  },
  indicatorChip: {
    padding: '12px 14px',
    borderRadius: 8,
    background: 'var(--color-surface-2)',
    border: '1px solid var(--color-border)',
  },
  center: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '40vh',
  },
  spinner: {
    width: 32,
    height: 32,
    border: '3px solid var(--color-border)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  footerNote: {
    marginTop: 48,
    padding: '14px 18px',
    borderRadius: 10,
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    fontSize: 13,
    color: 'var(--color-muted)',
    lineHeight: 1.5,
  },
}
