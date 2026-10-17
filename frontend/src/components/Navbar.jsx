// src/components/Navbar.jsx
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'

export default function Navbar() {
  const { user, signOut, isAdmin, role } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/login')
  }

  return (
    <nav style={{ background: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)' }}
         className="px-6 py-4 flex items-center justify-between sticky top-0 z-50 backdrop-blur-sm">
      {/* Logo */}
      <Link to="/dashboard" className="flex items-center gap-2 no-underline">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">JF</div>
        <span className="font-semibold text-sm" style={{ color: 'var(--color-text)' }}>
          Job-Fit Assessment
        </span>
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-5">
        {user && (
          <>
            <Link to="/dashboard" className="text-sm transition-colors"
                  style={{ color: 'var(--color-muted)' }}
                  onMouseEnter={e => e.target.style.color = 'var(--color-text)'}
                  onMouseLeave={e => e.target.style.color = 'var(--color-muted)'}>
              Dashboard
            </Link>
            <Link to="/dimensions" className="text-sm transition-colors"
                  style={{ color: 'var(--color-muted)' }}
                  onMouseEnter={e => e.target.style.color = 'var(--color-text)'}
                  onMouseLeave={e => e.target.style.color = 'var(--color-muted)'}>
              Dimensions
            </Link>
            <Link to="/jobs" className="text-sm transition-colors"
                  style={{ color: 'var(--color-muted)' }}
                  onMouseEnter={e => e.target.style.color = 'var(--color-text)'}
                  onMouseLeave={e => e.target.style.color = 'var(--color-muted)'}>
              Jobs
            </Link>

            {/* Admin Framework Manager link — authorized administrators only */}
            {isAdmin && (
              <Link
                to="/admin/framework"
                id="nav-admin-framework"
                className="text-xs transition-all flex items-center gap-1.5 px-3 py-1.5 rounded-lg no-underline font-medium hover:scale-105"
                style={{
                  background: 'rgba(236, 72, 153, 0.12)',
                  color: '#f472b6',
                  border: '1px solid rgba(236, 72, 153, 0.3)',
                }}
              >
                <span>⚙️</span>
                <span>Framework Manager</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-pink-500/20 text-pink-300">
                  Admin
                </span>
              </Link>
            )}

            <div className="flex items-center gap-3 pl-2 border-l border-slate-700">
              <span className="text-xs px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold"
                    style={{
                      background: isAdmin ? 'rgba(236, 72, 153, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                      color: isAdmin ? '#f472b6' : '#818cf8',
                      border: `1px solid ${isAdmin ? 'rgba(236, 72, 153, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`,
                    }}>
                {role}
              </span>
              <button onClick={handleSignOut}
                      className="text-xs px-3 py-1.5 rounded-lg transition-colors cursor-pointer border-0 font-medium"
                      style={{ background: 'var(--color-surface-2)', color: 'var(--color-muted)' }}
                      onMouseEnter={e => { e.target.style.background = 'var(--color-border)'; e.target.style.color = 'var(--color-text)' }}
                      onMouseLeave={e => { e.target.style.background = 'var(--color-surface-2)'; e.target.style.color = 'var(--color-muted)' }}>
                Sign out
              </button>
            </div>
          </>
        )}
      </div>
    </nav>
  )
}
