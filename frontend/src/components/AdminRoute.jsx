// src/components/AdminRoute.jsx
// Protects routes that strictly require platform administrator privileges.
// Recruiters and unauthenticated users cannot access.
import { Navigate, Link } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

export default function AdminRoute({ children }) {
  const { user, isAdmin, role, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm mt-3" style={{ color: 'var(--color-muted)' }}>
          Verifying administrator permissions…
        </p>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!isAdmin) {
    return (
      <div className="max-w-xl mx-auto mt-20 p-8 rounded-2xl border text-center"
           style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-3xl">
          🛡️
        </div>
        <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>
          Administrator Privileges Required
        </h2>
        <p className="text-sm mb-6 leading-relaxed" style={{ color: 'var(--color-muted)' }}>
          Your current account role is <span className="font-semibold text-indigo-400 capitalize">{role}</span>.
          Only authorized platform administrators can manage the behavioral framework, edit global competencies, or publish framework versions.
        </p>
        <div className="flex justify-center gap-3">
          <Link
            to="/dashboard"
            className="px-4 py-2 rounded-lg text-sm font-semibold transition-all no-underline text-white"
            style={{ background: 'var(--color-primary)' }}
          >
            Return to Dashboard
          </Link>
          <Link
            to="/dimensions"
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all no-underline"
            style={{ background: 'var(--color-surface-2)', color: 'var(--color-text)' }}
          >
            View Active Dimensions
          </Link>
        </div>
      </div>
    )
  }

  return children
}
