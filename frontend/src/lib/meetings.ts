import { supabase } from './supabase'

type RequestOptions = {
  method?: 'GET' | 'POST'
  body?: unknown
  isFormData?: boolean
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

export type MeetingAction = {
  operation: 'create' | 'update' | 'close' | 'ignore'
  company: string
  description: string
  action: string
  deadline: string
  status: '' | 'won' | 'lost'
  reason: string
  confidence: number
  selected?: boolean
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null
  const accessToken = session?.access_token

  const response = await fetch(`${apiBaseUrl}${path}`, {
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
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `API error (${response.status})`)
  }

  return (await response.json()) as T
}

export async function extractMeetingActions(content: string): Promise<MeetingAction[]> {
  const payload = await request<{ actions: MeetingAction[] }>('/meetings/extract', {
    method: 'POST',
    body: { content },
  })
  return payload.actions.map((item) => ({ ...item, selected: item.operation !== 'ignore' }))
}

export async function extractMeetingActionsFromFile(file: File): Promise<MeetingAction[]> {
  const formData = new FormData()
  formData.append('file', file)

  const payload = await request<{ actions: MeetingAction[] }>('/meetings/extract/file', {
    method: 'POST',
    body: formData,
    isFormData: true,
  })
  return payload.actions.map((item) => ({ ...item, selected: item.operation !== 'ignore' }))
}

export async function applyMeetingActions(actions: MeetingAction[], dryRun = false): Promise<{ created: number; updated: number; closed: number; ignored: number; failed: number }> {
  const payload = await request<{ created: number; updated: number; closed: number; ignored: number; failed: number }>('/meetings/apply', {
    method: 'POST',
    body: {
      actions: actions.map(({ selected, ...item }) => item),
      dry_run: dryRun,
    },
  })
  return payload
}
