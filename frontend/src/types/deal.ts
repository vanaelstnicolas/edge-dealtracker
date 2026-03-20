export type DealStatus = 'active' | 'won' | 'lost'

export type Deal = {
  id: string
  company: string
  description: string
  action: string
  deadline: string
  owner: string
  status: DealStatus
}

export type UserMapping = {
  id: string
  fullName: string
  email: string
  whatsappNumber: string
}
