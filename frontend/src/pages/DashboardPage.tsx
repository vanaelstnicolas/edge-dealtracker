import { mockDeals } from '../lib/mock-data'

function formatPct(value: number) {
  return `${Math.round(value * 100)}%`
}

export function DashboardPage() {
  const active = mockDeals.filter((deal) => deal.status === 'active').length
  const won = mockDeals.filter((deal) => deal.status === 'won').length
  const lost = mockDeals.filter((deal) => deal.status === 'lost').length
  const totalClosed = won + lost
  const conversion = totalClosed > 0 ? won / totalClosed : 0
  const now = new Date().toISOString().slice(0, 10)
  const lateDeals = mockDeals.filter((deal) => deal.status === 'active' && deal.deadline < now)

  const cards = [
    { label: 'Dossiers actifs', value: active.toString() },
    { label: 'Gagnes', value: won.toString() },
    { label: 'Perdus', value: lost.toString() },
    { label: 'Conversion', value: formatPct(conversion) },
  ]

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
                {deal.company} - echeance {deal.deadline} - owner {deal.owner}
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="font-heading text-lg font-semibold text-slate-900">Charge par collaborateur</h2>
          <div className="mt-4 space-y-3">
            {Object.entries(
              mockDeals
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
    </div>
  )
}
