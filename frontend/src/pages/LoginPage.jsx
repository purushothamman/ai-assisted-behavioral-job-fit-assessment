// src/pages/LoginPage.jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { supabase } from '../services/supabase'

export default function LoginPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab]       = useState('login')   // 'login' | 'register'
  const [email, setEmail]   = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (tab === 'login') {
        const { error } = await signIn(email, password)
        if (error) throw error
        navigate('/dashboard')
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { role: 'recruiter' } },
        })
        if (error) throw error
        setTab('login')
        setError('Account created! Please check your email to confirm, then log in.')
      }
    } catch (err) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4"
         style={{ background: 'var(--color-bg)' }}>
      {/* Card */}
      <div className="w-full max-w-sm rounded-2xl p-8 shadow-2xl"
           style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-lg mx-auto mb-4">JF</div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Job-Fit Assessment</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>Recruiter Portal</p>
        </div>

        {/* Tabs */}
        <div className="flex rounded-lg p-1 mb-6" style={{ background: 'var(--color-surface-2)' }}>
          {['login', 'register'].map(t => (
            <button key={t} onClick={() => { setTab(t); setError('') }}
                    className="flex-1 py-2 rounded-md text-sm font-medium transition-all cursor-pointer border-0"
                    style={{
                      background: tab === t ? 'var(--color-primary)' : 'transparent',
                      color: tab === t ? '#fff' : 'var(--color-muted)',
                    }}>
              {t === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>
              Email
            </label>
            <input id="email" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                   placeholder="you@example.com"
                   className="w-full px-3 py-2.5 rounded-lg text-sm outline-none transition-all"
                   style={{
                     background: 'var(--color-surface-2)', color: 'var(--color-text)',
                     border: '1px solid var(--color-border)',
                   }} />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-muted)' }}>
              Password
            </label>
            <input id="password" type="password" required value={password} onChange={e => setPassword(e.target.value)}
                   placeholder="••••••••"
                   className="w-full px-3 py-2.5 rounded-lg text-sm outline-none transition-all"
                   style={{
                     background: 'var(--color-surface-2)', color: 'var(--color-text)',
                     border: '1px solid var(--color-border)',
                   }} />
          </div>

          {error && (
            <p className="text-xs rounded-lg px-3 py-2"
               style={{
                 color: error.includes('created') ? 'var(--color-success)' : 'var(--color-danger)',
                 background: error.includes('created') ? 'rgba(52,211,153,.1)' : 'rgba(248,113,113,.1)',
               }}>
              {error}
            </p>
          )}

          <button id="submit-auth" type="submit" disabled={loading}
                  className="w-full py-2.5 rounded-lg font-semibold text-sm text-white transition-all cursor-pointer border-0"
                  style={{ background: loading ? 'var(--color-border)' : 'var(--color-primary)' }}>
            {loading ? 'Please wait…' : tab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p className="text-xs text-center mt-6" style={{ color: 'var(--color-muted)' }}>
          AI-assisted decision support · Not an automated hiring system
        </p>
      </div>
    </div>
  )
}
