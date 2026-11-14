import { Link } from 'react-router-dom'
import { useAlerts } from '../../alerts/context'
import AlertItem from '../../components/alerts/AlertItem'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'

export default function AlertsPanel() {
  const { alerts, unreadCount, loading, markRead } = useAlerts()
  const shown = alerts.slice(0, 4)

  return (
    <Card
      title="Alerts"
      subtitle={unreadCount ? `${unreadCount} unread` : 'You are all caught up'}
      action={
        <Link to="/alerts" className="btn btn-ghost btn-sm">
          View all
        </Link>
      }
    >
      {loading ? null : shown.length === 0 ? (
        <EmptyState icon="bell" title="No alerts" description="You will be notified when spending crosses 80% or 100% of a budget." />
      ) : (
        <ul className="alert-list">
          {shown.map((alert) => (
            <AlertItem key={alert.id} alert={alert} onMarkRead={markRead} />
          ))}
        </ul>
      )}
    </Card>
  )
}

