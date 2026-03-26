import { useState } from 'react'
import edgeLogo from '../assets/logo.svg'
import { isSupabaseConfigured, supabase } from '../lib/supabase'

export function LoginPage() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    if (!supabase) {
      setError('La connexion est indisponible pour le moment. Merci de contacter le support.')
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
    <div className="mx-auto flex min-h-screen w-full max-w-[640px] items-center p-6">
      <div className="relative w-full overflow-hidden rounded-[2rem] border border-black/10 bg-white/85 p-8 shadow-[0_25px_70px_rgba(14,22,34,0.2)] backdrop-blur">
        <div className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-amber-200/60 blur-3xl" aria-hidden />
        <img src={edgeLogo} alt="Edge" className="relative mx-auto h-14 w-auto" />
        <p className="relative mt-5 text-[0.72rem] uppercase tracking-[0.22em] text-slate-500">Suivi commercial</p>
        <h1 className="relative mt-2 font-heading text-3xl font-semibold text-slate-900">Connexion DealTracker</h1>
        <p className="relative mt-3 max-w-md text-sm text-slate-600">Connecte-toi avec ton compte Microsoft Entra pour retrouver ton pipeline, tes alertes et ton resume omnicanal.</p>
        <button
          type="button"
          onClick={() => {
            void handleLogin()
          }}
          disabled={loading || !isSupabaseConfigured}
          className="relative mt-7 inline-flex rounded-2xl bg-black px-5 py-2.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? 'Redirection...' : 'Se connecter avec Microsoft'}
        </button>
        {error && <p className="relative mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  )
}
