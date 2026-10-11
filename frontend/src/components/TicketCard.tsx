import { useRef } from 'react'
import type { Ticket } from '../types'
import { money } from '../derive'

const TYPE_LABEL: Record<string, { label: string; icon: string }> = {
  customer_order: { label: 'Customer order', icon: '🛍️' },
  rent_notice: { label: 'Rent notice', icon: '🏠' },
  price_override: { label: 'Price request', icon: '🏷️' },
}

export type Badge = { text: string; cls: string }
export function badgeFor(t: Ticket): Badge {
  if (t.run_status === 'running') return { text: 'Agents working', cls: 'working' }
  if (t.state === 'resolved') return { text: 'Resolved', cls: 'resolved' }
  if (t.awaiting_approval) return { text: 'Needs your approval', cls: 'needs' }
  if (t.status === 'escalated') return { text: 'Escalated', cls: 'needs' }
  return { text: 'Open', cls: 'open' }
}

interface Props {
  ticket: Ticket
  selected: boolean
  onSelect: () => void
  onRun: () => void
  disabled: boolean
}

export default function TicketCard({ ticket: t, selected, onSelect, onRun, disabled }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const badge = badgeFor(t)
  const meta = TYPE_LABEL[t.type] ?? { label: t.type, icon: '📄' }

  // gentle 3-D tilt that follows the pointer
  const onMove = (e: React.MouseEvent) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width - 0.5
    const y = (e.clientY - r.top) / r.height - 0.5
    el.style.setProperty('--ry', `${x * 7}deg`)
    el.style.setProperty('--rx', `${-y * 7}deg`)
    el.style.setProperty('--mx', `${(x + 0.5) * 100}%`)
    el.style.setProperty('--my', `${(y + 0.5) * 100}%`)
  }
  const onLeave = () => {
    const el = ref.current
    if (!el) return
    el.style.setProperty('--ry', '0deg'); el.style.setProperty('--rx', '0deg')
  }

  const canRun = t.state !== 'resolved' && t.run_status === 'idle' && !disabled
  return (
    <div
      ref={ref}
      className={`ticket glass ${selected ? 'selected' : ''} ${badge.cls}`}
      onClick={onSelect}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect() } }}
    >
      <div className="ticket-glow" />
      <div className="ticket-head">
        <span className="ticket-icon">{meta.icon}</span>
        <div className="ticket-title">
          <small>#{t.id} · {meta.label}</small>
          <strong>{t.subject}</strong>
        </div>
        <span className={`badge ${badge.cls}`}>
          {badge.cls === 'resolved' && <svg viewBox="0 0 24 24" width="14" height="14"><path className="tick" d="M5 13l4 4L19 7" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>}
          {badge.cls === 'working' && <i className="spinner" />}
          {badge.text}
        </span>
      </div>
      <p className="ticket-who">{t.requester}</p>
      <p className="ticket-notes">{t.notes?.split('\n')[0]}</p>
      <div className="ticket-foot">
        {t.sku && <span className="chip">{t.qty ?? 1} × {t.sku} {t.size}</span>}
        {t.pending_payment && !t.pending_payment.already_paid && (
          <span className="chip pay">{money(t.pending_payment.amount)} {t.pending_payment.kind === 'rent' ? 'rent' : 'invoice'}</span>
        )}
        <span className="spacer" />
        <button
          className="btn primary small"
          disabled={!canRun}
          onClick={(e) => { e.stopPropagation(); onSelect(); onRun() }}
        >
          {t.run_status === 'running' ? 'Running…' : t.state === 'resolved' ? 'Done' : '▶ Run team'}
        </button>
      </div>
    </div>
  )
}
