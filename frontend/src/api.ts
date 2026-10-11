import type { AgentEvent, Cash, EventsResponse, RunStatus, Ticket } from './types'

export const BASE = 'http://localhost:8000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* keep statusText */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const getTickets = () => call<Ticket[]>('/api/tickets')
export const getCash = () => call<Cash>('/api/cash')
export const runTicket = (id: number) => call<RunStatus>(`/api/tickets/${id}/run`, { method: 'POST' })
export const getRun = (runId: string) => call<RunStatus>(`/api/runs/${runId}`)
export const getEvents = (runId: string, after: number) =>
  call<EventsResponse>(`/api/events?run_id=${runId}&after=${after}&limit=500`)
export const approvePayment = (id: number, approvedBy: string) =>
  call<{ new_balance: number; payment: { amount: number } }>(`/api/tickets/${id}/approve-payment`, {
    method: 'POST',
    body: JSON.stringify({ approved_by: approvedBy }),
  })
export const resolveTicket = (id: number, approvedBy: string) =>
  call<{ ticket_status: string }>(`/api/tickets/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ approved_by: approvedBy }),
  })
export const resetDesk = () => call<{ reset: boolean }>('/api/reset', { method: 'POST' })

export type { AgentEvent }
