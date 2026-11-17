import { useState } from 'react'
import { useAlerts } from '../alerts/context'
import AlertItem from '../components/alerts/AlertItem'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import Segmented from '../components/ui/Segmented'

const PAGE_SIZE = 10

export default function AlertsPage() {
  const { alerts, unreadCount, loading, error, markRead, markAllRead, refresh } = useAlerts()
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const filteredAlerts = alerts.filter((alert) => {
    if (filter === 'unread') return !alert.is_read
    if (filter === 'threshold' || filter === 'anomaly') return alert.alert_type === filter
    return true
  })
  const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const shown = filteredAlerts.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const setFilterAndResetPage = (value) => {
    setFilter(value)
    setPage(1)
  }

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
          <p className="page-subtitle">Budget threshold and unusual-spending alerts.</p>
        </div>
        <div className="page-actions">
          <Segmented
            label="Filter alerts"
            value={filter}
            onChange={setFilterAndResetPage}
            options={[
              { value: 'all', label: `All (${alerts.length})` },
              { value: 'unread', label: `Unread (${unreadCount})` },
              { value: 'threshold', label: `Threshold (${alerts.filter((a) => a.alert_type === 'threshold').length})` },
              { value: 'anomaly', label: `Anomaly (${alerts.filter((a) => a.alert_type === 'anomaly').length})` },
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
            title={filter === 'unread' ? 'No unread alerts' : `No ${filter === 'all' ? '' : `${filter} `}alerts`}
            description={filter === 'unread' ? 'You are all caught up.' : 'Alerts appear here when a budget threshold is reached or spending is unusual.'}
          />
        ) : (
          <>
            <ul className="alert-list alert-list-page">
              {shown.map((alert) => (
                <AlertItem key={alert.id} alert={alert} onMarkRead={(id) => run(() => markRead(id))} />
              ))}
            </ul>
            <div className="pagination">
              <span>
                {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredAlerts.length)} of {filteredAlerts.length}
              </span>
              <div className="pagination-actions">
                <Button size="sm" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
                  Previous
                </Button>
                <span className="pagination-page">Page {currentPage} / {totalPages}</span>
                <Button size="sm" disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>
                  Next
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </>
  )
}
