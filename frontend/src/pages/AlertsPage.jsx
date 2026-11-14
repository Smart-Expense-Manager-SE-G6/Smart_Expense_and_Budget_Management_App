import { useState } from 'react'
import { useAlerts } from '../alerts/context'
import AlertItem from '../components/alerts/AlertItem'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import Segmented from '../components/ui/Segmented'

export default function AlertsPage() {
  const { alerts, unreadCount, loading, error, markRead, markAllRead, refresh } = useAlerts()
  const [filter, setFilter] = useState('all')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const shown = filter === 'unread' ? alerts.filter((a) => !a.is_read) : alerts

  async function run(action) {
    setActionError(null)
    try {
      await action()
    } catch (err) {
      setActionError(err)
    }
  }

  async function handleMarkAll() {
    setBusy(true)
    await run(markAllRead)
    setBusy(false)
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Alerts</h1>
          <p className="page-subtitle">Budget threshold notifications at 80% and 100% of a limit.</p>
        </div>
        <div className="page-actions">
          <Segmented
            label="Filter alerts"
            value={filter}
            onChange={setFilter}
            options={[
              { value: 'all', label: `All (${alerts.length})` },
              { value: 'unread', label: `Unread (${unreadCount})` },
            ]}
          />
          <Button icon="check" disabled={unreadCount === 0} loading={busy} onClick={handleMarkAll}>
            Mark all read
          </Button>
        </div>
      </header>

      {(error || actionError) && (
        <div className="flash">
          <Notice tone="danger" action={<Button size="sm" onClick={refresh}>Retry</Button>}>
            {(actionError ?? error).message}
          </Notice>
        </div>
      )}

      <Card flush>
        {loading ? null : shown.length === 0 ? (
          <EmptyState
            icon="bell"
            title={filter === 'unread' ? 'No unread alerts' : 'No alerts yet'}
            description={filter === 'unread' ? 'You are all caught up.' : 'Alerts appear here when spending reaches 80% or 100% of a budget.'}
          />
        ) : (
          <ul className="alert-list alert-list-page">
            {shown.map((alert) => (
              <AlertItem key={alert.id} alert={alert} onMarkRead={(id) => run(() => markRead(id))} />
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}

