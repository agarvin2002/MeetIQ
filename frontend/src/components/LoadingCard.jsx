export default function LoadingCard({ meeting }) {
  return (
    <article className="bg-surface rounded-2xl shadow-card-muted animate-card-enter">
      <div className="px-7 pt-[22px] pb-[18px]">

        {/* Eyebrow */}
        <p className="text-[11px] font-mono uppercase tracking-[0.07em] text-ink-300 mb-3">
          {meeting.start_time
            ? new Date(meeting.start_time).toLocaleDateString([], { weekday: 'long' }) + ' · ' +
              new Date(meeting.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : 'Upcoming'}
        </p>

        {/* Animated indicator */}
        <div className="flex items-center gap-2.5 mb-4">
          <div className="flex gap-1.5">
            {[0, 1, 2].map(i => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-accent"
                style={{ animation: `dotPulse 1.4s ease-in-out ${i * 0.2}s infinite` }}
              />
            ))}
          </div>
          <span className="text-[13px] font-medium text-ink-500">
            Researching {meeting.company_name || 'company'}…
          </span>
        </div>

        {/* Skeleton company name */}
        <div className="h-7 w-36 rounded mb-2 bg-gradient-to-r from-border via-ground to-border bg-[length:600px_100%] animate-shimmer" />
        <div className="h-3.5 w-56 rounded bg-gradient-to-r from-border via-ground to-border bg-[length:600px_100%] animate-shimmer" />

        <hr className="border-border my-4" />

        {/* Skeleton description */}
        <div className="flex flex-col gap-2">
          <div className="h-3 w-full rounded bg-gradient-to-r from-border via-ground to-border bg-[length:600px_100%] animate-shimmer" />
          <div className="h-3 w-4/5 rounded bg-gradient-to-r from-border via-ground to-border bg-[length:600px_100%] animate-shimmer" />
        </div>

        <hr className="border-border my-4" />

        {/* Skeleton talking points */}
        <div className="h-[10px] w-24 rounded mb-3 bg-gradient-to-r from-border via-ground to-border bg-[length:600px_100%] animate-shimmer" />
        <div className="flex flex-col gap-2">
          {[88, 74, 82].map((w, i) => (
            <div key={i} className="h-3 rounded bg-gradient-to-r from-border via-ground to-border bg-[length:600px_100%] animate-shimmer" style={{ width: `${w}%` }} />
          ))}
        </div>

      </div>
    </article>
  )
}
