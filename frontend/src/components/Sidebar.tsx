import { NavLink } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import edgeLogo from '../assets/logo.svg'

const links = [
  { path: '/dashboard', label: 'Vue globale' },
  { path: '/pipeline', label: 'Pipeline' },
  { path: '/settings', label: 'Paramètres' },
]

export function Sidebar() {
  return (
    <aside className="relative w-full overflow-hidden rounded-3xl border border-black/10 bg-white/70 p-4 shadow-[0_20px_70px_rgba(15,17,22,0.12)] backdrop-blur md:w-72">
      <div className="absolute -left-8 -top-8 h-20 w-20 rounded-full bg-amber-200/45 blur-2xl" aria-hidden />
      <div className="mb-8 border-b border-black/10 pb-5">
        <img src={edgeLogo} alt="Edge" className="mx-auto h-8 w-auto" />
        <p className="mt-3 text-center text-[0.72rem] uppercase tracking-[0.22em] text-slate-500">Suivi commercial</p>
      </div>
      <nav className="flex gap-2 md:flex-col">
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            className={({ isActive }) =>
              `rounded-2xl px-4 py-2.5 text-sm font-semibold tracking-[0.01em] transition ${
                isActive
                  ? 'bg-black text-white shadow-[0_10px_30px_rgba(2,5,12,0.28)]'
                  : 'text-slate-600 hover:bg-white hover:text-slate-900'
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
        className="mt-7 w-full rounded-2xl border border-black/10 bg-white px-4 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:-translate-y-0.5 hover:bg-amber-50 hover:text-slate-900"
      >
        Se deconnecter
      </button>
    </aside>
  )
}
