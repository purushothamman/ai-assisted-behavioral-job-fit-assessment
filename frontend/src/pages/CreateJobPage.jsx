// src/pages/CreateJobPage.jsx
// Form to create a new job listing.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { jobsApi } from '../services/api'

function Field({ id, label, required, children }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>
        {label} {required && <span style={{ color: 'var(--color-danger)' }}>*</span>}
      </label>
      {children}
    </div>
  )
}

const inputStyle = {
  background: 'var(--color-surface-2)',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
}

export default function CreateJobPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    title: '', description: '', responsibilities: '', requirements: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await jobsApi.create(form)
      navigate(`/jobs/${res.data.id}`)
    } catch (err) {
      setError(err.message || 'Failed to create job')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="mb-8">
        <button onClick={() => navigate('/jobs')} className="text-xs mb-4 cursor-pointer border-0 bg-transparent p-0"
                style={{ color: 'var(--color-muted)' }}>
          ← Back to Jobs
        </button>
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>Create New Job</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>
          Enter the job details. Groq AI will analyze it in Phase 4.
        </p>
      </div>

      <form onSubmit={handleSubmit}
            className="rounded-xl p-6 flex flex-col gap-5"
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        <Field id="title" label="Job Title" required>
          <input id="title" type="text" required value={form.title} onChange={set('title')}
                 placeholder="e.g. Senior Data Scientist"
                 className="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
                 style={inputStyle} />
        </Field>

        <Field id="description" label="Job Description" required>
          <textarea id="description" required rows={5} value={form.description} onChange={set('description')}
                    placeholder="Describe the role, team, and context…"
                    className="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-y"
                    style={inputStyle} />
        </Field>

        <Field id="responsibilities" label="Key Responsibilities">
          <textarea id="responsibilities" rows={4} value={form.responsibilities} onChange={set('responsibilities')}
                    placeholder="List the main responsibilities…"
                    className="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-y"
                    style={inputStyle} />
        </Field>

        <Field id="requirements" label="Requirements / Qualifications">
          <textarea id="requirements" rows={4} value={form.requirements} onChange={set('requirements')}
                    placeholder="Experience, skills, or qualifications required…"
                    className="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-y"
                    style={inputStyle} />
        </Field>

        {error && (
          <p className="text-xs rounded-lg px-3 py-2"
             style={{ color: 'var(--color-danger)', background: 'rgba(248,113,113,.1)' }}>
            {error}
          </p>
        )}

        <div className="flex gap-3 pt-2">
          <button type="button" onClick={() => navigate('/jobs')}
                  className="flex-1 py-2.5 rounded-lg text-sm font-medium cursor-pointer border-0"
                  style={{ background: 'var(--color-surface-2)', color: 'var(--color-muted)' }}>
            Cancel
          </button>
          <button id="create-job-submit" type="submit" disabled={loading}
                  className="flex-1 py-2.5 rounded-lg text-sm font-semibold text-white cursor-pointer border-0"
                  style={{ background: loading ? 'var(--color-border)' : 'var(--color-primary)' }}>
            {loading ? 'Creating…' : 'Create Job'}
          </button>
        </div>
      </form>
    </div>
  )
}
