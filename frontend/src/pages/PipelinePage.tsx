import { Fragment, useEffect, useMemo, useState, type ChangeEvent } from 'react'
import { StatusBadge } from '../components/StatusBadge'
import { createDeal, deleteDeal, fetchDeals, fetchUsers, importDealsFromExcel, updateDeal, type DealScope } from '../lib/api'
import type { Deal, DealStatus, UserMapping } from '../types/deal'

const statusOptions: Array<{ label: string; value: DealStatus | 'all' }> = [
  { label: 'Tous', value: 'all' },
  { label: 'Gagnés', value: 'won' },
  { label: 'Perdus', value: 'lost' },
]

const scopeOptions: Array<{ label: string; value: DealScope }> = [
  { label: 'Tous', value: 'all' },
  { label: 'Actifs', value: 'active' },
  { label: 'Archivés', value: 'archived' },
]

const editableStatusOptions: Array<{ label: string; value: DealStatus }> = [
  { label: 'Actif', value: 'active' },
  { label: 'Gagné', value: 'won' },
  { label: 'Perdu', value: 'lost' },
]

type DealEditDraft = {
  description: string
  action: string
  deadline: string
  status: DealStatus
  ownerId: string
}

type DealCreateDraft = {
  company: string
  description: string
  action: string
  deadline: string
}

type SortKey = 'company' | 'deadline' | 'owner' | 'status'

function capitalizeFirst(value: string): string {
  if (!value) {
    return value
  }
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
}

function firstNameFromUser(user: UserMapping): string {
  const nameBased = user.fullName.trim().split(/\s+/)[0]
  if (nameBased) {
    return capitalizeFirst(nameBased)
  }

  const emailLocalPart = user.email.split('@')[0] ?? ''
  const emailBased = emailLocalPart.split(/[._-]/)[0]?.trim()
  if (emailBased) {
    return capitalizeFirst(emailBased)
  }

  return user.id
}

function humanizeApiError(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback
  }

  const raw = error.message.trim()
  if (!raw.startsWith('{')) {
    return raw || fallback
  }

  try {
    const payload = JSON.parse(raw) as {
      detail?: Array<{ loc?: Array<string | number>; type?: string; msg?: string }>
    }
    const first = payload.detail?.[0]
    if (!first) {
      return fallback
    }

    const loc = (first.loc ?? []).join('.')
    if (loc.includes('action') && first.type === 'string_too_short') {
      return "L'action est trop courte. Ajoute au moins 2 caracteres."
    }
    if (loc.includes('action') && first.type === 'string_too_long') {
      return "L'action est trop longue. Maximum 500 caracteres."
    }
    if (loc.includes('description') && first.type === 'string_too_short') {
      return 'La description est trop courte. Ajoute plus de contexte.'
    }
    if (loc.includes('description') && first.type === 'string_too_long') {
      return 'La description est trop longue. Maximum 500 caracteres.'
    }
    if (loc.includes('company') && first.type === 'string_too_short') {
      return "Le nom d'entreprise est trop court."
    }

    return first.msg || fallback
  } catch {
    return raw || fallback
  }
}

