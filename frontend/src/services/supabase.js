// src/services/supabase.js
// Supabase browser client.
// Used for Auth only on the frontend.
// All data operations go through the FastAPI backend.
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL  = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!SUPABASE_URL || !SUPABASE_ANON) {
  console.error('[supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY is not set.')
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON, {
  auth: {
    persistSession: true,
    storageKey: 'sb-session',
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})
