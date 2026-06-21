const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-surface-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md animate-fade-in">

        {/* Logo + brand */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-500 shadow-lg mb-5">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-ink-900 tracking-tight">MeetIQ</h1>
          <p className="mt-2 text-ink-500 text-base">Meeting intelligence, automatically.</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-card p-8">
          <h2 className="text-xl font-semibold text-ink-900 mb-1">Connect your calendar</h2>
          <p className="text-ink-500 text-sm mb-7 leading-relaxed">
            MeetIQ reads your upcoming meetings, identifies the companies involved,
            and prepares an intelligence brief before each call — automatically.
          </p>

          {/* Feature list */}
          <ul className="space-y-3 mb-8">
            {[
              ['📅', 'Reads your Google Calendar'],
              ['🔍', 'Researches companies from attendee emails'],
              ['📝', 'Generates briefs with news, tech signals & talking points'],
              ['🔒', 'Read-only access — never modifies your calendar'],
            ].map(([icon, text]) => (
              <li key={text} className="flex items-center gap-3 text-sm text-ink-700">
                <span className="text-base">{icon}</span>
                <span>{text}</span>
              </li>
            ))}
          </ul>

          {/* CTA */}
          <a
            href={`${API}/auth/login`}
            className="flex items-center justify-center gap-3 w-full py-3.5 px-5 rounded-xl bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white font-semibold text-sm transition-all duration-150 shadow-sm hover:shadow-md"
          >
            <GoogleIcon />
            Sign in with Google
          </a>

          <p className="mt-5 text-center text-xs text-ink-300">
            Only calendar read-access is requested. No data is stored permanently.
          </p>
        </div>
      </div>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24">
      <path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="rgba(255,255,255,0.8)" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="rgba(255,255,255,0.6)" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="rgba(255,255,255,0.9)" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  )
}
