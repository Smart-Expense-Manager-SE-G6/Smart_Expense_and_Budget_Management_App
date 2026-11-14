import Icon from './Icon'

export default function EmptyState({ icon = 'receipt', title, description, action }) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon name={icon} size={24} />
      </span>
      <h3 className="empty-title">{title}</h3>
      {description && <p className="empty-text">{description}</p>}
      {action}
    </div>
  )
}

