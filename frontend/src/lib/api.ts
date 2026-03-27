import type { Deal, DealStatus, UserMapping } from '../types/deal'
import { supabase } from './supabase'

type ApiDeal = {
  id: string
  company: string
  description: string
  action: string
  deadline: string
  owner_id: string
  status: DealStatus
}

type ApiUserMapping = {
  id: string
  full_name: string
  email: string
  whatsapp_number: string | null
}

type RequestOptions = {
  method?: 'GET' | 'PUT' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  isFormData?: boolean
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'
const requestTimeoutMs = 30000
const getCacheTtlMs = 30000
const getCache = new Map<string, { expiresAt: number; data: unknown }>()
const inflightGetRequests = new Map<string, Promise<unknown>>()

function cacheKey(path: string, accessToken: string | undefined): string {
  return `${accessToken ?? 'anon'}::${path}`
}

function toDisplayName(email: string, fullName: string): string {
  const preferred = fullName.trim()
  if (preferred) {
    return preferred
  }

  const localPart = email.split('@')[0]?.trim() ?? ''
  if (!localPart) {
    return email
  }

  const token = localPart.split(/[._-]/)[0]?.trim() ?? localPart
  if (!token) {
    return localPart
  }
  return token.charAt(0).toUpperCase() + token.slice(1)
}

function invalidateGetCache(prefixes: string[]): void {
  for (const key of getCache.keys()) {
    if (prefixes.some((prefix) => key.endsWith(`::${prefix}`))) {
      getCache.delete(key)
    }
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null
  const accessToken = session?.access_token
  const method = options.method ?? 'GET'

  if (method === 'GET') {
    const key = cacheKey(path, accessToken)
    const cached = getCache.get(key)
    if (cached && cached.expiresAt > Date.now()) {
      return cached.data as T
    }

    const inflight = inflightGetRequests.get(key)
    if (inflight) {
      return (await inflight) as T
    }

    const pending = performRequest<T>(path, options, accessToken).then((result) => {
      getCache.set(key, { expiresAt: Date.now() + getCacheTtlMs, data: result })
      return result
    })
    inflightGetRequests.set(key, pending as Promise<unknown>)
    try {
      return await pending
    } finally {
      inflightGetRequests.delete(key)
    }
  }

  return performRequest<T>(path, options, accessToken)
}

async function performRequest<T>(path: string, options: RequestOptions, accessToken: string | undefined): Promise<T> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs)

  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      method: options.method ?? 'GET',
      headers: {
        ...(options.isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: options.body
        ? options.isFormData
          ? (options.body as FormData)
          : JSON.stringify(options.body)
        : undefined,
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error("La requete prend plus de temps que prevu. Reessaie dans quelques secondes.")
    }
    if (error instanceof TypeError) {
      throw new Error("Impossible de contacter le serveur pour le moment. Verifie ta connexion et reessaie.")
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `API error (${response.status})`)
  }

  return (await response.json()) as T
}

type DealImportResult = {
  imported: number
  skipped: number
  errors: string[]
}

export type DealScope = 'all' | 'active' | 'archived'

export type ActionSummaryItem = {
  company: string
  action: string
  deadline: string
  status: string
}

export type MyActionSummary = {
  ownerId: string
  ownerName: string
  summary: string
  items: ActionSummaryItem[]
}

export async function fetchUsers(): Promise<UserMapping[]> {
  const rows = await request<ApiUserMapping[]>('/settings/users')
  return rows.map((row) => ({
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    whatsappNumber: row.whatsapp_number ?? '',
  }))
}

export async function updateUserProfile(userId: string, payload: { fullName: string; whatsappNumber: string }): Promise<UserMapping> {
  const row = await request<ApiUserMapping>(`/settings/users/${userId}`, {
    method: 'PUT',
    body: { full_name: payload.fullName, whatsapp_number: payload.whatsappNumber },
  })
  invalidateGetCache(['/settings/users', '/deals'])
  return {
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    whatsappNumber: row.whatsapp_number ?? '',
  }
}

