import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim()
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim()

export const supabaseClient =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null

export async function getAccessToken(): Promise<string | null> {
  if (!supabaseClient) return null
  const { data, error } = await supabaseClient.auth.getSession()
  if (error) throw error
  return data.session?.access_token ?? null
}
