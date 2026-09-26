// src/pages/JobsPage.jsx
// Lists all jobs and provides navigation to create/view individual jobs.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { jobsApi } from '../services/api'

const STATUS_COLORS = {
  draft:    { bg: 'rgba(148,163,184,.12)', text: 'var(--color-muted)' },
  analyzed: { bg: 'rgba(34,211,238,.12)',  text: 'var(--color-accent)' },
  active:   { bg: 'rgba(52,211,153,.12)',  text: 'var(--color-success)' },
  closed:   { bg: 'rgba(248,113,113,.12)', text: 'var(--color-danger)' },
}

export default function JobsPage() {
  const [jobs, setJobs]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState('')

  useEffect(() => {
    jobsApi.list()
      .then(r => setJobs(r?.data ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>Jobs</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
            {jobs.length} job{jobs.length !== 1 ? 's' : ''} in your workspace
          </p>
        </div>
        <Link to="/jobs/new"
              className="text-sm px-4 py-2 rounded-lg font-medium no-underline"
              style={{ background: 'var(--color-primary)', color: '#fff' }}>
          + New Job
        </Link>
      </div>

      {loading && <p style={{ color: 'var(--color-muted)' }} className="text-sm">Loading…</p>}
      {error   && <p style={{ color: 'var(--color-danger)' }} className="text-sm">{error}</p>}

      {!loading && jobs.length === 0 && (
        <div className="rounded-xl p-12 text-center" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <p style={{ color: 'var(--color-muted)' }} className="text-sm">
            No jobs yet. Create your first job listing to begin an assessment.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {jobs.map(job => {
          const sc = STATUS_COLORS[job.status] || STATUS_COLORS.draft
          return (
            <Link key={job.id} to={`/jobs/${job.id}`}
                  className="block rounded-xl p-5 no-underline transition-all"
                  style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-border)'}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-semibold text-sm mb-1" style={{ color: 'var(--color-text)' }}>{job.title}</p>
                  <p className="text-xs" style={{ color: 'var(--color-muted)' }}>
                    Created {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-xs px-2.5 py-1 rounded-full capitalize shrink-0"
                      style={{ background: sc.bg, color: sc.text }}>
                  {job.status}
                </span>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
