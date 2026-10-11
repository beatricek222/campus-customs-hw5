import type { AgentEvent, RoleKey } from './types'
import { AGENTS } from './agents'

export type AgentState = 'idle' | 'thinking' | 'tool' | 'waiting' | 'speaking' | 'done' | 'error' | 'unused'
export interface AgentStatus { state: AgentState; label: string }

/** Replay the event stream to learn what each agent is doing right now. */
export function deriveStatuses(events: AgentEvent[], runFinished: boolean): Record<RoleKey, AgentStatus> {
  const out = Object.fromEntries(AGENTS.map((a) => [a.key, { state: 'idle', label: 'Standing by' }])) as Record<RoleKey, AgentStatus>
  const active: Record<string, number> = {}
  for (const e of events) {
    const k = e.agent as RoleKey
    if (!out[k]) continue
    if (e.event === 'run_start') {
      active[k] = (active[k] ?? 0) + 1
      out[k] = { state: 'thinking', label: 'Reading the request' }
    } else if (e.event === 'model_request') {
      out[k] = { state: 'thinking', label: e.tool_results.length ? 'Reading results' : 'Thinking' }
    } else if (e.event === 'model_response') {
      const call = e.tool_calls[0]
      if (call?.delegates_to) out[k] = { state: 'waiting', label: `Asking ${prettyRole(call.delegates_to)}` }
      else if (call) out[k] = { state: 'tool', label: `Using ${call.tool}` }
      else out[k] = { state: 'speaking', label: 'Writing the answer' }
    } else if (e.event === 'run_end') {
      active[k] = Math.max(0, (active[k] ?? 1) - 1)
      if (active[k] === 0) out[k] = { state: 'done', label: 'Finished' }
    } else if (e.event === 'run_error') {
      out[k] = { state: 'error', label: 'Hit a problem' }
    }
  }
  if (runFinished) {
    for (const a of AGENTS) if (out[a.key].state === 'idle') out[a.key] = { state: 'unused', label: 'Not needed here' }
  }
  return out
}

export const prettyRole = (key: string) => AGENTS.find((a) => a.key === key)?.name ?? key

// ---------------------------------------------------------------- feed
export type FeedItem =
  | { kind: 'start'; key: string; agent: string; text: string }
  | { kind: 'say'; key: string; agent: string; text: string }
  | { kind: 'tool'; key: string; agent: string; tool: string; args: Record<string, unknown>; done: boolean; result?: string; failed?: boolean }
  | { kind: 'delegate'; key: string; from: string; to: string; task: string; childRun?: string; reply?: string }
  | { kind: 'final'; key: string; agent: string; text: string }
  | { kind: 'error'; key: string; agent: string; text: string }

const stripPrefix = (task: string) => task.replace(/^Delegated by [^\n]*:\n/, '')

/** Turn raw audit events into the conversation the board shows. */
export function buildFeed(events: AgentEvent[]): FeedItem[] {
  const items: FeedItem[] = []
  const byCall = new Map<string, FeedItem>()
  const byChild = new Map<string, Extract<FeedItem, { kind: 'delegate' }>>()
  for (const e of events) {
    const key = `e${e.index}`
    if (e.event === 'run_start') {
      if (e.depth === 0) {
        items.push({ kind: 'start', key, agent: e.agent, text: 'Ticket received. Reading it and deciding who to call.' })
      } else {
        const pending = [...items].reverse().find(
          (i): i is Extract<FeedItem, { kind: 'delegate' }> => i.kind === 'delegate' && i.to === e.agent && !i.childRun)
        if (pending) { pending.childRun = e.run_id; byChild.set(e.run_id, pending) }
      }
    } else if (e.event === 'model_response') {
      // text that comes with tool calls is the agent thinking out loud; a bare final answer is shown by run_end
      if (e.said && e.tool_calls.length > 0) items.push({ kind: 'say', key: key + 's', agent: e.agent, text: e.said })
      e.tool_calls.forEach((c, i) => {
        const k = `${key}c${i}`
        if (c.delegates_to) {
          const item: FeedItem = { kind: 'delegate', key: k, from: e.agent, to: c.delegates_to, task: String(c.args.task ?? '') }
          items.push(item); if (c.id) byCall.set(c.id, item)
        } else {
          const item: FeedItem = { kind: 'tool', key: k, agent: e.agent, tool: c.tool, args: c.args, done: false }
          items.push(item); if (c.id) byCall.set(c.id, item)
        }
      })
    } else if (e.event === 'model_request') {
      for (const r of e.tool_results) {
        const item = r.id ? byCall.get(r.id) : undefined
        if (item?.kind === 'tool') {
          item.done = true
          item.result = r.content ?? r.error
          item.failed = Boolean(r.error) || /"error"\s*:/.test(r.content ?? '')
        }
      }
    } else if (e.event === 'run_end') {
      const d = byChild.get(e.run_id)
      if (d) d.reply = e.said ?? undefined
      else items.push({ kind: 'final', key, agent: e.agent, text: e.said ?? 'Done.' })
    } else if (e.event === 'run_error') {
      items.push({ kind: 'error', key, agent: e.agent, text: e.error ?? 'Something went wrong.' })
    }
  }
  return items
}

// ---------------------------------------------------------------- summaries
export interface AgentSummary {
  role: RoleKey
  involved: boolean
  summary?: string
  tools: Record<string, number>
  delegatedTo: string[]
  actions: string[]
  extra?: string
}

/** One concise card per agent: what it concluded, which tools it used, what it changed. */
export function summarize(events: AgentEvent[]): AgentSummary[] {
  return AGENTS.map((a) => {
    const mine = events.filter((e) => e.agent === a.key)
    const tools: Record<string, number> = {}
    const delegatedTo: string[] = []
    for (const e of mine) for (const c of e.tool_calls) {
      if (c.delegates_to) { if (!delegatedTo.includes(c.delegates_to)) delegatedTo.push(c.delegates_to) }
      else tools[c.tool] = (tools[c.tool] ?? 0) + 1
    }
    const end = [...mine].reverse().find((e) => e.event === 'run_end')
    const out = end?.output ?? undefined
    const actions: string[] = Array.isArray(out?.actions_taken) ? out!.actions_taken : []
    let extra: string | undefined
    if (a.key === 'boss' && out) {
      extra = out.cash_plan
    }
    return { role: a.key, involved: mine.length > 0, summary: end?.said ?? undefined, tools, delegatedTo, actions, extra }
  })
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
