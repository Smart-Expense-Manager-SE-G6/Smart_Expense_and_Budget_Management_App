
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Notifications() {
  const [alerts, setAlerts] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function loadAlerts() {
    setLoading(true)
    setError('')

    try {
      const data = await api('/alerts/')
      setAlerts(Array.isArray(data) ? data : data.results ?? [])
    } catch (err) {
      setError(err.message || 'Could not load notifications.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlerts()
  }, [])

  async function markAsRead(alertId) {
    try {
      const updated = await api(`/alerts/${alertId}/mark-read/`, {
        method: 'PATCH',
      })

      setAlerts((current) =>
        current.map((alert) =>
          alert.id === alertId ? updated : alert
        )
      )
    } catch (err) {
      setError(err.message || 'Could not update notification.')
    }
  }

  const unreadCount = alerts.filter((alert) => !alert.is_read).length

  return (
    <div className="notification-wrapper">
      <button
        type="button"
        className="notification-button"
        aria-label={`Notifications, ${unreadCount} unread`}
        aria-expanded={open}
        onClick={() => {
          setOpen((value) => !value)
          if (!open) loadAlerts()
        }}
      >
        🔔
        {unreadCount > 0 && (
          <span className="notification-count">{unreadCount}</span>
        )}
      </button>

      {open && (
        <section className="notification-panel">
          <h3>Notifications</h3>

          {loading && <p>Loading notifications...</p>}
          {error && <p role="alert">{error}</p>}

          {!loading && alerts.length === 0 && (
            <p>No notifications yet.</p>
          )}

          {alerts.map((alert) => (
            <article
              key={alert.id}
              className={`notification-item ${
                alert.is_read ? 'read' : 'unread'
              }`}
            >
              <strong>{alert.title}</strong>
              <p>{alert.message}</p>

              {alert.alert_type === 'anomaly' && (
                <span className="anomaly-label">
                  Spending anomaly
                </span>
              )}

              {!alert.is_read && (
                <button
                  type="button"
                  onClick={() => markAsRead(alert.id)}
                >
                  Mark as read
                </button>
              )}
            </article>
          ))}
        </section>
      )}
    </div>
  )
}
