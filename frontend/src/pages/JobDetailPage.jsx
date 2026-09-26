// src/pages/JobDetailPage.jsx
// View and edit a single job. Shows job metadata + placeholder sections
// for behavioral requirements (Phase 4) and questions (Phase 5).
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { jobsApi } from '../services/api'

const inputStyle = {
  background: 'var(--color-surface-2)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
}

const STATUS_OPTS = ['draft', 'analyzed', 'active', 'closed']

export default function JobDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [job, setJob]         = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm]       = useState({})
  const [error, setError]     = useState('')
  const [saved, setSaved]     = useState(false)

  useEffect(() => {
    jobsApi.get(id)
      .then(r => { setJob(r.data); setForm(r.data) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }))

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
      await jobsApi.delete(id)
      navigate('/jobs')
    } catch (err) {
      setError(err.message)
      setDeleting(false)
    }
  }

  if (loading) return <div className="p-10 text-center" style={{ color: 'var(--color-muted)' }}>Loading…</div>
  if (!job)    return <div className="p-10 text-center" style={{ color: 'var(--color-danger)' }}>Job not found.</div>

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      {/* Back */}
      <button onClick={() => navigate('/jobs')} className="text-xs mb-6 cursor-pointer border-0 bg-transparent p-0"
              style={{ color: 'var(--color-muted)' }}>
        ← Back to Jobs
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>{job.title}</h1>
          <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
            Created {new Date(job.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-2">
          {!editing && (
            <button onClick={() => setEditing(true)}
                    className="text-sm px-3 py-1.5 rounded-lg cursor-pointer border-0"
                    style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)' }}>
              Edit
            </button>
          )}
          <button onClick={handleDelete} disabled={deleting}
                  className="text-sm px-3 py-1.5 rounded-lg cursor-pointer border-0"
                  style={{ background: 'rgba(248,113,113,.15)', color: 'var(--color-danger)' }}>
            {deleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && <p className="text-xs mb-4 px-3 py-2 rounded-lg" style={{ color: 'var(--color-danger)', background: 'rgba(248,113,113,.1)' }}>{error}</p>}
      {saved && <p className="text-xs mb-4 px-3 py-2 rounded-lg" style={{ color: 'var(--color-success)', background: 'rgba(52,211,153,.1)' }}>Saved successfully.</p>}

      {/* Job detail card */}
      <div className="rounded-xl p-6 flex flex-col gap-5"
           style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        {editing ? (
          <>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>Title</label>
              <input value={form.title} onChange={set('title')} className="w-full px-3 py-2.5 rounded-lg text-sm outline-none" style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>Status</label>
              <select value={form.status} onChange={set('status')} className="w-full px-3 py-2.5 rounded-lg text-sm outline-none" style={inputStyle}>
                {STATUS_OPTS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>Description</label>
              <textarea rows={5} value={form.description || ''} onChange={set('description')} className="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-y" style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>Responsibilities</label>
              <textarea rows={4} value={form.responsibilities || ''} onChange={set('responsibilities')} className="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-y" style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>Requirements</label>
              <textarea rows={4} value={form.requirements || ''} onChange={set('requirements')} className="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-y" style={inputStyle} />
            </div>
            <div className="flex gap-3">
              <button onClick={() => { setEditing(false); setForm(job) }}
                      className="flex-1 py-2.5 rounded-lg text-sm cursor-pointer border-0"
                      style={{ background: 'var(--color-surface-2)', color: 'var(--color-muted)' }}>
                Cancel
              </button>
              <button onClick={handleSave} disabled={saving}
                      className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-0"
                      style={{ background: saving ? 'var(--color-border)' : 'var(--color-primary)' }}>
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </>
        ) : (
          <>
            <Section label="Description"      value={job.description} />
            <Section label="Responsibilities" value={job.responsibilities} />
            <Section label="Requirements"     value={job.requirements} />
            <div className="pt-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
              <span className="text-xs px-2.5 py-1 rounded-full capitalize"
                    style={{ background: 'rgba(99,102,241,.15)', color: 'var(--color-primary-h)' }}>
                {job.status}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Phase placeholders */}
      <PlaceholderSection title="Behavioral Requirements" phase="Phase 4" description="AI will extract behavioral requirements from this job description." />
      <PlaceholderSection title="Assessment Questions"   phase="Phase 5" description="Role-specific behavioral questions will be generated here." />
    </div>
  )
}

function Section({ label, value }) {
  if (!value) return null
  return (
    <div>
      <p className="text-xs font-medium mb-1" style={{ color: 'var(--color-muted)' }}>{label}</p>
      <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--color-text)' }}>{value}</p>
    </div>
  )
}

function PlaceholderSection({ title, phase, description }) {
  return (
    <div className="rounded-xl p-5 mt-4" style={{ background: 'var(--color-surface)', border: '1px dashed var(--color-border)' }}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(99,102,241,.15)', color: 'var(--color-primary-h)' }}>
          {phase}
        </span>
        <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>{title}</p>
      </div>
      <p className="text-xs" style={{ color: 'var(--color-muted)' }}>{description}</p>
    </div>
  )
}
