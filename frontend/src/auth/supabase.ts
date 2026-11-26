import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim()
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim()

export const supabaseClient =
  supabaseUrl && supabasePublishableKey ? createClient(supabaseUrl, supabasePublishableKey) : null

export async function getAccessToken(): Promise<string | null> {
  if (!supabaseClient) return null
  const { data, error } = await supabaseClient.auth.getSession()
  if (error) throw error
  return data.session?.access_token ?? null
}
