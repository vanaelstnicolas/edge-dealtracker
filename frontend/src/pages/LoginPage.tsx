import { useState } from 'react'
import { isSupabaseConfigured, supabase } from '../lib/supabase'

export function LoginPage() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    if (!supabase) {
      setError('Supabase non configure. Ajoute VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY dans frontend/.env.local.')
      return
    }

    setLoading(true)
    setError(null)
    const { error: loginError } = await supabase.auth.signInWithOAuth({
      provider: 'azure',
      options: {
        redirectTo: window.location.origin,
        queryParams: { prompt: 'select_account' },
      },
    })
    if (loginError) {
      setError(loginError.message)
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[560px] items-center p-6">
      <div className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
        <h1 className="font-heading text-2xl font-semibold text-slate-900">Connexion DealTracker</h1>
        <p className="mt-2 text-sm text-slate-600">Connecte-toi avec ton compte Microsoft Entra.</p>
        <button
          type="button"
          onClick={() => {
            void handleLogin()
          }}
          disabled={loading || !isSupabaseConfigured}
          className="mt-5 rounded-xl bg-edge-primary px-4 py-2 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? 'Redirection...' : 'Se connecter avec Microsoft'}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  )
}
