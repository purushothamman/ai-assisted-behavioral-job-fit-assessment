// src/services/supabase.js
// Supabase browser client.
// Used for Auth only on the frontend.
// All data operations go through the FastAPI backend.
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL  = import.meta.env.VITE_SUPABASE_URL || 'https://dwzydxctpnspfhtzrzyz.supabase.co'
const SUPABASE_ANON = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_FDKPV6A_cTr7hTX6QI1Ofw_PgqipM0p'

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON, {
  auth: {
    persistSession: true,
    storageKey: 'sb-session',
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})
