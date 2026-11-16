import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import { AlertsContext } from './context'

const POLL_MS = 60_000
const FETCH_PAGE_SIZE = 100

const byNewest = (a, b) => new Date(b.created_at) - new Date(a.created_at)

// Shared in-app alert state (FR16/FR18) so the sidebar badge, dashboard and alerts page stay in sync.
export default function AlertsProvider({ children }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const refreshing = useRef(false)

  const refresh = useCallback(async () => {
    if (refreshing.current) return
    refreshing.current = true
    try {
      const firstPage = await api(`/alerts/?page_size=${FETCH_PAGE_SIZE}`)
      const list = Array.isArray(firstPage) ? firstPage : [...(firstPage?.results ?? [])]
      const count = firstPage?.count ?? list.length
      const totalPages = Math.ceil(count / FETCH_PAGE_SIZE)
      for (let page = 2; page <= totalPages; page += 1) {
        const data = await api(`/alerts/?page=${page}&page_size=${FETCH_PAGE_SIZE}`)
        list.push(...(data?.results ?? []))
      }
      setAlerts([...list].sort(byNewest))
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      refreshing.current = false
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, POLL_MS)
    const refreshOnFocus = () => refresh()
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    window.addEventListener('focus', refreshOnFocus)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      clearInterval(id)
      window.removeEventListener('focus', refreshOnFocus)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [refresh])

  const markRead = useCallback(async (id) => {
    await api(`/alerts/${id}/mark-read/`, { method: 'PATCH' })
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)))
  }, [])

  const markAllRead = useCallback(async () => {
    await api('/alerts/mark-all-read/', { method: 'PATCH' })
    setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })))
  }, [])

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
