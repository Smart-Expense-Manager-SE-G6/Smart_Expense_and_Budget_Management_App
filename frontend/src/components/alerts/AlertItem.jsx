import Icon from '../ui/Icon'
import Button from '../ui/Button'
import { timeAgo } from '../../lib/format'

function toneFor(alert) {
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
      </div>
      {!alert.is_read && onMarkRead && (
        <Button size="sm" icon="check" onClick={() => onMarkRead(alert.id)}>
          Mark read
        </Button>
      )}
    </li>
  )
}

