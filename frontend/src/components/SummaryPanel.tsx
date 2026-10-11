import type { AgentSummary } from '../derive'
import { prettyRole } from '../derive'
import { agentOf } from '../agents'

/** One concise card per agent: what it concluded, who it asked, which tools it used, what it changed. */
export default function SummaryPanel({ summaries, finished }: { summaries: AgentSummary[]; finished: boolean }) {
  return (
    <div className="summaries">
      {summaries.map((s, i) => {
        const a = agentOf(s.role)
        const toolList = Object.entries(s.tools)
        return (
          <div key={s.role} className={`sum glass ${s.involved ? '' : 'muted'}`}
            style={{ ['--accent' as string]: a.color, animationDelay: `${i * 70}ms` }}>
            <div className="sum-head">
              <span className="mini-avatar">{a.icon}</span>
              <b>{a.name}</b>
              {!s.involved && finished && <em>Not needed on this ticket</em>}
              {!s.involved && !finished && <em>Waiting to be called</em>}
            </div>
            {s.involved && (
              <>
                <p className="sum-text">{s.summary ?? 'Working…'}</p>
                <div className="sum-meta">
                  {s.delegatedTo.length > 0 && <span className="pill">asked {s.delegatedTo.map(prettyRole).join(', ')}</span>}
                  {toolList.map(([t, n]) => <span key={t} className="pill tool-pill">{t}{n > 1 ? ` ×${n}` : ''}</span>)}
                </div>
                {s.actions.length > 0 && <ul className="sum-actions">{s.actions.map((x, k) => <li key={k}>{x}</li>)}</ul>}
                {s.extra && <p className="sum-extra"><b>Cash plan:</b> {s.extra}</p>}
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
