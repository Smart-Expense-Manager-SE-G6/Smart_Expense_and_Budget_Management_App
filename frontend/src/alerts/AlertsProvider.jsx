import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { AlertsContext } from './context'

const POLL_MS = 60_000

const byNewest = (a, b) => new Date(b.created_at) - new Date(a.created_at)

// Shared in-app alert state (FR16/FR18) so the sidebar badge, dashboard and alerts page stay in sync.
export default function AlertsProvider({ children }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const data = await api('/alerts/')
      const list = Array.isArray(data) ? data : (data?.results ?? [])
      setAlerts([...list].sort(byNewest))
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const markRead = useCallback(async (id) => {
    await api(`/alerts/${id}/mark-read/`, { method: 'PATCH' })
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)))
  }, [])

  const markAllRead = useCallback(async () => {
    const unread = alerts.filter((a) => !a.is_read)
    await Promise.all(unread.map((a) => api(`/alerts/${a.id}/mark-read/`, { method: 'PATCH' })))
    setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })))
  }, [alerts])

  const value = useMemo(
    () => ({
      alerts,
      unreadCount: alerts.filter((a) => !a.is_read).length,
      loading,
      error,
      refresh,
      markRead,
      markAllRead,
    }),
    [alerts, loading, error, refresh, markRead, markAllRead],
  )

  return <AlertsContext.Provider value={value}>{children}</AlertsContext.Provider>
}

