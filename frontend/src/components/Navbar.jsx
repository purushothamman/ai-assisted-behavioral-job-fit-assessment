// src/components/Navbar.jsx
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, signOut } = useAuth()
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
      <div className="flex items-center gap-6">
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
            <button onClick={handleSignOut}
                    className="text-sm px-3 py-1.5 rounded-lg transition-colors cursor-pointer border-0"
                    style={{ background: 'var(--color-surface-2)', color: 'var(--color-muted)' }}
                    onMouseEnter={e => { e.target.style.background = 'var(--color-border)'; e.target.style.color = 'var(--color-text)' }}
                    onMouseLeave={e => { e.target.style.background = 'var(--color-surface-2)'; e.target.style.color = 'var(--color-muted)' }}>
              Sign out
            </button>
          </>
        )}
      </div>
    </nav>
  )
}
