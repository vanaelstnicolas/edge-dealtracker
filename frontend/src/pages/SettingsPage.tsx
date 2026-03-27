import { useEffect, useState } from 'react'
import { fetchUsers, sendWhatsappTest, updateUserProfile } from '../lib/api'
import type { UserMapping } from '../types/deal'

const e164Regex = /^\+[1-9]\d{6,14}$/

function getSettingsErrorMessage(error: unknown): string {
  const fallback = 'Erreur de sauvegarde'
  if (!(error instanceof Error)) {
    return fallback
  }

  if (error.message.includes('Forbidden owner scope')) {
    return "Tu n'as pas les droits pour modifier cet utilisateur."
  }

  return error.message || fallback
}

export function SettingsPage() {
  const [rows, setRows] = useState<UserMapping[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingFor, setSavingFor] = useState<string | null>(null)
  const [sendingTestFor, setSendingTestFor] = useState<string | null>(null)
  const [testMessage, setTestMessage] = useState<string | null>(null)

  async function saveRow(row: UserMapping) {
    if (!e164Regex.test(row.whatsappNumber)) {
      return
    }
    if (row.fullName.trim().length < 2) {
      setError('Le surnom doit contenir au moins 2 caracteres.')
      return
    }

    setSavingFor(row.id)
    setError(null)
    try {
      const updated = await updateUserProfile(row.id, {
        fullName: row.fullName.trim(),
        whatsappNumber: row.whatsappNumber,
      })
      setRows((current) =>
        current.map((item) =>
          item.id === updated.id
            ? { ...item, fullName: updated.fullName, whatsappNumber: updated.whatsappNumber }
            : item,
        ),
      )
    } catch (err) {
      setError(getSettingsErrorMessage(err))
    } finally {
      setSavingFor(null)
    }
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchUsers()
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
        setError(getSettingsErrorMessage(err))
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

  if (loading) {
    return <p className="text-sm text-slate-500">Chargement des utilisateurs...</p>
  }

  if (error) {
    return <p className="text-sm text-red-600">Une erreur est survenue: {error}</p>
  }

  return (
    <div className="space-y-5 edge-enter">
      <header className="edge-panel p-5 md:p-6">
        <p className="edge-eyebrow">Operations settings</p>
        <h1 className="edge-title mt-2 font-heading text-3xl font-semibold">Paramètres</h1>
        <p className="mt-2 text-sm text-slate-600">Annuaire utilisateurs: personnalise le surnom affiche et le numero WhatsApp (ex: +32470123456).</p>
      </header>

      <section className="edge-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-[15px]">
            <thead className="bg-slate-50 text-sm text-slate-600">
              <tr>
                <th className="px-4 py-3 font-heading font-medium">Surnom affiche</th>
                <th className="px-4 py-3 font-heading font-medium">Email</th>
                <th className="px-4 py-3 font-heading font-medium">WhatsApp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => {
                const valid = e164Regex.test(row.whatsappNumber)
                return (
                  <tr key={row.id}>
                    <td className="px-4 py-3">
                      <input
                        value={row.fullName}
                        onChange={(event) => {
                          setRows((current) =>
                            current.map((item) =>
                              item.id === row.id ? { ...item, fullName: event.target.value } : item,
                            ),
                          )
                        }}
                        onBlur={async () => {
                          await saveRow(row)
                        }}
                        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-900 outline-none focus:border-slate-400"
                      />
                    </td>
                    <td className="px-4 py-3 text-slate-600">{row.email}</td>
                    <td className="px-4 py-3">
                      <input
                        value={row.whatsappNumber}
                        onChange={(event) => {
                          setRows((current) =>
                            current.map((item) =>
                              item.id === row.id ? { ...item, whatsappNumber: event.target.value } : item,
                            ),
                          )
                        }}
                        onBlur={async () => {
                          await saveRow(row)
                        }}
                        className={`w-full rounded-xl border px-3 py-2 text-sm outline-none ${
                          valid ? 'border-slate-200 focus:border-slate-400' : 'border-red-300 focus:border-red-500'
                        }`}
                      />
                      {!valid && <p className="mt-1 text-xs text-red-600">Format attendu: +33612345678</p>}
                      {savingFor === row.id ? <p className="mt-1 text-xs text-slate-500">Sauvegarde...</p> : null}
                      <button
                        type="button"
                        onClick={async () => {
                          setError(null)
                          setTestMessage(null)
                          setSendingTestFor(row.id)
                          try {
                            await sendWhatsappTest(row.id)
                            setTestMessage('Message de test WhatsApp envoye avec succes.')
                          } catch (err) {
                            setError(getSettingsErrorMessage(err))
                          } finally {
                            setSendingTestFor(null)
                          }
                        }}
                        disabled={!valid || sendingTestFor === row.id}
                        className="mt-2 rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {sendingTestFor === row.id ? 'Envoi...' : 'Tester WhatsApp'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
      {testMessage ? <p className="text-sm text-emerald-700">{testMessage}</p> : null}
    </div>
  )
}
