export type RoleKey = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface PendingPayment {
  kind: 'invoice' | 'rent'
  ref_id: number
  amount: number
  payee: string
  due_date: string
  already_paid: boolean
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  status: string
  state: 'open' | 'resolved'
  awaiting_approval: boolean
  notes: string | null
  created_at: string
  pending_payment: PendingPayment | null
  run_status: 'idle' | 'running'
  last_run_id: string | null
}

export interface RunStatus {
  run_id: string
  ticket_id: number
  status: 'running' | 'done' | 'error'
  started_at: string
  finished_at: string | null
  result: Record<string, any> | null
  error: string | null
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
  id?: string | null
  delegates_to?: string
}

export interface ToolResult {
  tool: string | null
  id?: string | null
  content?: string
  error?: string
}

export interface AgentEvent {
  index: number
  timestamp: string
  root_run_id: string
  run_id: string
  parent_run_id: string | null
  depth: number
  agent: string
  step: number
  event: string
  task: string | null
  said: string | null
  tool_calls: ToolCall[]
  tool_results: ToolResult[]
  error: string | null
  output: Record<string, any> | null
  usage: Record<string, number>
}

export interface EventsResponse {
  total: number
  next_after: number
  events: AgentEvent[]
}

export interface Cash {
  checking: number
  as_of: string
}
