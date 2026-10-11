import { useEffect, useRef, useState } from 'react'
import type { FeedItem } from '../derive'
import { agentOf } from '../agents'
import { prettyRole } from '../derive'

const short = (args: Record<string, unknown>) =>
  Object.entries(args).map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`).join(', ')

function Avatar({ role }: { role: string }) {
  const a = agentOf(role)
  return <span className="mini-avatar" style={{ ['--accent' as string]: a.color }}>{a.icon}</span>
}

function ToolChip({ item }: { item: Extract<FeedItem, { kind: 'tool' }> }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`tool ${item.done ? (item.failed ? 'failed' : 'done') : 'running'}`} onClick={() => setOpen((o) => !o)}>
      <span className="tool-state">{item.done ? (item.failed ? '!' : '✓') : <i className="spinner" />}</span>
      <code>{item.tool}</code>
      <span className="tool-args">{short(item.args)}</span>
      {open && item.result && <pre className="tool-result">{prettyJson(item.result)}</pre>}
    </div>
  )
}

function prettyJson(s: string) {
  try { return JSON.stringify(JSON.parse(s), null, 2) } catch { return s }
}

export default function Feed({ items, running }: { items: FeedItem[]; running: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, [items.length])

  if (items.length === 0) {
    return (
      <div className="empty">
        <div className="empty-orb" />
        <p>{running ? 'Waking up the team…' : 'Pick “Run team” and watch the agents talk it through here.'}</p>
      </div>
    )
  }

  return (
    <div className="feed">
      {items.map((it) => {
        switch (it.kind) {
          case 'start':
            return <div key={it.key} className="divider"><span>{it.text}</span></div>
          case 'say':
            return (
              <div key={it.key} className="row" style={{ ['--accent' as string]: agentOf(it.agent).color }}>
                <Avatar role={it.agent} />
                <div className="bubble said"><b>{prettyRole(it.agent)}</b>{it.text}</div>
              </div>
            )
          case 'tool':
            return (
              <div key={it.key} className="row" style={{ ['--accent' as string]: agentOf(it.agent).color }}>
                <Avatar role={it.agent} />
                <ToolChip item={it} />
              </div>
            )
          case 'delegate':
            return (
              <div key={it.key} className="delegate" style={{ ['--from' as string]: agentOf(it.from).color, ['--to' as string]: agentOf(it.to).color }}>
                <div className="delegate-head">
                  <Avatar role={it.from} /><span className="arrow">➜</span><Avatar role={it.to} />
                  <span><b>{prettyRole(it.from)}</b> asks <b>{prettyRole(it.to)}</b></span>
                </div>
                <p className="ask">{it.task}</p>
                {it.reply ? <p className="reply"><b>{prettyRole(it.to)} reports:</b> {it.reply}</p>
                  : <p className="reply waiting"><span className="typing"><i /><i /><i /></span> {prettyRole(it.to)} is working…</p>}
              </div>
            )
          case 'final':
            return (
              <div key={it.key} className="row" style={{ ['--accent' as string]: agentOf(it.agent).color }}>
                <Avatar role={it.agent} />
                <div className="bubble final"><b>{prettyRole(it.agent)} · final answer</b>{it.text}</div>
              </div>
            )
          case 'error':
            return <div key={it.key} className="bubble error"><b>{prettyRole(it.agent)}</b> {it.text}</div>
        }
      })}
      {running && <div className="row"><span className="typing big"><i /><i /><i /></span></div>}
      <div ref={end} />
    </div>
  )
}
