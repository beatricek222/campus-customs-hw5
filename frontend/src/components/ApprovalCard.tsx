import { useState } from 'react'
import type { Ticket } from '../types'
import { money } from '../derive'

interface Props {
  ticket: Ticket
  recommendation?: string
  busy: boolean
  error: string | null
  onApprove: (name: string) => void
  onResolve: (name: string) => void
}

const loadName = () => { try { return localStorage.getItem('cc-approver') ?? '' } catch { return '' } }

/** The human gate. Agents only prepare; nothing is paid until a named person confirms here. */
export default function ApprovalCard({ ticket, recommendation, busy, error, onApprove, onResolve }: Props) {
  const [name, setName] = useState(loadName)
  const [armed, setArmed] = useState(false)
  const pay = ticket.pending_payment && !ticket.pending_payment.already_paid ? ticket.pending_payment : null
  const ready = name.trim().length > 1

  const remember = (v: string) => { setName(v); try { localStorage.setItem('cc-approver', v) } catch { /* ignore */ } }
  const go = () => (pay ? onApprove(name.trim()) : onResolve(name.trim()))

  return (
    <div className="approval glass">
      <div className="approval-head">
        <span className="hand">✋</span>
        <div>
          <h3>{pay ? 'Payment ready for your approval' : 'A decision is waiting for you'}</h3>
          <p>The agents only prepared this. Nothing moves until you approve.</p>
        </div>
      </div>

      {pay ? (
        <div className="pay-box">
          <div className="pay-amount">{money(pay.amount)}</div>
          <div className="pay-meta">
            <span>{pay.kind === 'rent' ? 'Rent to' : 'Vendor invoice to'} <b>{pay.payee}</b></span>
            <span>Due {pay.due_date}</span>
          </div>
        </div>
      ) : (
        <div className="pay-box rec">
          <b>Team recommendation</b>
          <p>{recommendation ?? 'See the summaries below. Accepting records your decision on the ticket.'}</p>
        </div>
      )}

      <label className="field">
        <span>Your name</span>
        <input value={name} onChange={(e) => { remember(e.target.value); setArmed(false) }} placeholder="e.g. Beatrice" />
      </label>

      {error && <p className="err">{error}</p>}

      {!armed ? (
        <button className="btn primary big" disabled={!ready || busy} onClick={() => setArmed(true)}>
          {pay ? `Approve ${money(pay.amount)}` : 'Accept recommendation'}
        </button>
      ) : (
        <div className="confirm-row">
          <span>{pay ? `Pay ${money(pay.amount)} to ${pay.payee} as ${name.trim()}?` : `Resolve as ${name.trim()}?`}</span>
          <button className="btn primary" disabled={busy} onClick={go}>{busy ? 'Working…' : 'Yes, confirm'}</button>
          <button className="btn ghost" disabled={busy} onClick={() => setArmed(false)}>Back</button>
        </div>
      )}
    </div>
  )
}
