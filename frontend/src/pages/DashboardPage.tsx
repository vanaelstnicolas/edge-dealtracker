import { useEffect, useState } from 'react'
import { fetchDeals, fetchMyActionSummary, sendMyActionSummary, type MyActionSummary } from '../lib/api'
import type { Deal } from '../types/deal'

function formatPct(value: number) {
  return `${Math.round(value * 100)}%`
}

function ownerFirstName(owner: string): string {
  const normalized = owner.trim()
  if (!normalized) {
    return owner
  }

  const base = normalized.includes('@') ? normalized.split('@')[0] : normalized
  const token = base.split(/[._\-\s]+/)[0]
  if (!token) {
    return normalized
  }

  return token.charAt(0).toUpperCase() + token.slice(1).toLowerCase()
}

function channelStatusLabel(channel: 'whatsapp' | 'email', status: string): string {
  const channelLabel = channel === 'whatsapp' ? 'WhatsApp' : 'Email'
  if (status === 'sent') {
    return `${channelLabel} envoye`
  }
  if (status === 'not_configured') {
    return `${channelLabel} non configure`
  }
  if (status === 'skipped') {
    return `${channelLabel} ignore`
  }
  return `${channelLabel} statut: ${status}`
}

export function DashboardPage() {
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<MyActionSummary | null>(null)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [summaryStatus, setSummaryStatus] = useState<string | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [sendingSummary, setSendingSummary] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchDeals()
      .then((data) => {
        if (cancelled) {
          return
        }
        setDeals(data)
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

  const active = deals.filter((deal) => deal.status === 'active').length
  const won = deals.filter((deal) => deal.status === 'won').length
  const lost = deals.filter((deal) => deal.status === 'lost').length
  const totalClosed = won + lost
  const conversion = totalClosed > 0 ? won / totalClosed : 0
  const now = new Date().toISOString().slice(0, 10)
  const lateDeals = deals.filter((deal) => deal.status === 'active' && deal.deadline < now)

  const cards = [
    { label: 'Dossiers actifs', value: active.toString() },
    { label: 'Gagnes', value: won.toString() },
    { label: 'Perdus', value: lost.toString() },
    { label: 'Conversion', value: formatPct(conversion) },
  ]

  if (loading) {
    return <p className="text-sm text-slate-500">Chargement du dashboard...</p>
  }

  if (error) {
    return <p className="text-sm text-red-600">Erreur API: {error}</p>
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-heading text-2xl font-semibold">Dashboard commercial</h1>
        <p className="text-sm text-slate-500">Vue temps reel du pipeline et des risques.</p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <article key={card.label} className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-sm text-slate-500">{card.label}</p>
            <p className="mt-2 font-heading text-3xl font-semibold text-slate-900">{card.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-2xl border border-red-100 bg-red-50 p-4">
          <h2 className="font-heading text-lg font-semibold text-red-700">Alertes deadline</h2>
          <ul className="mt-3 space-y-2 text-sm text-red-700">
            {lateDeals.length === 0 && <li>Aucun retard detecte.</li>}
            {lateDeals.map((deal) => (
              <li key={deal.id}>
                {deal.company} - echeance {deal.deadline} - owner {ownerFirstName(deal.owner)}
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="font-heading text-lg font-semibold text-slate-900">Charge par collaborateur</h2>
          <div className="mt-4 space-y-3">
            {Object.entries(
              deals
                .filter((deal) => deal.status === 'active')
                .reduce<Record<string, number>>((acc, deal) => {
                  acc[deal.owner] = (acc[deal.owner] || 0) + 1
                  return acc
                }, {}),
            ).map(([owner, count]) => (
              <div key={owner}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span>{owner}</span>
                  <span>{count}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-edge-primary"
                    style={{ width: `${Math.min(100, count * 25)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-heading text-lg font-semibold text-slate-900">Mon resume to-do</h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={summaryLoading}
              onClick={async () => {
                setSummaryLoading(true)
                setSummaryError(null)
                setSummaryStatus(null)
                try {
                  const next = await fetchMyActionSummary()
                  setSummary(next)
                } catch (err: unknown) {
                  setSummaryError(err instanceof Error ? err.message : 'Impossible de charger le resume')
                } finally {
                  setSummaryLoading(false)
                }
              }}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-60"
            >
              {summaryLoading ? 'Chargement...' : 'Afficher mon resume'}
            </button>
            <button
              type="button"
              disabled={sendingSummary}
              onClick={async () => {
                setSendingSummary(true)
                setSummaryError(null)
                setSummaryStatus(null)
                try {
                  const result = await sendMyActionSummary()
                  setSummaryStatus(
                    `Resume envoye - ${channelStatusLabel('whatsapp', result.whatsapp)} - ${channelStatusLabel('email', result.email)}`,
                  )
                } catch (err: unknown) {
                  setSummaryError(err instanceof Error ? err.message : 'Impossible d envoyer le resume')
                } finally {
                  setSendingSummary(false)
                }
              }}
              className="rounded-xl bg-edge-primary px-3 py-2 text-sm font-semibold text-black disabled:opacity-60"
            >
              {sendingSummary ? 'Envoi...' : 'Envoyer sur WhatsApp + Email'}
            </button>
          </div>
        </div>

        {summaryStatus ? <p className="mt-3 text-sm text-emerald-700">{summaryStatus}</p> : null}
        {summaryError ? <p className="mt-3 text-sm text-red-600">{summaryError}</p> : null}

        {summary ? (
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <p className="font-medium text-slate-900">{summary.summary}</p>
            {summary.items.length === 0 ? (
              <p>Aucune action active.</p>
            ) : (
              <ul className="list-disc space-y-1 pl-5">
                {summary.items.map((item, index) => (
                  <li key={`${item.company}-${index}`}>
                    {item.company} - {item.action} (deadline {item.deadline})
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </section>
    </div>
  )
}
