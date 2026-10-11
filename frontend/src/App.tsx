import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as api from './api'
import type { AgentEvent, RunStatus, Ticket } from './types'
import { buildFeed, deriveStatuses, summarize } from './derive'
import { useInterval } from './hooks'
import { fireConfetti } from './confetti'
import Header from './components/Header'
import TicketCard, { badgeFor } from './components/TicketCard'
import AgentRing from './components/AgentRing'
import Feed from './components/Feed'
import SummaryPanel from './components/SummaryPanel'
import ApprovalCard from './components/ApprovalCard'

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [balance, setBalance] = useState<number | null>(null)
  // ?ticket=101 opens the board on that ticket (handy for screenshots and links)
  const [selectedId, setSelectedId] = useState<number | null>(() => Number(new URLSearchParams(window.location.search).get('ticket')) || null)
  const [events, setEvents] = useState<Record<string, AgentEvent[]>>({})
  const [runs, setRuns] = useState<Record<string, RunStatus>>({})
  const [online, setOnline] = useState(true)
  const [banner, setBanner] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [approveError, setApproveError] = useState<string | null>(null)
  const [resetting, setResetting] = useState(false)
  const prevState = useRef<Record<number, string>>({})
  const lastIndex = useRef<Record<string, number>>({})

  const selected = tickets.find((t) => t.id === selectedId) ?? null
  const runId = selected?.last_run_id ?? null
  const anyRunning = tickets.some((t) => t.run_status === 'running')

  // pick the first ticket once they load
  useEffect(() => { if (selectedId === null && tickets.length) setSelectedId(tickets[0].id) }, [tickets, selectedId])

  const refresh = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([api.getTickets(), api.getCash()])
      setOnline(true); setBanner(null)
      // celebrate a ticket that just became resolved (not on first load)
      for (const x of t) {
        if (prevState.current[x.id] && prevState.current[x.id] !== 'resolved' && x.state === 'resolved') {
          fireConfetti(window.innerWidth * 0.62, window.innerHeight * 0.35)
        }
        prevState.current[x.id] = x.state
      }
      setTickets(t); setBalance(c.checking)
      const sel = t.find((x) => x.id === selectedIdRef.current)
      const rid = sel?.last_run_id
      if (rid) {
        const run = await api.getRun(rid)
        setRuns((r) => ({ ...r, [rid]: run }))
        const after = lastIndex.current[rid] ?? -1
        const ev = await api.getEvents(rid, after)
        if (ev.events.length) {
          lastIndex.current[rid] = Math.max(lastIndex.current[rid] ?? -1, ev.events[ev.events.length - 1].index)
          // overlapping polls can return the same event twice, so merge by its unique index
          setEvents((e) => {
            const have = new Set((e[rid] ?? []).map((x) => x.index))
            return { ...e, [rid]: [...(e[rid] ?? []), ...ev.events.filter((x) => !have.has(x.index))].sort((a, b) => a.index - b.index) }
          })
        }
      }
    } catch {
      setOnline(false)
      setBanner('Can’t reach the backend at http://localhost:8000. Start it from the backend folder: uvicorn main:app --reload --port 8000')
    }
  }, [])

  const selectedIdRef = useRef<number | null>(null)
  selectedIdRef.current = selectedId

  useEffect(() => { refresh() }, [refresh, selectedId])
  useInterval(refresh, anyRunning ? 1000 : 2500)

  const evs = (runId && events[runId]) || []
  const run = runId ? runs[runId] : undefined
  const runFinished = run?.status === 'done' || run?.status === 'error'
  const statuses = useMemo(() => deriveStatuses(evs, Boolean(runFinished)), [evs, runFinished])
  const feed = useMemo(() => buildFeed(evs), [evs])
  const summaries = useMemo(() => summarize(evs), [evs])
  const bossOut = [...evs].reverse().find((e) => e.agent === 'boss' && e.event === 'run_end')?.output
  const recommendation: string | undefined = bossOut?.ticket_outcomes?.[0]?.decision

  const start = async (id: number) => {
    setBanner(null)
    try {
      const r = await api.runTicket(id)
      setRuns((x) => ({ ...x, [r.run_id]: r }))
      await refresh()
    } catch (e) { setBanner((e as Error).message) }
  }

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setApproveError(null)
    try { await fn(); await refresh() } catch (e) { setApproveError((e as Error).message) } finally { setBusy(false) }
  }

  const reset = async () => {
    setResetting(true)
    try {
      await api.resetDesk()
      setEvents({}); setRuns({}); lastIndex.current = {}; prevState.current = {}
      await refresh()
    } catch (e) { setBanner((e as Error).message) } finally { setResetting(false) }
  }

  const badge = selected ? badgeFor(selected) : null
  const needsHuman = selected && selected.awaiting_approval && selected.run_status === 'idle'

  return (
    <div className="app">
      <div className="bubbles" aria-hidden="true">
        {Array.from({ length: 9 }, (_, i) => <span key={i} className={`bg-bubble b${i}`} />)}
      </div>

      <Header balance={balance} onReset={reset} resetting={resetting} online={online} />
      {banner && <div className="banner glass">{banner}</div>}

      <main className="layout">
        <aside className="tickets">
          <h2 className="section-title">Tickets <small>{tickets.filter((t) => t.state === 'resolved').length}/{tickets.length} resolved</small></h2>
          {tickets.map((t, i) => (
            <div key={t.id} className="enter" style={{ animationDelay: `${i * 90}ms` }}>
              <TicketCard ticket={t} selected={t.id === selectedId} onSelect={() => setSelectedId(t.id)}
                onRun={() => start(t.id)} disabled={anyRunning} />
            </div>
          ))}
          {tickets.length === 0 && online && <div className="glass skeleton">Loading tickets…</div>}
        </aside>

        <section className="detail">
          {selected ? (
            <>
              <div className={`detail-head glass ${badge?.cls}`}>
                <div>
                  <small>Ticket #{selected.id}</small>
                  <h2>{selected.subject} <span className="muted-name">· {selected.requester}</span></h2>
                </div>
                <span className={`badge big ${badge?.cls}`}>{badge?.text}</span>
                {selected.state === 'resolved' && (
                  <svg className="big-check" viewBox="0 0 52 52" aria-hidden="true">
                    <circle cx="26" cy="26" r="23" fill="none" strokeWidth="3" />
                    <path d="M15 27l8 8 15-17" fill="none" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>

              <div className="detail-grid">
                <div className="col-left">
                  <div className="glass panel">
                    <h3 className="panel-title">The team</h3>
                    <AgentRing statuses={statuses} events={evs} />
                  </div>

                  {needsHuman && (
                    <ApprovalCard key={selected.id} ticket={selected} recommendation={recommendation} busy={busy} error={approveError}
                      onApprove={(n) => act(() => api.approvePayment(selected.id, n))}
                      onResolve={(n) => act(() => api.resolveTicket(selected.id, n))} />
                  )}
                </div>

                <div className="col-right">
                  <div className="glass panel feed-panel">
                    <h3 className="panel-title">Live conversation {run?.status === 'running' && <span className="live">LIVE</span>}</h3>
                    <Feed items={feed} running={run?.status === 'running'} />
                  </div>
                </div>
              </div>

              {(evs.length > 0 || runFinished) && (
                <div className="panel-wrap">
                  <h3 className="panel-title plain">What each agent did</h3>
                  <SummaryPanel summaries={summaries} finished={Boolean(runFinished)} />
                  {run?.status === 'error' && <p className="err">The run stopped: {run.error}</p>}
                </div>
              )}
            </>
          ) : <div className="glass skeleton">Pick a ticket</div>}
        </section>
      </main>
    </div>
  )
}
