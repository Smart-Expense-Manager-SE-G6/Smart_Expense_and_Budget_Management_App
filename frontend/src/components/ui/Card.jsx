export default function Card({ title, subtitle, action, flush = false, className = '', children, as: Tag = 'section', ...rest }) {
  return (
    <Tag className={`card ${flush ? 'card-flush' : ''} ${className}`.trim()} {...rest}>
      {(title || action) && (
        <div className="card-header">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="card-body">{children}</div>
    </Tag>
  )
}

