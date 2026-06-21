import { useMeetings } from '../hooks/useMeetings'
import MeetingCard from '../components/MeetingCard'
import LoadingCard from '../components/LoadingCard'
import FallbackCard from '../components/FallbackCard'
import RefreshBar from '../components/RefreshBar'

export default function DashboardPage({ user, onLogout }) {
  const { meetings, loading, error, lastUpdated, refresh, refreshMeeting } = useMeetings()

  const upcoming = meetings.filter(m => new Date(m.start_time) >= new Date())
  const past     = meetings.filter(m => new Date(m.start_time) <  new Date())

  return (
    <div className="min-h-screen bg-ground">

      {/* ── Navbar ─────────────────────────────────────────────────── */}
      <header className="bg-nav h-[52px] flex items-center px-7 gap-6 sticky top-0 z-50">
        <div className="flex items-center gap-2.5 flex-shrink-0">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <span className="text-white font-bold text-base tracking-tight">MeetIQ</span>
        </div>

        <div className="w-px h-5 bg-white/10 flex-shrink-0" />

        <span className="text-[13px] font-mono text-[#C9D1E3] flex-1">
          {new Date().toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
        </span>

        <div className="flex items-center gap-4 text-[13px] text-[#C9D1E3]">
          {user?.email && <span className="hidden sm:block">{user.email}</span>}
          <button
            onClick={onLogout}
            className="text-[#C9D1E3]/55 hover:text-white hover:bg-white/8 px-2.5 py-1 rounded-md transition-all text-[13px]"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────────── */}
      <main className="max-w-[760px] mx-auto px-6 pt-9 pb-20">

        {/* Page header */}
        <div className="flex items-end justify-between gap-4 mb-7">
          <div>
            <h1 className="text-[26px] font-bold tracking-tighter text-ink-900 leading-tight">
              Your briefings
            </h1>
            <p className="text-[13px] font-mono text-ink-300 mt-1">
              {upcoming.length} meeting{upcoming.length !== 1 ? 's' : ''} identified · next 7 days
            </p>
          </div>
          <RefreshBar lastUpdated={lastUpdated} onRefresh={refresh} loading={loading} />
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Initial load skeleton */}
        {loading && meetings.length === 0 && (
          <div className="flex flex-col gap-3.5">
            {[0, 1, 2].map(i => (
              <div key={i} className="bg-surface rounded-2xl shadow-card px-7 py-6">
                <div className="h-3 w-48 bg-border rounded animate-shimmer mb-3" />
                <div className="h-7 w-40 bg-border rounded animate-shimmer mb-2" />
                <div className="h-3 w-64 bg-border rounded animate-shimmer" />
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && meetings.length === 0 && !error && (
          <div className="text-center py-24">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-ground border border-border mb-5">
              <svg className="w-7 h-7 text-ink-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="font-semibold text-ink-500">No upcoming meetings</p>
            <p className="text-[13px] text-ink-300 mt-1">Meetings with external attendees appear here</p>
          </div>
        )}

        {/* Meeting cards */}
        {upcoming.length > 0 && (
          <div className="flex flex-col gap-3.5">
            {upcoming.map(m => <MeetingRouter key={m.id} meeting={m} onRefresh={refreshMeeting} />)}
          </div>
        )}

        {/* Past meetings */}
        {past.length > 0 && (
          <details className="mt-10 group">
            <summary className="cursor-pointer list-none flex items-center gap-2 text-[13px] text-ink-300 hover:text-ink-500 font-medium mb-4 transition-colors">
              <svg className="w-3.5 h-3.5 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              {past.length} past meeting{past.length !== 1 ? 's' : ''}
            </summary>
            <div className="flex flex-col gap-3.5 opacity-50">
              {past.map(m => <MeetingRouter key={m.id} meeting={m} onRefresh={refreshMeeting} />)}
            </div>
          </details>
        )}
      </main>
    </div>
  )
}

function MeetingRouter({ meeting, onRefresh }) {
  switch (meeting.brief_status) {
    case 'ready':        return <MeetingCard meeting={meeting} onRefresh={onRefresh} />
    case 'researching':  return <LoadingCard meeting={meeting} />
    case 'failed':       return <FailedCard meeting={meeting} onRefresh={onRefresh} />
    case 'unidentified':
    default:             return <FallbackCard meeting={meeting} />
  }
}

function FailedCard({ meeting, onRefresh }) {
  return (
    <article className="bg-surface rounded-2xl shadow-card border border-red-100 px-7 py-5 animate-card-enter">
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="text-base font-semibold text-ink-700">{meeting.title}</h3>
        <span className="flex-shrink-0 text-[11px] font-medium text-red-700 bg-red-50 rounded-full px-2.5 py-1">Failed</span>
      </div>
      <p className="text-[13px] text-ink-300 mb-3">Research could not complete for {meeting.company_name}.</p>
      <button
        onClick={() => onRefresh(meeting.id)}
        className="text-[13px] font-semibold text-accent hover:text-indigo-700 flex items-center gap-1.5 transition-colors"
      >
        ↻ Try again
      </button>
    </article>
  )
}
