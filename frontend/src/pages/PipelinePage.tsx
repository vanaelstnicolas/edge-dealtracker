import { useEffect, useMemo, useState } from 'react'
import { StatusBadge } from '../components/StatusBadge'
import { fetchDeals } from '../lib/api'
import type { Deal } from '../types/deal'
import type { DealStatus } from '../types/deal'

const statusOptions: Array<{ label: string; value: DealStatus | 'all' }> = [
  { label: 'Tous', value: 'all' },
  { label: 'Actifs', value: 'active' },
  { label: 'Gagnes', value: 'won' },
  { label: 'Perdus', value: 'lost' },
]

export function PipelinePage() {
  const [rows, setRows] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<DealStatus | 'all'>('all')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchDeals()
      .then((data) => {
        if (cancelled) {
          return
        }
        setRows(data)
        setError(null)
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return
        }
        setError(err instanceof Error ? err.message : 'Erreur de chargement')
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const deals = useMemo(() => {
    const normalized = query.toLowerCase().trim()
    return rows
      .filter((deal) => (status === 'all' ? true : deal.status === status))
      .filter((deal) => {
        if (!normalized) {
          return true
        }
        return (
          deal.company.toLowerCase().includes(normalized) ||
          deal.description.toLowerCase().includes(normalized) ||
          deal.owner.toLowerCase().includes(normalized)
        )
      })
      .sort((a, b) => a.deadline.localeCompare(b.deadline))
  }, [query, rows, status])

  const today = new Date().toISOString().slice(0, 10)

  if (loading) {
    return <p className="text-sm text-slate-500">Chargement du pipeline...</p>
  }

  if (error) {
    return <p className="text-sm text-red-600">Erreur API: {error}</p>
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="font-heading text-2xl font-semibold">Pipeline</h1>
        <p className="text-sm text-slate-500">Gestion des dossiers actifs, gagnes et perdus.</p>
      </header>

      <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 md:flex-row md:items-center md:justify-between">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Rechercher entreprise, owner, description"
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 md:max-w-md"
        />
        <div className="flex flex-wrap gap-2">
          {statusOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setStatus(option.value)}
              className={`rounded-xl px-3 py-2 text-sm font-medium ${
                status === option.value
                  ? 'bg-edge-primary text-black'
                  : 'bg-white text-slate-600 hover:bg-slate-100'
              }`}
            >
              {option.label}
            </button>
          ))}
          <button type="button" className="rounded-xl bg-edge-primary px-3 py-2 text-sm font-semibold">
            + Nouveau dossier
          </button>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-[15px]">
            <thead className="bg-slate-50 text-sm text-slate-600">
              <tr>
                <th className="px-4 py-3 font-heading font-medium">Entreprise</th>
                <th className="px-4 py-3 font-heading font-medium">Description</th>
                <th className="px-4 py-3 font-heading font-medium">Action</th>
                <th className="px-4 py-3 font-heading font-medium">Deadline</th>
                <th className="px-4 py-3 font-heading font-medium">Owner</th>
                <th className="px-4 py-3 font-heading font-medium">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {deals.map((deal) => (
                <tr key={deal.id} className="cursor-pointer hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{deal.company}</td>
                  <td className="px-4 py-3 text-slate-600">{deal.description}</td>
                  <td className="px-4 py-3 text-slate-700">{deal.action}</td>
                  <td
                    className={`px-4 py-3 ${
                      deal.status === 'active' && deal.deadline < today ? 'font-semibold text-red-700' : ''
                    }`}
                  >
                    {deal.deadline}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{deal.owner}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={deal.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
