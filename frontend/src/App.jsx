import { useState, useEffect } from 'react'
import api from './api/client'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'

export default function App() {
  const [authState, setAuthState] = useState('loading')  // 'loading' | 'authenticated' | 'unauthenticated'
  const [user, setUser] = useState(null)

  useEffect(() => {
    api.get('/auth/status')
      .then(({ data }) => {
        if (data.authenticated) {
          setUser({ email: data.email })
          setAuthState('authenticated')
        } else {
          setAuthState('unauthenticated')
        }
      })
      .catch(() => setAuthState('unauthenticated'))
  }, [])

  const handleLogout = async () => {
    await api.post('/auth/logout').catch(() => {})
    setUser(null)
    setAuthState('unauthenticated')
  }

  if (authState === 'loading') {
    return (
      <div className="min-h-screen bg-surface-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500 animate-pulse" />
          <p className="text-sm text-ink-400 font-medium">Loading…</p>
        </div>
      </div>
    )
  }

  if (authState === 'unauthenticated') {
    return <LoginPage />
  }

  return <DashboardPage user={user} onLogout={handleLogout} />
}
