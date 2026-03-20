import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import type { Session } from '@supabase/supabase-js'
import { Sidebar } from './components/Sidebar'
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

  if (loading) {
    return <p className="p-6 text-sm text-slate-500">Verification de session...</p>
  }

  if (!session) {
    return <LoginPage />
  }

  return (
    <div className="min-h-screen bg-slate-50 text-edge-text">
      <div className="mx-auto flex min-h-screen w-full max-w-[1280px] gap-4 p-4 md:p-6">
        <Sidebar />
        <main className="flex-1 rounded-2xl border border-slate-200 bg-white p-4 shadow-card md:p-6">
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
