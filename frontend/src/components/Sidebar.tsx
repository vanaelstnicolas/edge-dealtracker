import { NavLink } from 'react-router-dom'
import { supabase } from '../lib/supabase'

const links = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/pipeline', label: 'Pipeline' },
  { path: '/settings', label: 'Settings' },
]

export function Sidebar() {
  return (
    <aside className="w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-card md:w-64">
      <div className="mb-8 border-b border-slate-100 pb-4">
        <p className="font-heading text-lg font-semibold">Edge Consulting</p>
        <p className="text-sm text-slate-500">DealTracker MVP</p>
      </div>
      <nav className="flex gap-2 md:flex-col">
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            className={({ isActive }) =>
              `rounded-xl px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'bg-edge-primary text-black'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <button
        type="button"
        onClick={() => {
          void supabase?.auth.signOut()
        }}
        className="mt-6 w-full rounded-xl border border-slate-200 px-3 py-2 text-left text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900"
      >
        Se deconnecter
      </button>
    </aside>
  )
}
