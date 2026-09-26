// src/pages/DashboardPage.jsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { jobsApi } from '../services/api'

function StatCard({ label, value, color }) {
  return (
    <div className="rounded-xl p-5" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
      <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-muted)' }}>{label}</p>
      <p className="text-3xl font-bold" style={{ color }}>{value}</p>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [jobs, setJobs]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState('')

  useEffect(() => {
    jobsApi.list()
      .then(r => setJobs(r?.data ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const stats = {
    total:    jobs.length,
    active:   jobs.filter(j => j.status === 'active').length,
    analyzed: jobs.filter(j => j.status === 'analyzed').length,
    draft:    jobs.filter(j => j.status === 'draft').length,
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      {/* Greeting */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
          Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Here's an overview of your job assessments.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        <StatCard label="Total Jobs"  value={stats.total}    color="var(--color-text)" />
        <StatCard label="Active"      value={stats.active}   color="var(--color-success)" />
        <StatCard label="Analyzed"    value={stats.analyzed} color="var(--color-accent)" />
        <StatCard label="Draft"       value={stats.draft}    color="var(--color-muted)" />
      </div>

      {/* Recent jobs */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold" style={{ color: 'var(--color-text)' }}>Recent Jobs</h2>
        <Link to="/jobs/new"
              className="text-xs px-3 py-1.5 rounded-lg font-medium no-underline transition-colors"
              style={{ background: 'var(--color-primary)', color: '#fff' }}>
          + New Job
        </Link>
      </div>

      {loading && <p style={{ color: 'var(--color-muted)' }} className="text-sm">Loading…</p>}
      {error   && <p style={{ color: 'var(--color-danger)' }} className="text-sm">{error}</p>}

      {!loading && jobs.length === 0 && (
        <div className="rounded-xl p-10 text-center" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <p style={{ color: 'var(--color-muted)' }} className="text-sm mb-4">No jobs yet. Create your first job to get started.</p>
          <Link to="/jobs/new" className="text-sm px-4 py-2 rounded-lg font-medium no-underline"
                style={{ background: 'var(--color-primary)', color: '#fff' }}>
            Create Job
          </Link>
        </div>
      )}

      {!loading && jobs.slice(0, 5).map(job => (
        <Link key={job.id} to={`/jobs/${job.id}`}
              className="block rounded-xl p-4 mb-3 no-underline transition-all"
              style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-border)'}>
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm" style={{ color: 'var(--color-text)' }}>{job.title}</span>
            <span className="text-xs px-2 py-0.5 rounded-full capitalize"
                  style={{
                    background: job.status === 'active' ? 'rgba(52,211,153,.15)' : 'rgba(99,102,241,.15)',
                    color: job.status === 'active' ? 'var(--color-success)' : 'var(--color-primary-h)',
                  }}>
              {job.status}
            </span>
          </div>
          <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
            {new Date(job.created_at).toLocaleDateString()}
          </p>
        </Link>
      ))}
    </div>
  )
}