export async function sendWhatsappTest(userId: string): Promise<{ messageSid: string }> {
  const row = await request<{ result: string; message_sid: string }>(`/settings/users/${userId}/whatsapp/test`, {
    method: 'POST',
  })
  return { messageSid: row.message_sid }
}

export async function fetchDeals(scope: DealScope = 'all'): Promise<Deal[]> {
  const dealsPath = scope === 'all' ? '/deals' : `/deals?scope=${scope}`
  const [deals, users] = await Promise.all([
    request<ApiDeal[]>(dealsPath),
    request<ApiUserMapping[]>('/settings/users'),
  ])

  const ownerById = new Map(users.map((user) => [user.id, toDisplayName(user.email, user.full_name)]))
  return deals.map((deal) => ({
    id: deal.id,
    company: deal.company,
    description: deal.description,
    action: deal.action,
    deadline: deal.deadline,
    ownerId: deal.owner_id,
    owner: ownerById.get(deal.owner_id) ?? deal.owner_id,
    status: deal.status,
  }))
}

type DealUpdatePayload = {
  description?: string
  action?: string
  deadline?: string
  status?: DealStatus
  ownerId?: string
}

type DealCreatePayload = {
  company: string
  description: string
  action: string
  deadline: string
}

export async function createDeal(payload: DealCreatePayload): Promise<void> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null
  const ownerId = session?.user?.id
  if (!ownerId) {
    throw new Error('Session introuvable pour creer un dossier')
  }

  await request<ApiDeal>('/deals', {
    method: 'POST',
    body: {
      company: payload.company,
      description: payload.description,
      action: payload.action,
      deadline: payload.deadline,
      owner_id: ownerId,
      status: 'active',
    },
  })
  invalidateGetCache(['/deals', '/dashboard/kpis', '/summary/me'])
}

export async function updateDeal(dealId: string, payload: DealUpdatePayload): Promise<void> {
  const body: Record<string, unknown> = {}
  if (payload.description !== undefined) {
    body.description = payload.description
  }
  if (payload.action !== undefined) {
    body.action = payload.action
  }
  if (payload.deadline !== undefined) {
    body.deadline = payload.deadline
  }
  if (payload.status !== undefined) {
    body.status = payload.status
  }
  if (payload.ownerId !== undefined) {
    body.owner_id = payload.ownerId
  }

  await request<ApiDeal>(`/deals/${dealId}`, {
    method: 'PATCH',
    body,
  })
  invalidateGetCache(['/deals', '/dashboard/kpis', '/summary/me'])
}

export async function deleteDeal(dealId: string): Promise<void> {
  await request<{ result: string }>(`/deals/${dealId}`, {
    method: 'DELETE',
  })
  invalidateGetCache(['/deals', '/dashboard/kpis', '/summary/me'])
}

export async function fetchMyActionSummary(): Promise<MyActionSummary> {
  const row = await request<{
    owner_id: string
    owner_name: string
    summary: string
    items: ActionSummaryItem[]
  }>('/summary/me')
  return {
    ownerId: row.owner_id,
    ownerName: row.owner_name,
    summary: row.summary,
    items: row.items,
  }
}

export async function sendMyActionSummary(): Promise<{ whatsapp: string; email: string; summary: string }> {
  const row = await request<{ whatsapp: string; email: string; summary: string }>('/summary/me/send', {
    method: 'POST',
  })
  return row
}

export function importDealsFromExcel(file: File): Promise<DealImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request<DealImportResult>('/deals/import/excel', {
    method: 'POST',
    body: formData,
    isFormData: true,
  }).then((result) => {
    invalidateGetCache(['/deals'])
    return result
  })
}

export function prefetchCoreData(): void {
  void fetchDeals()
  void fetchUsers()
}
