import type { Deal, UserMapping } from '../types/deal'

export const mockDeals: Deal[] = [
  {
    id: 'DL-001',
    company: 'Nova Industrie',
    description: 'Renouvellement audit organisationnel',
    action: 'Envoyer proposition finale',
    deadline: '2026-03-24',
    ownerId: 'u-1',
    owner: 'Nicolas Ferrand',
    status: 'active',
  },
  {
    id: 'DL-002',
    company: 'Atelier Horizon',
    description: 'Accompagnement PMO 6 mois',
    action: 'Préparer atelier de cadrage',
    deadline: '2026-03-19',
    ownerId: 'u-2',
    owner: 'Claire Dubois',
    status: 'active',
  },
  {
    id: 'DL-003',
    company: 'Groupe Altis',
    description: 'Mission transformation CRM',
    action: 'Dossier clôturé',
    deadline: '2026-03-10',
    ownerId: 'u-1',
    owner: 'Nicolas Ferrand',
    status: 'won',
  },
  {
    id: 'DL-004',
    company: 'Sirius Retail',
    description: 'Refonte du process avant-vente',
    action: 'Dossier clôturé',
    deadline: '2026-03-07',
    ownerId: 'u-3',
    owner: 'Julien Martin',
    status: 'lost',
  },
]

export const mockMappings: UserMapping[] = [
  {
    id: 'u-1',
    fullName: 'Nicolas Ferrand',
    email: 'nicolas@edge-consulting.fr',
    whatsappNumber: '+33612345678',
  },
  {
    id: 'u-2',
    fullName: 'Claire Dubois',
    email: 'claire@edge-consulting.fr',
    whatsappNumber: '+33622334455',
  },
]
