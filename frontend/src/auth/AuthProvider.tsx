import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { User } from '@supabase/supabase-js'
import { clearQueryCache } from '../query/queryClient'
import { AuthContext } from './AuthContext'
import type { AuthContextValue } from './AuthContext'
import { supabaseClient } from './supabase'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(Boolean(supabaseClient))
  const [initializationError, setInitializationError] = useState<string | null>(null)
  const [recovery, setRecovery] = useState(false)
  const currentUserId = useRef<string | null>(null)

  useEffect(() => {
    if (!supabaseClient) return
    let active = true
    const updateUser = (nextUser: User | null) => {
      if (currentUserId.current !== (nextUser?.id ?? null)) {
        clearQueryCache()
        currentUserId.current = nextUser?.id ?? null
      }
      setUser(nextUser)
    }
    const {
      data: { subscription },
    } = supabaseClient.auth.onAuthStateChange((event, session) => {
      if (!active) return
      updateUser(session?.user ?? null)
      setRecovery(event === 'PASSWORD_RECOVERY')
      setLoading(false)
      setInitializationError(null)
    })

    void supabaseClient.auth
      .getSession()
      .then(({ data, error }) => {
        if (!active) return
        if (error) {
          setInitializationError(error.message)
          return
        }
        updateUser(data.session?.user ?? null)
      })
      .catch((error: unknown) => {
        if (!active) return
        setInitializationError(error instanceof Error ? error.message : 'Could not restore your sign-in session.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: Boolean(supabaseClient),
      loading,
      user,
      recovery,
      initializationError,
      async signIn(email, password) {
        if (!supabaseClient) throw new Error('Supabase sign-in is not configured for this website.')
        const { error } = await supabaseClient.auth.signInWithPassword({ email, password })
        if (error) throw error
      },
      async signUp(email, password) {
        if (!supabaseClient) throw new Error('Supabase sign-up is not configured for this website.')
        const { data, error } = await supabaseClient.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: window.location.origin },
        })
        if (error) throw error
        return Boolean(data.session)
      },
      async resetPassword(email) {
        if (!supabaseClient) throw new Error('Password reset is not configured for this website.')
        const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/portfolio`,
        })
        if (error) throw error
      },
      async updatePassword(password) {
        if (!supabaseClient) throw new Error('Password reset is not configured for this website.')
        const { error } = await supabaseClient.auth.updateUser({ password })
        if (error) throw error
        setRecovery(false)
      },
      async signOut() {
        if (!supabaseClient) return
        const { error } = await supabaseClient.auth.signOut()
        if (error) throw error
      },
    }),
    [initializationError, loading, recovery, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
