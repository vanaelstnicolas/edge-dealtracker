import { Navigate, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { DashboardPage } from './pages/DashboardPage'
import { PipelinePage } from './pages/PipelinePage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
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
