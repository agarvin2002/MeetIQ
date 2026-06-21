export function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)

  if (d.toDateString() === today.toDateString())    return 'Today'
  if (d.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return d.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })
}

export function timeUntil(iso) {
  const diff = new Date(iso) - new Date()
  if (diff < 0) return 'Now'
  const mins = Math.floor(diff / 60000)
  if (mins < 60)  return `in ${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)   return `in ${hrs}h ${mins % 60}m`
  return `in ${Math.floor(hrs / 24)}d`
}

export function secondsAgo(date) {
  return Math.floor((new Date() - date) / 1000)
}
