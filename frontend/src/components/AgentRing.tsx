import { useEffect, useRef, useState } from 'react'
import { AGENTS, agentOf } from '../agents'
import type { AgentEvent, RoleKey } from '../types'
import type { AgentStatus } from '../derive'

interface Props {
  statuses: Record<RoleKey, AgentStatus>
  events: AgentEvent[]
}

interface Pulse { id: string; from: RoleKey; to: RoleKey; kind: 'ask' | 'reply' }

const pairs = AGENTS.flatMap((a, i) => AGENTS.slice(i + 1).map((b) => [a, b] as const))

/** The five agents on a ring, all linked (full connectivity). Messages fly along the lines as agents delegate and report back. */
export default function AgentRing({ statuses, events }: Props) {
  const [pulses, setPulses] = useState<Pulse[]>([])
  const seen = useRef(-1)
  const runAgent = useRef(new Map<string, RoleKey>())

  useEffect(() => {
    const fresh: Pulse[] = []
    for (const e of events) {
      if (e.event === 'run_start') runAgent.current.set(e.run_id, e.agent as RoleKey)
      if (e.index <= seen.current) continue
      if (e.event === 'model_response') {
        for (const c of e.tool_calls) if (c.delegates_to) fresh.push({ id: `${e.index}-${c.tool}`, from: e.agent as RoleKey, to: c.delegates_to as RoleKey, kind: 'ask' })
      } else if (e.event === 'run_end' && e.parent_run_id) {
        const parent = runAgent.current.get(e.parent_run_id)
        if (parent) fresh.push({ id: `${e.index}-back`, from: e.agent as RoleKey, to: parent, kind: 'reply' })
      }
    }
    if (events.length) seen.current = events[events.length - 1].index
    if (events.length === 0) { seen.current = -1; runAgent.current.clear() }
    if (fresh.length) {
      setPulses((p) => [...p, ...fresh])
      // not cleared on re-render: polling replaces `events` every second and must not cancel this clean-up
      setTimeout(() => setPulses((p) => p.filter((x) => !fresh.includes(x))), 1700)
    }
  }, [events])

  const active = new Set(pulses.map((p) => [p.from, p.to].sort().join('|')))

  return (
    <div className="ring">
      <svg className="ring-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {pairs.map(([a, b]) => (
          <line key={a.key + b.key} x1={a.pos.x} y1={a.pos.y} x2={b.pos.x} y2={b.pos.y}
            className={active.has([a.key, b.key].sort().join('|')) ? 'lit' : ''} vectorEffect="non-scaling-stroke" />
        ))}
        {pulses.map((p) => {
          const f = agentOf(p.from).pos, t = agentOf(p.to).pos
          return (
            <circle key={p.id} r="1.6" className={`pulse ${p.kind}`} fill={agentOf(p.from).color}>
              <animate attributeName="cx" from={f.x} to={t.x} dur="1.2s" fill="freeze" calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1" />
              <animate attributeName="cy" from={f.y} to={t.y} dur="1.2s" fill="freeze" calcMode="spline" keySplines=".4 0 .2 1" keyTimes="0;1" />
            </circle>
          )
        })}
      </svg>

      {AGENTS.map((a) => {
        const s = statuses[a.key]
        return (
          <div key={a.key} className={`node ${s.state}`} style={{ left: `${a.pos.x}%`, top: `${a.pos.y}%`, ['--accent' as string]: a.color }}>
            <div className="avatar">
              <span className="ripple r1" /><span className="ripple r2" />
              {a.icon}
              {s.state === 'done' && <span className="mini-check">✓</span>}
            </div>
            <div className="node-name">{a.name}</div>
            <div className="node-state" title={s.label}>
              {(s.state === 'thinking' || s.state === 'waiting') && <span className="typing"><i /><i /><i /></span>}
              {s.label}
            </div>
          </div>
        )
      })}
    </div>
  )
}
