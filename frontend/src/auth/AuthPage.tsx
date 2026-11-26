import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from './useAuth'

type AuthMode = 'sign-in' | 'sign-up' | 'reset' | 'recovery'

export function AuthPage() {
  const { configured, initializationError, recovery, signIn, signUp, resetPassword, updatePassword } = useAuth()
  const [mode, setMode] = useState<AuthMode>('sign-in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const effectiveMode = recovery ? 'recovery' : mode
  const isReset = effectiveMode === 'reset'
  const isSignUp = effectiveMode === 'sign-up'
  const isRecovery = effectiveMode === 'recovery'

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setMessage(null)
    setSubmitting(true)
    try {
      if (isReset) {
        await resetPassword(email)
        setMessage('If an account exists for that email, a password-reset link is on its way.')
      } else if (isRecovery) {
        await updatePassword(password)
        setMessage('Your password has been updated.')
      } else if (isSignUp) {
        const hasSession = await signUp(email, password)
        setMessage(
          hasSession
            ? 'Your account is ready.'
            : 'Account created. Check your email to confirm your address before signing in.',
        )
      } else {
        await signIn(email, password)
        setMessage('Signed in successfully.')
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Authentication request failed.')
    } finally {
      setSubmitting(false)
    }
  }

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode)
    setError(null)
    setMessage(null)
  }

  return (
    <section className="mx-auto max-w-lg rounded-xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl sm:p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-300">Personal portfolio</p>
      <h2 className="mt-2 text-2xl font-semibold text-white">
        {isReset || isRecovery ? 'Reset your password' : isSignUp ? 'Create your account' : 'Sign in to StockSense'}
      </h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        Market pages remain public. Sign in to securely view and manage your own portfolio.
      </p>

      {!configured ? (
        <p role="alert" className="mt-5 rounded-md border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-100">
          Authentication is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY in the frontend deployment.
        </p>
      ) : null}
      {initializationError ? (
        <p role="alert" className="mt-5 rounded-md border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">
          Could not restore your sign-in session: {initializationError}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-5 rounded-md border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="mt-5 rounded-md border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-200">
          {message}
        </p>
      ) : null}

      <form className="mt-6 space-y-4" onSubmit={(event) => void submit(event)}>
        <label className="block text-sm text-slate-300">
          Email
          <input
            autoComplete="email"
            className="mt-1.5 w-full rounded-md border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-cyan-400"
            disabled={!configured || submitting}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>
        {!isReset ? (
          <label className="block text-sm text-slate-300">
            {isRecovery ? 'New password' : 'Password'}
            <input
              autoComplete={isSignUp || isRecovery ? 'new-password' : 'current-password'}
              className="mt-1.5 w-full rounded-md border border-white/10 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-cyan-400"
              disabled={!configured || submitting}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
        ) : null}
        <button
          className="w-full rounded-md bg-cyan-300 px-4 py-2.5 font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:opacity-50"
          disabled={!configured || submitting}
          type="submit"
        >
          {submitting ? 'Please wait...' : isReset ? 'Send reset link' : isRecovery ? 'Save new password' : isSignUp ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <div className="mt-5 flex flex-wrap gap-x-4 gap-y-2 text-sm text-cyan-300">
        {effectiveMode !== 'sign-in' && !isRecovery ? (
          <button type="button" onClick={() => changeMode('sign-in')}>Back to sign in</button>
        ) : effectiveMode === 'sign-in' ? (
          <>
            <button type="button" onClick={() => changeMode('sign-up')}>Create an account</button>
            <button type="button" onClick={() => changeMode('reset')}>Forgot password?</button>
          </>
        ) : null}
      </div>
    </section>
  )
}
