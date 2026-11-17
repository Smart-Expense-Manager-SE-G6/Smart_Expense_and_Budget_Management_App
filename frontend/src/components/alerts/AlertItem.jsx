import Icon from '../ui/Icon'
import Button from '../ui/Button'
import { Link } from 'react-router-dom'
import { timeAgo } from '../../lib/format'

function toneFor(alert) {
  if (alert.alert_type === 'anomaly') return 'danger'
  if ((alert.threshold_percentage ?? 0) >= 100) return 'danger'
  if ((alert.threshold_percentage ?? 0) >= 80) return 'warning'
  return 'info'
}

export default function AlertItem({ alert, onMarkRead }) {
  const tone = toneFor(alert)
  return (
    <li className="alert-item" data-read={alert.is_read} data-tone={tone}>
      <span className="alert-icon" data-tone={tone}>
        <Icon name={tone === 'info' ? 'info' : 'alert'} size={18} />
      </span>
      <div className="alert-main">
        <div className="alert-title">
          <strong>{alert.title}</strong>
          {!alert.is_read && <span className="unread-dot" aria-label="Unread" />}
        </div>
        <p className="alert-message">{alert.message}</p>
        <span className="cell-sub">{timeAgo(alert.created_at)}</span>
        <div className="alert-links">
          {alert.budget && <Link to={`/budgets?budget_id=${alert.budget}`}>View budget</Link>}
          {alert.expense && <Link to={`/expenses?expense_id=${alert.expense}`}>View expense</Link>}
        </div>
        <span className="cell-sub">
          {alert.email_sent ? 'Email sent' : alert.email_error ? `Email failed: ${alert.email_error}` : 'Email not sent'}
        </span>
      </div>
      {!alert.is_read && onMarkRead && (
        <Button size="sm" icon="check" onClick={() => onMarkRead(alert.id)}>
          Mark read
        </Button>
      )}
    </li>
  )
}
