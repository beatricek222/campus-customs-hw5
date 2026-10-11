import { useEffect, useRef, useState } from 'react'
import { useAnimatedNumber } from '../hooks'
import { money } from '../derive'

interface Props {
  balance: number | null
  onReset: () => void
  resetting: boolean
  online: boolean
}

/** Brand + the checking balance "coin purse". The balance counts down smoothly and a −$ chip floats up after a payment. */
export default function Header({ balance, onReset, resetting, online }: Props) {
  const shown = useAnimatedNumber(balance)
  const prev = useRef<number | null>(balance)
  const [delta, setDelta] = useState<{ amount: number; id: number } | null>(null)
  const [confirm, setConfirm] = useState(false)

  useEffect(() => {
    if (balance !== null && prev.current !== null && balance !== prev.current) {
      setDelta({ amount: balance - prev.current, id: Date.now() })
      const t = setTimeout(() => setDelta(null), 2600)
      prev.current = balance
      return () => clearTimeout(t)
    }
    prev.current = balance
  }, [balance])

  return (
    <header className="topbar glass">
      <div className="brand">
        <div className="crest" aria-hidden="true"><span>C</span></div>
        <div>
          <h1>Campus Customs Desk</h1>
          <p>Your AI team, working the tickets <span className={`dot ${online ? 'on' : 'off'}`} title={online ? 'Backend connected' : 'Backend offline'} /></p>
        </div>
      </div>

      <div className="purse" aria-live="polite">
        <div className="purse-label">Checking balance</div>
        <div className={`purse-amount ${delta && delta.amount < 0 ? 'dropping' : ''}`}>
          {shown === null ? '···' : money(shown)}
        </div>
        {delta && (
          <span key={delta.id} className={`flyout ${delta.amount < 0 ? 'neg' : 'pos'}`}>
            {delta.amount < 0 ? '−' : '+'}{money(Math.abs(delta.amount))}
          </span>
        )}
        <span className="purse-shine" />
      </div>

      <div className="reset">
        {!confirm ? (
          <button className="btn ghost" disabled={resetting} onClick={() => setConfirm(true)}>↺ Reset desk</button>
        ) : (
          <span className="confirm-inline">
            Start fresh?
            <button className="btn small danger" onClick={() => { setConfirm(false); onReset() }}>Yes, reset</button>
            <button className="btn small ghost" onClick={() => setConfirm(false)}>Cancel</button>
          </span>
        )}
      </div>
    </header>
  )
}
