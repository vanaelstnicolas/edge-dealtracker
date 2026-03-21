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
  method?: 'GET' | 'PUT' | 'POST' | 'PATCH'
  body?: unknown
  isFormData?: boolean
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'
const requestTimeoutMs = 12000

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null
  const accessToken = session?.access_token
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
      throw new Error(`Delai depasse (${requestTimeoutMs / 1000}s) pour ${path}`)
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

export async function fetchUsers(): Promise<UserMapping[]> {
  const rows = await request<ApiUserMapping[]>('/settings/users')
  return rows.map((row) => ({
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    whatsappNumber: row.whatsapp_number ?? '',
  }))
}

export async function updateUserWhatsapp(userId: string, whatsappNumber: string): Promise<UserMapping> {
  const row = await request<ApiUserMapping>(`/settings/users/${userId}`, {
    method: 'PUT',
    body: { whatsapp_number: whatsappNumber },
  })
  return {
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    whatsappNumber: row.whatsapp_number ?? '',
  }
}

export async function fetchDeals(): Promise<Deal[]> {
  const [deals, users] = await Promise.all([
    request<ApiDeal[]>('/deals'),
    request<ApiUserMapping[]>('/settings/users'),
  ])

  const ownerById = new Map(users.map((user) => [user.id, user.full_name]))
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
  description: string
  action: string
  deadline: string
  status: DealStatus
  ownerId: string
}

export async function updateDeal(dealId: string, payload: DealUpdatePayload): Promise<void> {
  await request<ApiDeal>(`/deals/${dealId}`, {
    method: 'PATCH',
    body: {
      description: payload.description,
      action: payload.action,
      deadline: payload.deadline,
      status: payload.status,
      owner_id: payload.ownerId,
    },
  })
}

export function importDealsFromExcel(file: File): Promise<DealImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request<DealImportResult>('/deals/import/excel', {
    method: 'POST',
    body: formData,
    isFormData: true,
  })
}
