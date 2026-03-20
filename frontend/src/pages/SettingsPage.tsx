import { useState } from 'react'
import { mockMappings } from '../lib/mock-data'

const e164Regex = /^\+[1-9]\d{6,14}$/

export function SettingsPage() {
  const [rows, setRows] = useState(mockMappings)

  return (
    <div className="space-y-5">
      <header>
        <h1 className="font-heading text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-slate-500">Mapping utilisateurs et numero WhatsApp (format E.164).</p>
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-[15px]">
            <thead className="bg-slate-50 text-sm text-slate-600">
              <tr>
                <th className="px-4 py-3 font-heading font-medium">Utilisateur</th>
                <th className="px-4 py-3 font-heading font-medium">Email</th>
                <th className="px-4 py-3 font-heading font-medium">WhatsApp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => {
                const valid = e164Regex.test(row.whatsappNumber)
                return (
                  <tr key={row.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{row.fullName}</td>
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
                        className={`w-full rounded-xl border px-3 py-2 text-sm outline-none ${
                          valid ? 'border-slate-200 focus:border-slate-400' : 'border-red-300 focus:border-red-500'
                        }`}
                      />
                      {!valid && <p className="mt-1 text-xs text-red-600">Format attendu: +33612345678</p>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
