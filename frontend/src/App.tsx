import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import type { Session } from '@supabase/supabase-js'
import { Sidebar } from './components/Sidebar'
import { prefetchCoreData } from './lib/api'
import { supabase } from './lib/supabase'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { PipelinePage } from './pages/PipelinePage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!supabase) {
      setLoading(false)
      return
    }

    let mounted = true
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) {
          setSession(data.session)
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
        }
      })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
    })

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    if (!session) {
      return
    }
    prefetchCoreData()
  }, [session])

  if (loading) {
    return <p className="p-6 text-sm text-slate-500">Verification de session...</p>
  }

  if (!session) {
    return <LoginPage />
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f2f2ed] text-edge-text">
      <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-amber-200/65 blur-3xl" aria-hidden />
      <div className="pointer-events-none absolute -right-40 top-12 h-96 w-96 rounded-full bg-white/80 blur-3xl" aria-hidden />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.14]"
        style={{ backgroundImage: 'radial-gradient(#000 0.7px, transparent 0.7px)', backgroundSize: '16px 16px' }}
        aria-hidden
      />

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1340px] gap-5 px-4 py-5 md:px-6 md:py-7">
        <Sidebar />
        <main className="flex-1 rounded-[2rem] border border-black/10 bg-white/82 p-4 shadow-[0_24px_80px_rgba(13,17,23,0.14)] backdrop-blur md:p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
