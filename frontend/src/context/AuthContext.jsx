// src/context/AuthContext.jsx
// Provides auth state (user, session, profile, role, isAdmin, loading) and helper methods
// (signIn, signUp, signOut) to the entire React tree.
import { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '../services/supabase'
import { authApi } from '../services/api'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [session, setSession] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchProfile = async () => {
    try {
      const res = await authApi.me()
      if (res?.data) {
        setProfile(res.data)
      }
    } catch {
      // non-fatal
    }
  }

  useEffect(() => {
    // Initial session check
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchProfile().finally(() => setLoading(false))
      } else {
        setLoading(false)
      }
    })

    // Listen for auth state changes (login / logout / token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      if (session?.user) {
        fetchProfile()
      } else {
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signIn = async (email, password) => {
    const res = await supabase.auth.signInWithPassword({ email, password })
    if (res.data?.session) {
      await fetchProfile()
    }
    return res
  }

  const signUp = (email, password) =>
    supabase.auth.signUp({ email, password, options: { data: { role: 'recruiter' } } })

  const signOut = () => {
    setProfile(null)
    return supabase.auth.signOut()
  }

  const role = profile?.role || user?.user_metadata?.role || 'recruiter'
  const isAdmin = role === 'admin'

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        profile,
        role,
        isAdmin,
        loading,
        signIn,
        signUp,
        signOut,
        refreshProfile: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

