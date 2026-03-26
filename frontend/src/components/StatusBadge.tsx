import type { DealStatus } from '../types/deal'

const labels: Record<DealStatus, string> = {
  active: 'Actif',
  won: 'Gagne',
  lost: 'Perdu',
}

const classes: Record<DealStatus, string> = {
  active: 'border border-amber-300 bg-amber-100 text-amber-900',
  won: 'border border-emerald-300 bg-emerald-100 text-emerald-900',
  lost: 'border border-slate-300 bg-slate-100 text-slate-700',
}

type StatusBadgeProps = {
  status: DealStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold tracking-[0.02em] ${classes[status]}`}>
      {labels[status]}
    </span>
  )
}
