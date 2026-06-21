import { useState, useEffect, useCallback } from 'react'
import api from '../api/client'

export function useMeetings() {
  const [meetings, setMeetings]       = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchMeetings = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    setError(null)
    try {
      const { data } = await api.get('/meetings/')
      setMeetings(data)
      setLastUpdated(new Date())
    } catch (e) {
      if (e.response?.status === 401) {
        // Session expired — reload triggers auth check in App
        window.location.reload()
      } else {
        setError('Could not load meetings. Is the backend running?')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshMeeting = useCallback(async (meetingId) => {
    try {
      await api.post(`/meetings/${meetingId}/refresh`)
      // Silently re-fetch all meetings after triggering refresh
      await fetchMeetings(true)
    } catch (e) {
      console.error('Refresh failed', e)
    }
  }, [fetchMeetings])

  useEffect(() => {
    fetchMeetings()
    // Poll every 60s — "researching" cards flip to "ready" on next poll
    const interval = setInterval(() => fetchMeetings(true), 60_000)
    return () => clearInterval(interval)
  }, [fetchMeetings])

  return { meetings, loading, error, lastUpdated, refresh: fetchMeetings, refreshMeeting }
}
