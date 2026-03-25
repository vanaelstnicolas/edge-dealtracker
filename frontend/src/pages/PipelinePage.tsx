import { Fragment, useEffect, useMemo, useState, type ChangeEvent } from 'react'
import { StatusBadge } from '../components/StatusBadge'
import { fetchDeals, fetchUsers, importDealsFromExcel, updateDeal } from '../lib/api'
import type { Deal, DealStatus, UserMapping } from '../types/deal'

const statusOptions: Array<{ label: string; value: DealStatus | 'all' }> = [
  { label: 'Tous', value: 'all' },
  { label: 'Actifs', value: 'active' },
  { label: 'Gagnes', value: 'won' },
  { label: 'Perdus', value: 'lost' },
]

const editableStatusOptions: Array<{ label: string; value: DealStatus }> = [
  { label: 'Actif', value: 'active' },
  { label: 'Gagne', value: 'won' },
  { label: 'Perdu', value: 'lost' },
]

type DealEditDraft = {
  description: string
  action: string
  deadline: string
  status: DealStatus
  ownerId: string
}

function capitalizeFirst(value: string): string {
  if (!value) {
    return value
  }
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
}

function firstNameFromUser(user: UserMapping): string {
  const emailLocalPart = user.email.split('@')[0] ?? ''
  const emailBased = emailLocalPart.split(/[._-]/)[0]?.trim()
  if (emailBased) {
    return capitalizeFirst(emailBased)
  }

  const nameBased = user.fullName.trim().split(/\s+/)[0]
  if (nameBased) {
    return capitalizeFirst(nameBased)
  }

  return user.id
}