export function PipelinePage() {
  const today = new Date().toISOString().slice(0, 10)
  const [rows, setRows] = useState<Deal[]>([])
  const [users, setUsers] = useState<UserMapping[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState<DealScope>('all')
  const [ownerFilter, setOwnerFilter] = useState<string>('all')
  const [status, setStatus] = useState<DealStatus | 'all'>('all')
  const [sortKey, setSortKey] = useState<SortKey>('deadline')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [importing, setImporting] = useState(false)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const [createDraft, setCreateDraft] = useState<DealCreateDraft>({
    company: '',
    description: '',
    action: '',
    deadline: today,
  })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [statusUpdatingDealId, setStatusUpdatingDealId] = useState<string | null>(null)
  const [deletingDealId, setDeletingDealId] = useState<string | null>(null)
  const [editingDealId, setEditingDealId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<DealEditDraft | null>(null)
  const [saving, setSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  async function loadDeals() {
    setLoading(true)
    try {
      const [dealsData, usersData] = await Promise.all([fetchDeals(scope), fetchUsers()])
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
      setImportMessage(`Import termine: ${result.imported} dossiers ajoutes, ${result.skipped} lignes ignorees.`)
      await loadDeals()
    } catch (err: unknown) {
      setImportMessage(err instanceof Error ? `Import echoue: ${err.message}` : 'Import echoue')
    } finally {
      setImporting(false)
    }
  }

  async function handleCreateDeal() {
    setCreateError(null)
    const company = createDraft.company.trim()
    const description = createDraft.description.trim()
    const action = createDraft.action.trim()
    const deadline = createDraft.deadline

    if (!company || !description || !action || !deadline) {
      setCreateError('Tous les champs du nouveau dossier sont obligatoires.')
      return
    }
    if (action.length < 2) {
      setCreateError("L'action est trop courte. Ajoute au moins 2 caracteres.")
      return
    }
    if (action.length > 500) {
      setCreateError("L'action est trop longue. Maximum 500 caracteres.")
      return
    }
    if (description.length < 2) {
      setCreateError('La description est trop courte.')
      return
    }
    if (description.length > 500) {
      setCreateError('La description est trop longue. Maximum 500 caracteres.')
      return
    }

    setCreating(true)
    try {
      await createDeal({ company, description, action, deadline })
      setCreateDraft({ company: '', description: '', action: '', deadline })
      await loadDeals()
    } catch (err: unknown) {
      setCreateError(humanizeApiError(err, 'Erreur lors de la creation du dossier'))
    } finally {
      setCreating(false)
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

    const currentDeal = rows.find((row) => row.id === editingDealId)
    if (!currentDeal) {
      setEditError('Le dossier est introuvable. Recharge la page puis recommence.')
      return
    }

    const payload: {
      description?: string
      action?: string
      deadline?: string
      status?: DealStatus
      ownerId?: string
    } = {}

    if (editDraft.description !== currentDeal.description) {
      payload.description = editDraft.description
    }
    if (editDraft.action !== currentDeal.action) {
      payload.action = editDraft.action
    }
    if (editDraft.deadline !== currentDeal.deadline) {
      payload.deadline = editDraft.deadline
    }
    if (editDraft.status !== currentDeal.status) {
      payload.status = editDraft.status
    }
    if (editDraft.ownerId !== currentDeal.ownerId) {
      payload.ownerId = editDraft.ownerId
    }

    if (Object.keys(payload).length === 0) {
      cancelEdit()
      return
    }

    if (payload.action !== undefined && payload.action.trim().length < 2) {
      setEditError("L'action est trop courte. Ajoute au moins 2 caracteres.")
      return
    }
    if (payload.action !== undefined && payload.action.trim().length > 500) {
      setEditError("L'action est trop longue. Maximum 500 caracteres.")
      return
    }
    if (payload.description !== undefined && payload.description.trim().length < 2) {
      setEditError('La description est trop courte. Ajoute plus de detail.')
      return
    }
    if (payload.description !== undefined && payload.description.trim().length > 500) {
      setEditError('La description est trop longue. Maximum 500 caracteres.')
      return
    }

    setSaving(true)
    setEditError(null)
    try {
      await updateDeal(editingDealId, payload)
      await loadDeals()
      cancelEdit()
    } catch (err: unknown) {
      setEditError(humanizeApiError(err, 'Erreur de sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  async function updateDealStatusQuick(deal: Deal, nextStatus: DealStatus) {
    setStatusUpdatingDealId(deal.id)
    setEditError(null)
    try {
      await updateDeal(deal.id, { status: nextStatus })
      await loadDeals()
    } catch (err: unknown) {
      setEditError(humanizeApiError(err, 'Erreur de changement de statut'))
    } finally {
      setStatusUpdatingDealId(null)
    }
  }

  async function deleteDealQuick(deal: Deal) {
    const confirmed = window.confirm(`Supprimer le dossier ${deal.company} ?`)
    if (!confirmed) {
      return
    }

    setDeletingDealId(deal.id)
    setEditError(null)
    try {
      await deleteDeal(deal.id)
      await loadDeals()
      if (editingDealId === deal.id) {
        cancelEdit()
      }
    } catch (err: unknown) {
      setEditError(err instanceof Error ? err.message : 'Erreur de suppression')
    } finally {
      setDeletingDealId(null)
    }
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDirection('asc')
  }

  useEffect(() => {
    void loadDeals().catch(() => undefined)
  }, [scope])

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
      .filter((deal) => (ownerFilter === 'all' ? true : deal.ownerId === ownerFilter))
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
      .sort((a, b) => {
        let result = 0
        if (sortKey === 'deadline') {
          result = a.deadline.localeCompare(b.deadline)
        } else if (sortKey === 'company') {
          result = a.company.localeCompare(b.company)
        } else if (sortKey === 'owner') {
          const ownerA = ownerLabelById.get(a.ownerId) ?? a.owner
          const ownerB = ownerLabelById.get(b.ownerId) ?? b.owner
          result = ownerA.localeCompare(ownerB)
        } else {
          result = a.status.localeCompare(b.status)
        }
        return sortDirection === 'asc' ? result : -result
      })
  }, [ownerFilter, ownerLabelById, query, rows, sortDirection, sortKey, status])

  function sortIndicator(key: SortKey): string {
    if (sortKey !== key) {
      return '↕'
    }
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Chargement du pipeline...</p>
  }

  if (error) {
    return <p className="text-sm text-red-600">Une erreur est survenue: {error}</p>
  }

  return (
    <div className="space-y-5 edge-enter">
      <header className="edge-panel p-5 md:p-6">
        <p className="edge-eyebrow">Suivi des opportunites</p>
        <h1 className="edge-title mt-2 font-heading text-3xl font-semibold text-slate-900">Pipeline</h1>
        <p className="mt-2 text-sm text-slate-600">Gestion des dossiers actifs et archives avec edition rapide.</p>
      </header>

      <section className="edge-panel flex flex-col gap-3 p-3 md:flex-row md:items-center md:justify-between">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Rechercher entreprise, responsable, description"
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 md:max-w-md"
        />
        <div className="flex flex-wrap gap-2">
          {scopeOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setScope(option.value)}
              className={`rounded-2xl px-3 py-2 text-sm font-medium transition ${
                scope === option.value ? 'bg-black text-white' : 'bg-white text-slate-600 hover:bg-slate-100'
              }`}
            >
              {option.label}
            </button>
          ))}
          {statusOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setStatus(option.value)}
              className={`rounded-2xl px-3 py-2 text-sm font-medium transition ${
                status === option.value ? 'bg-amber-200 text-black' : 'bg-white text-slate-600 hover:bg-slate-100'
              }`}
            >
              {option.label}
            </button>
          ))}
          <label className="cursor-pointer rounded-2xl bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100">
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
          <label className="rounded-2xl bg-white px-3 py-2 text-sm font-medium text-slate-700">
            Collaborateur
            <select
              value={ownerFilter}
              onChange={(event) => setOwnerFilter(event.target.value)}
              className="ml-2 rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm"
            >
              <option value="all">Tous</option>
              {ownerOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="edge-panel p-4">
        <h2 className="font-heading text-base font-semibold text-slate-900">Nouveau dossier</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-sm text-slate-700">
            Entreprise
            <input
              value={createDraft.company}
              onChange={(event) => setCreateDraft({ ...createDraft, company: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm text-slate-700">
            Deadline
            <input
              type="date"
              value={createDraft.deadline}
              onChange={(event) => setCreateDraft({ ...createDraft, deadline: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm text-slate-700 md:col-span-2">
            Description
            <textarea
              value={createDraft.description}
              onChange={(event) => setCreateDraft({ ...createDraft, description: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              rows={3}
            />
          </label>
          <label className="text-sm text-slate-700 md:col-span-2">
            Prochaine action
            <textarea
              value={createDraft.action}
              onChange={(event) => setCreateDraft({ ...createDraft, action: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              rows={3}
            />
          </label>
        </div>
        {createError ? <p className="mt-3 text-sm text-red-600">{createError}</p> : null}
        <div className="mt-4">
          <button
            type="button"
            onClick={() => {
              void handleCreateDeal()
            }}
            disabled={creating}
            className="rounded-lg bg-edge-primary px-3 py-2 text-sm font-semibold text-black disabled:opacity-60"
          >
            {creating ? 'Creation...' : 'Creer le dossier'}
          </button>
        </div>
      </section>

      {importMessage ? <p className="text-sm text-slate-600">{importMessage}</p> : null}

      <section className="edge-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-[15px]">
            <thead className="bg-slate-50/80 text-sm text-slate-600">
              <tr>
                <th className="px-4 py-3 font-heading font-medium">
                  <button type="button" onClick={() => toggleSort('company')} className="inline-flex items-center gap-1 hover:text-slate-900">
                    Entreprise <span className="text-xs text-slate-400">{sortIndicator('company')}</span>
                  </button>
                </th>
                <th className="px-4 py-3 font-heading font-medium">Description</th>
                <th className="px-4 py-3 font-heading font-medium">Action</th>
                <th className="px-4 py-3 font-heading font-medium">
                  <button type="button" onClick={() => toggleSort('deadline')} className="inline-flex items-center gap-1 hover:text-slate-900">
                    Deadline <span className="text-xs text-slate-400">{sortIndicator('deadline')}</span>
                  </button>
                </th>
                <th className="px-4 py-3 font-heading font-medium">
                  <button type="button" onClick={() => toggleSort('owner')} className="inline-flex items-center gap-1 hover:text-slate-900">
                    Responsable <span className="text-xs text-slate-400">{sortIndicator('owner')}</span>
                  </button>
                </th>
                <th className="px-4 py-3 font-heading font-medium">
                  <button type="button" onClick={() => toggleSort('status')} className="inline-flex items-center gap-1 hover:text-slate-900">
                    Statut <span className="text-xs text-slate-400">{sortIndicator('status')}</span>
                  </button>
                </th>
                <th className="px-4 py-3 font-heading font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {deals.map((deal) => (
                <Fragment key={deal.id}>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{deal.company}</td>
                    <td className="whitespace-pre-line px-4 py-3 text-slate-600">{deal.description}</td>
                    <td className="whitespace-pre-line px-4 py-3 text-slate-700">{deal.action}</td>
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
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => startEdit(deal)}
                          className="rounded-lg border border-slate-200 px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100"
                        >
                          Editer
                        </button>
                        {deal.status === 'active' ? (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                void updateDealStatusQuick(deal, 'won')
                              }}
                              disabled={statusUpdatingDealId === deal.id}
                              className="rounded-lg border border-emerald-300 px-3 py-1 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-60"
                            >
                              Gagne
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                void updateDealStatusQuick(deal, 'lost')
                              }}
                              disabled={statusUpdatingDealId === deal.id}
                              className="rounded-lg border border-rose-300 px-3 py-1 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-60"
                            >
                              Perdu
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              void updateDealStatusQuick(deal, 'active')
                            }}
                            disabled={statusUpdatingDealId === deal.id}
                            className="rounded-lg border border-slate-300 px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                          >
                            Reouvrir
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            void deleteDealQuick(deal)
                          }}
                          disabled={deletingDealId === deal.id}
                          className="rounded-lg border border-red-300 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
                        >
                          {deletingDealId === deal.id ? 'Suppression...' : 'Supprimer'}
                        </button>
                      </div>
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
                            <textarea
                              value={editDraft.action}
                              onChange={(event) => setEditDraft({ ...editDraft, action: event.target.value })}
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                              rows={3}
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
