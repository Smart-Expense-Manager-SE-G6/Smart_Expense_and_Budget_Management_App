import Icon from './Icon'

// variant: primary | secondary | ghost | danger   size: sm | md | lg
export default function Button({
  variant = 'secondary',
  size = 'md',
  icon,
  loading = false,
  block = false,
  iconOnly = false,
  className = '',
  children,
  disabled,
  type = 'button',
  ...rest
}) {
  const classes = [
    'btn',
    variant !== 'secondary' && `btn-${variant}`,
    size !== 'md' && `btn-${size}`,
    block && 'btn-block',
    iconOnly && 'btn-icon',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <button type={type} className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className="spinner" aria-hidden="true" /> : icon && <Icon name={icon} size={size === 'sm' ? 15 : 17} />}
      {children}
    </button>
  )
}

