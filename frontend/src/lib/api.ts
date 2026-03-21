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
  method?: 'GET' | 'PUT'
  body?: unknown
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null
  const accessToken = session?.access_token

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method ?? 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `API error (${response.status})`)
  }

  return (await response.json()) as T
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
    owner: ownerById.get(deal.owner_id) ?? deal.owner_id,
    status: deal.status,
  }))
}
