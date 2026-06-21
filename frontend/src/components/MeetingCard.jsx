import { useState } from 'react'
import { formatTime, formatDate } from '../utils/time'

export default function MeetingCard({ meeting, onRefresh }) {
  const [collapsed, setCollapsed] = useState(false)
  const { brief } = meeting
  const urgency = getUrgency(meeting.start_time)

  return (
    <article className={`bg-surface rounded-2xl animate-card-enter ${urgency.shadow}`}>
      <div className="px-7 pt-[22px] pb-[18px]">

        {/* ── Header ───────────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-mono font-medium uppercase tracking-[0.07em] text-ink-300 mb-1.5">
              {formatDate(meeting.start_time)} · {formatTime(meeting.start_time)} – {formatTime(meeting.end_time)}
              {meeting.attendees?.[0] && <span className="ml-2">· {meeting.attendees[0]}</span>}
            </p>
            {/* THE EDITORIAL RISK: company name at headline scale */}
            <h2 className="text-[26px] font-bold tracking-tighter text-ink-900 leading-tight mb-1.5">
              {meeting.company_name}
            </h2>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[13px] text-ink-500">{meeting.title}</span>
              {meeting.company_domain && (
                <a
                  href={`https://${meeting.company_domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[12px] font-mono text-ink-300 bg-ground px-2 py-0.5 rounded"
                >
                  {meeting.company_domain}
                </a>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[12px] font-mono font-semibold ${urgency.badge}`}>
              {urgency.label}
            </span>
            {brief?.eval_score != null && <ScoreBadge score={brief.eval_score} />}
          </div>
        </div>

        <hr className="border-border my-4" />

        {/* ── Description ──────────────────────────────────────────── */}
        <p className="text-sm leading-relaxed text-ink-500">{brief.description}</p>

        {/* ── Expanded content ─────────────────────────────────────── */}
        {!collapsed && (
          <>
            <hr className="border-border my-4" />

            {/* Talking points */}
            {brief.talking_points?.length > 0 && (
              <div className="mb-4">
                <p className="text-[10px] font-mono font-bold uppercase tracking-[0.09em] text-ink-300 mb-2.5">
                  Talking Points
                </p>
                <ol className="flex flex-col gap-2.5">
                  {brief.talking_points.map((pt, i) => (
                    <li key={i} className="flex items-start gap-2.5">
                      <span className="w-5 h-5 rounded-full bg-accent text-white text-[11px] font-bold font-mono flex items-center justify-center flex-shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <span className="text-sm text-ink-900 leading-relaxed">{pt}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            <hr className="border-border my-4" />

            {/* News + Tech two-column */}
            <div className="grid grid-cols-2 gap-5 mb-4">
              {brief.recent_news?.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono font-bold uppercase tracking-[0.09em] text-ink-300 mb-2.5">Recent News</p>
                  <ul className="flex flex-col gap-1.5">
                    {brief.recent_news.map((item, i) => (
                      <li key={i} className="flex items-baseline gap-1.5 text-[13px] text-ink-500 leading-snug">
                        <span className="text-ink-300 flex-shrink-0">·</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {brief.tech_signals?.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono font-bold uppercase tracking-[0.09em] text-ink-300 mb-2.5">Tech Stack</p>
                  <div className="flex flex-wrap gap-1.5">
                    {brief.tech_signals.map((tech, i) => (
                      <span key={i} className="text-[12px] font-mono text-ink-700 bg-ground border border-border rounded px-2 py-0.5">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Pain points */}
            {brief.pain_points?.length > 0 && (
              <>
                <hr className="border-border my-4" />
                <div>
                  <p className="text-[10px] font-mono font-bold uppercase tracking-[0.09em] text-ink-300 mb-2.5">Pain Points</p>
                  <ul className="flex flex-col gap-1.5">
                    {brief.pain_points.map((p, i) => (
                      <li key={i} className="flex items-baseline gap-2 text-[13px] text-ink-500">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-200 flex-shrink-0 mt-1.5" />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}

            {/* Sources */}
            {brief.sources_used?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-4">
                {brief.sources_used.map((src, i) => (
                  <span key={i} className="text-[11px] font-mono text-ink-300 bg-ground rounded px-2 py-0.5">
                    {formatSource(src)}
                  </span>
                ))}
                {brief.partial && (
                  <span className="text-[11px] font-mono text-amber-600 bg-amber-50 rounded px-2 py-0.5">partial data</span>
                )}
              </div>
            )}
          </>
        )}

        {/* ── Footer ───────────────────────────────────────────────── */}
        <div className="flex items-center justify-between pt-3.5 mt-3.5 border-t border-border">
          <button
            onClick={() => setCollapsed(c => !c)}
            className="text-[12px] font-medium text-ink-300 hover:text-ink-500 px-2 py-1 rounded transition-colors"
          >
            {collapsed ? 'Show brief' : 'Collapse'}
          </button>
          <button
            onClick={() => onRefresh(meeting.id)}
            className="text-[12px] font-medium text-accent hover:text-indigo-700 px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
          >
            ↻ Re-run
          </button>
        </div>

      </div>
    </article>
  )
}

function ScoreBadge({ score }) {
  const cls = score >= 8 ? 'text-success border-success'
            : score >= 6 ? 'text-warm border-warm'
            :              'text-danger border-danger'
  return (
    <div className={`flex flex-col items-center justify-center w-11 h-10 rounded-lg border-[1.5px] ${cls}`}>
      <span className="text-[17px] font-bold font-mono leading-none tracking-tight">{score.toFixed(1)}</span>
      <span className="text-[8px] font-bold font-mono uppercase tracking-widest opacity-70 mt-0.5">Score</span>
    </div>
  )
}

function getUrgency(startTime) {
  const mins = (new Date(startTime) - new Date()) / 60000
  if (mins < 0)   return { shadow: 'shadow-card',        badge: 'bg-ground text-ink-300',             label: 'Ended'    }
  if (mins < 60)  return { shadow: 'shadow-card-urgent', badge: 'bg-red-50 text-red-800',              label: `⚠ in ${Math.round(mins)}m` }
  if (mins < 240) return { shadow: 'shadow-card-warm',   badge: 'bg-amber-50 text-amber-800',          label: `Today · ${formatTime(startTime)}` }
  return            { shadow: 'shadow-card-accent',  badge: 'bg-indigo-50 text-indigo-700',        label: `Tomorrow · ${formatTime(startTime)}` }
}

function formatSource(src) {
  try { return new URL(src).hostname.replace('www.', '') }
  catch { return src.length > 36 ? src.slice(0, 36) + '…' : src }
}
