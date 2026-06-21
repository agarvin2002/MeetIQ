import { formatTime, formatDate } from '../utils/time'

export default function FallbackCard({ meeting }) {
  return (
    <article className="bg-surface rounded-2xl opacity-60 shadow-[0_1px_2px_rgba(17,24,39,0.04)] animate-card-enter">
      <div className="px-7 py-5 flex items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-mono uppercase tracking-[0.07em] text-ink-300 mb-1.5">
            {formatDate(meeting.start_time)} · {formatTime(meeting.start_time)} – {formatTime(meeting.end_time)}
          </p>
          <h3 className="text-[15px] font-semibold text-ink-500">{meeting.title}</h3>
          <p className="text-[12px] text-ink-300 mt-1 italic">
            All attendees use personal email domains — no company identified
          </p>
        </div>
        <span className="flex-shrink-0 text-[11px] font-medium text-ink-300 bg-ground border border-border rounded-full px-3 py-1">
          Unidentified
        </span>
      </div>
    </article>
  )
}
