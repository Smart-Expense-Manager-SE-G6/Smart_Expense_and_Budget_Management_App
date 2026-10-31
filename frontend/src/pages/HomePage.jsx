
import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth/context'

export default function HomePage() {
  const { user } = useAuth()

  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updatingId, setUpdatingId] = useState(null)

  useEffect(() => {
    let active = true

    async function loadAlerts() {
      try {
        const data = await api('/alerts/')
        if (active) {
          setAlerts(Array.isArray(data) ? data : data.results ?? [])
        }
      } catch (err) {
        if (active) setError(err.message || 'Could not load notifications.')
      } finally {
        if (active) setLoading(false)
      }
    }

    loadAlerts()
    return () => {
      active = false
    }
  }, [])

  async function handleMarkRead(alertId) {
    setUpdatingId(alertId)
    setError('')

    try {
      const updatedAlert = await api(
        `/alerts/${alertId}/mark-read/`,
        { method: 'PATCH' }
      )

      setAlerts((current) =>
        current.map((alert) =>
          alert.id === alertId ? updatedAlert : alert
        )
      )
    } catch (err) {
      setError(err.message || 'Could not mark notification as read.')
    } finally {
      setUpdatingId(null)
    }
  }

  const unreadCount = alerts.filter((alert) => !alert.is_read).length

  return (
    <section className="card">
      <h1>Welcome{user.first_name ? `, ${user.first_name}` : ''}</h1>
      <p className="muted">Your notifications and budget alerts.</p>

      <section aria-labelledby="notifications-heading">
        <h2 id="notifications-heading">
          Notifications ({unreadCount} unread)
        </h2>

        {loading && <p className="muted">Loading notifications...</p>}

        {error && <p className="form-error" role="alert">{error}</p>}

        {!loading && alerts.length === 0 && !error && (
          <p className="muted">You have no notifications yet.</p>
        )}

        <ul className="notification-list">
          {alerts.map((alert) => (
            <li key={alert.id} className="notification-item">
              <div>
                <h3>{alert.title}</h3>
                <p>{alert.message}</p>
                <p className="muted">
                  {new Date(alert.created_at).toLocaleString()}
                </p>
                <p className="muted">
                  {alert.is_read ? 'Read' : 'Unread'}
                </p>
              </div>

              {!alert.is_read && (
                <button
                  type="button"
                  onClick={() => handleMarkRead(alert.id)}
                  disabled={updatingId === alert.id}
                >
                  {updatingId === alert.id ? 'Updating...' : 'Mark as read'}
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </section>
  )
}
