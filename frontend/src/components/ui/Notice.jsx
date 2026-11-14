import Icon from './Icon'

const TONE_ICON = { danger: 'alert', warning: 'alert', success: 'checkCircle', info: 'info' }

export default function Notice({ tone = 'info', action, children, ...rest }) {
  return (
    <div className="notice" data-tone={tone} role={tone === 'danger' ? 'alert' : 'status'} {...rest}>
      <Icon name={TONE_ICON[tone]} size={18} />
      <div className="notice-body">{children}</div>
      {action}
    </div>
  )
}

