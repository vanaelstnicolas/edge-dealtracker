import { useMemo, useState, type ChangeEvent } from 'react'

import { applyMeetingActions, extractMeetingActions, extractMeetingActionsFromFile, type MeetingAction } from '../lib/meetings'

const operationLabels: Record<MeetingAction['operation'], string> = {
  create: 'Nouveau dossier',
  update: 'Mettre a jour',
  close: 'Cloturer',
  ignore: 'Ignorer',
}

export function MeetingsPage() {
  const [content, setContent] = useState('')
  const [actions, setActions] = useState<MeetingAction[]>([])
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resultMessage, setResultMessage] = useState<string | null>(null)

  const selectedCount = useMemo(() => actions.filter((item) => item.selected).length, [actions])

  async function handleAnalyze() {
    const trimmed = content.trim()
    if (trimmed.length < 20) {
      setError('Ajoute un resume plus detaille pour lancer l analyse.')
      return
    }

    setLoading(true)
    setError(null)
    setResultMessage(null)
    try {
      const extracted = await extractMeetingActions(trimmed)
      setActions(extracted)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analyse indisponible')
    } finally {
      setLoading(false)
    }
  }

  async function handleApply() {
    const selected = actions.filter((item) => item.selected)
    if (selected.length === 0) {
      setError('Selectionne au moins une action a appliquer.')
      return
    }

    setApplying(true)
    setError(null)
    setResultMessage(null)
    try {
      const result = await applyMeetingActions(selected)
      setResultMessage(
        `Actions appliquees: ${result.created} crees, ${result.updated} mises a jour, ${result.closed} clotures, ${result.failed} en echec.`,
      )
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Application impossible')
    } finally {
      setApplying(false)
    }
  }

  async function handleLoadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) {
      return
    }

    setLoading(true)
    setError(null)
    setResultMessage(null)
    try {
      if (file.type.startsWith('text/') || /\.(txt|md|csv)$/i.test(file.name)) {
        const text = await file.text()
        setContent(text)
      }

      const extracted = await extractMeetingActionsFromFile(file)
      setActions(extracted)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Lecture du fichier impossible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5 edge-enter">
      <header className="edge-panel p-5 md:p-6">
        <p className="edge-eyebrow">Compte rendu de reunion</p>
        <h1 className="edge-title mt-2 font-heading text-3xl font-semibold">Import intelligent</h1>
        <p className="mt-2 text-sm text-slate-600">Colle un transcript (ou charge un fichier PDF/TXT) pour proposer des creations et mises a jour de dossiers.</p>
      </header>

      <section className="edge-panel p-4">
        <div className="flex flex-wrap items-center gap-2">
          <label className="cursor-pointer rounded-2xl bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100">
            Charger un fichier
            <input type="file" accept=".pdf,.txt,.md,.csv,text/plain,text/markdown,application/pdf" onChange={handleLoadFile} className="hidden" />
          </label>
          <button
            type="button"
            onClick={() => {
              void handleAnalyze()
            }}
            disabled={loading}
            className="rounded-2xl bg-black px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
          >
            {loading ? 'Analyse...' : 'Analyser le texte'}
          </button>
        </div>

        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={10}
          placeholder="Ex: Reunion avec ACME. Besoin: audit organisationnel. Prochaine etape: envoyer proposition vendredi."
          className="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
        />
      </section>

      {error ? <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
      {resultMessage ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{resultMessage}</p> : null}

      {actions.length > 0 ? (
        <section className="edge-panel p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="font-heading text-lg font-semibold text-slate-900">Actions proposees</h2>
            <button
              type="button"
              onClick={() => {
                void handleApply()
              }}
              disabled={applying}
              className="rounded-2xl bg-edge-primary px-3 py-2 text-sm font-semibold text-black disabled:opacity-60"
            >
              {applying ? 'Application...' : `Appliquer (${selectedCount})`}
            </button>
          </div>

          <div className="space-y-3">
            {actions.map((item, index) => (
              <article key={`${item.company}-${index}`} className="edge-panel-soft p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Boolean(item.selected)}
                    onChange={(event) => {
                      const checked = event.target.checked
                      setActions((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, selected: checked } : row)))
                    }}
                  />
                  <select
                    value={item.operation}
                    onChange={(event) => {
                      const value = event.target.value as MeetingAction['operation']
                      setActions((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, operation: value } : row)))
                    }}
                    className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm"
                  >
                    {Object.entries(operationLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <span className="text-xs text-slate-500">Confiance: {Math.round(item.confidence * 100)}%</span>
                </div>

                <div className="mt-2 grid gap-2 md:grid-cols-2">
                  <input
                    value={item.company}
                    onChange={(event) => {
                      const value = event.target.value
                      setActions((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, company: value } : row)))
                    }}
                    placeholder="Entreprise"
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                  <input
                    value={item.deadline}
                    onChange={(event) => {
                      const value = event.target.value
                      setActions((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, deadline: value } : row)))
                    }}
                    placeholder="Deadline YYYY-MM-DD"
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                  <input
                    value={item.action}
                    onChange={(event) => {
                      const value = event.target.value
                      setActions((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, action: value } : row)))
                    }}
                    placeholder="Prochaine action"
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm md:col-span-2"
                  />
                </div>
                {item.reason ? <p className="mt-2 text-xs text-slate-500">{item.reason}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
