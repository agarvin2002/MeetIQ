import { useState, useEffect } from 'react'

const POLL = 60

export default function RefreshBar({ lastUpdated, onRefresh, loading }) {
  const [secs, setSecs] = useState(POLL)

  useEffect(() => {
    if (!lastUpdated) return
    setSecs(POLL)
    const t = setInterval(() => setSecs(s => (s <= 1 ? POLL : s - 1)), 1000)
    return () => clearInterval(t)
  }, [lastUpdated])

  const pct = ((POLL - secs) / POLL) * 100
  const r = 9
  const circ = 2 * Math.PI * r
  const dash = circ * (1 - pct / 100)

  return (
    <div className="flex items-center gap-2.5 flex-shrink-0">
      <span className="text-[12px] font-mono text-ink-300 whitespace-nowrap hidden sm:block">
        {lastUpdated
          ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · ${secs}s`
          : 'Loading…'}
      </span>

      {/* Countdown ring */}
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" className="flex-shrink-0">
        <circle cx="11" cy="11" r={r} stroke="#E5E8F2" strokeWidth="2.5" />
        <circle
          cx="11" cy="11" r={r}
          stroke="#5B6BF8" strokeWidth="2.5"
          strokeDasharray={circ}
          strokeDashoffset={dash}
          strokeLinecap="round"
          transform="rotate(-90 11 11)"
          style={{ transition: 'stroke-dashoffset 1s linear' }}
        />
      </svg>

      <button
        onClick={() => onRefresh()}
        disabled={loading}
        className="text-[13px] font-medium text-accent px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-indigo-50 hover:border-indigo-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm whitespace-nowrap"
      >
        {loading ? '…' : 'Refresh now'}
      </button>
    </div>
  )
}
