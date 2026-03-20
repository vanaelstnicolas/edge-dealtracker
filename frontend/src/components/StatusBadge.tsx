import type { DealStatus } from '../types/deal'

const labels: Record<DealStatus, string> = {
  active: 'Actif',
  won: 'Gagne',
  lost: 'Perdu',
}

const classes: Record<DealStatus, string> = {
  active: 'bg-edge-primary text-black',
  won: 'bg-edge-success text-black',
  lost: 'bg-slate-200 text-slate-700',
}

type StatusBadgeProps = {
  status: DealStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${classes[status]}`}>
      {labels[status]}
    </span>
  )
}
