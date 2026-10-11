import type { ReactNode } from 'react'
import type { RoleKey } from './types'

export interface AgentMeta {
  key: RoleKey
  name: string
  tagline: string
  color: string   // accent used for the glow, bubble edge and avatar
  icon: ReactNode
  pos: { x: number; y: number } // position in the team ring, in percent
}

const svg = (d: ReactNode) => (
  <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true">{d}</svg>
)

export const AGENTS: AgentMeta[] = [
  {
    key: 'boss', name: 'Boss', tagline: 'Leads & decides', color: '#f4c95d', pos: { x: 50, y: 13 },
    icon: svg(<path d="M3 8l4.2 4L12 5l4.8 7L21 8l-2 11H5L3 8z" />),
  },
  {
    key: 'inventory', name: 'Inventory', tagline: 'Stock & prices', color: '#62d0ff', pos: { x: 87, y: 41 },
    icon: svg(<path d="M12 2l9 5v10l-9 5-9-5V7l9-5zm0 2.3L5.8 7.7 12 11.2l6.2-3.5L12 4.3zM5 9.4v6.9l6 3.3v-6.9L5 9.4zm14 0l-6 3.3v6.9l6-3.3V9.4z" />),
  },
  {
    key: 'accounting', name: 'Accounting', tagline: 'Cash & bills', color: '#6ee7b7', pos: { x: 73, y: 86 },
    icon: svg(<><circle cx="12" cy="12" r="9.5" /><text x="12" y="16.5" textAnchor="middle" fontSize="12.5" fontWeight="700" fill="#0b2a66">$</text></>),
  },
  {
    key: 'facilities', name: 'Facilities', tagline: 'Leases & rent', color: '#b8a9ff', pos: { x: 27, y: 86 },
    icon: svg(<path d="M4 21V5l8-3 8 3v16h-6v-5h-4v5H4zm4-14v2h2V7H8zm6 0v2h2V7h-2zm-6 4v2h2v-2H8zm6 0v2h2v-2h-2z" />),
  },
  {
    key: 'customer_service', name: 'Customer Service', tagline: 'Friendly replies', color: '#ff9db1', pos: { x: 13, y: 41 },
    icon: svg(<path d="M4 4h16a2 2 0 012 2v9a2 2 0 01-2 2H9l-5 4v-4a2 2 0 01-2-2V6a2 2 0 012-2z" />),
  },
]

export const AGENT_BY_KEY = Object.fromEntries(AGENTS.map((a) => [a.key, a])) as Record<string, AgentMeta>
export const agentOf = (key: string): AgentMeta => AGENT_BY_KEY[key] ?? AGENTS[0]