export function PipelinePage() {
  const [rows, setRows] = useState<Deal[]>([])
  const [users, setUsers] = useState<UserMapping[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<DealStatus | 'all'>('all')
  const [importing, setImporting] = useState(false)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const [editingDealId, setEditingDealId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<DealEditDraft | null>(null)
  const [saving, setSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  async function loadDeals() {
    setLoading(true)
    try {
      const [dealsData, usersData] = await Promise.all([fetchDeals(), fetchUsers()])
      setRows(dealsData)
      setUsers(usersData)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur de chargement')
    } finally {
      setLoading(false)
    }
  }

  async function handleImportFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }

    setImporting(true)
    setImportMessage(null)
    try {
      const result = await importDealsFromExcel(file)
      setImportMessage(`Import termine: ${result.imported} ajoutes, ${result.skipped} ignores.`)
      await loadDeals()
    } catch (err: unknown) {
      setImportMessage(err instanceof Error ? `Import echoue: ${err.message}` : 'Import echoue')
    } finally {
      setImporting(false)
    }
  }

  function startEdit(deal: Deal) {
    setEditingDealId(deal.id)
    setEditError(null)
    setEditDraft({
      description: deal.description,
      action: deal.action,
      deadline: deal.deadline,
      status: deal.status,
      ownerId: deal.ownerId,
    })
  }

  function cancelEdit() {
    setEditingDealId(null)
    setEditDraft(null)
    setEditError(null)
  }

  async function saveEdit() {
    if (!editingDealId || !editDraft) {
      return
    }

    setSaving(true)
    setEditError(null)
    try {
      await updateDeal(editingDealId, editDraft)
      await loadDeals()
      cancelEdit()
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : 'Erreur de sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    void loadDeals().catch(() => undefined)
  }, [])

  const ownerOptions = useMemo(() => {
    const firstNameCounts = new Map<string, number>()
    for (const user of users) {
      const firstName = firstNameFromUser(user)
      firstNameCounts.set(firstName, (firstNameCounts.get(firstName) ?? 0) + 1)
    }

    return users.map((user) => {
      const firstName = firstNameFromUser(user)
      const label = (firstNameCounts.get(firstName) ?? 0) > 1 ? `${firstName} (${user.fullName})` : firstName
      return { value: user.id, label }
    })
  }, [users])

  const ownerLabelById = useMemo(() => new Map(ownerOptions.map((option) => [option.value, option.label])), [ownerOptions])

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
          (ownerLabelById.get(deal.ownerId) ?? deal.owner).toLowerCase().includes(normalized)
        )
      })
      .sort((a, b) => a.deadline.localeCompare(b.deadline))
  }, [query, rows, status, ownerLabelById])

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
          placeholder="Rechercher entreprise, responsable, description"
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 md:max-w-md"
        />
        <div className="flex flex-wrap gap-2">
          {statusOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setStatus(option.value)}
              className={`rounded-xl px-3 py-2 text-sm font-medium ${
                status === option.value ? 'bg-edge-primary text-black' : 'bg-white text-slate-600 hover:bg-slate-100'
              }`}
            >
              {option.label}
            </button>
          ))}
          <label className="cursor-pointer rounded-xl bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
            {importing ? 'Import en cours...' : 'Importer Excel'}
            <input
              type="file"
              accept=".xlsx"
              onChange={(event) => {
                void handleImportFile(event)
              }}
              disabled={importing}
              className="hidden"
            />
          </label>
        </div>
      </section>

      {importMessage ? <p className="text-sm text-slate-600">{importMessage}</p> : null}

      <section className="overflow-hidden rounded-2xl border border-slate-200">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-[15px]">
            <thead className="bg-slate-50 text-sm text-slate-600">
              <tr>
                <th className="px-4 py-3 font-heading font-medium">Entreprise</th>
                <th className="px-4 py-3 font-heading font-medium">Description</th>
                <th className="px-4 py-3 font-heading font-medium">Action</th>
                <th className="px-4 py-3 font-heading font-medium">Deadline</th>
                <th className="px-4 py-3 font-heading font-medium">Responsable</th>
                <th className="px-4 py-3 font-heading font-medium">Statut</th>
                <th className="px-4 py-3 font-heading font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {deals.map((deal) => (
                <Fragment key={deal.id}>
                  <tr className="hover:bg-slate-50">
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
                    <td className="px-4 py-3 text-slate-700">{ownerLabelById.get(deal.ownerId) ?? deal.owner}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={deal.status} />
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => startEdit(deal)}
                        className="rounded-lg border border-slate-200 px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100"
                      >
                        Editer
                      </button>
                    </td>
                  </tr>

                  {editingDealId === deal.id && editDraft ? (
                    <tr>
                      <td colSpan={7} className="bg-slate-50 px-4 py-4">
                        <div className="grid gap-3 md:grid-cols-2">
                          <label className="text-sm text-slate-700">
                            Description
                            <textarea
                              value={editDraft.description}
                              onChange={(event) => setEditDraft({ ...editDraft, description: event.target.value })}
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                              rows={3}
                            />
                          </label>

                          <label className="text-sm text-slate-700">
                            Action
                            <input
                              value={editDraft.action}
                              onChange={(event) => setEditDraft({ ...editDraft, action: event.target.value })}
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                            />
                          </label>

                          <label className="text-sm text-slate-700">
                            Deadline
                            <input
                              type="date"
                              value={editDraft.deadline}
                              onChange={(event) => setEditDraft({ ...editDraft, deadline: event.target.value })}
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                            />
                          </label>

                          <label className="text-sm text-slate-700">
                            Statut
                            <select
                              value={editDraft.status}
                              onChange={(event) =>
                                setEditDraft({ ...editDraft, status: event.target.value as DealStatus })
                              }
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                            >
                              {editableStatusOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </label>

                          <label className="text-sm text-slate-700 md:col-span-2">
                            Responsable
                            <select
                              value={editDraft.ownerId}
                              onChange={(event) => setEditDraft({ ...editDraft, ownerId: event.target.value })}
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                            >
                              {ownerOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </select>
                          </label>
                        </div>

                        {editError ? <p className="mt-3 text-sm text-red-600">{editError}</p> : null}

                        <div className="mt-4 flex gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              void saveEdit()
                            }}
                            disabled={saving}
                            className="rounded-lg bg-edge-primary px-3 py-2 text-sm font-semibold text-black disabled:opacity-60"
                          >
                            {saving ? 'Sauvegarde...' : 'Sauvegarder'}
                          </button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            disabled={saving}
                            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700"
                          >
                            Annuler
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
