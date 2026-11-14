import { initials } from '../../lib/format'

export default function Avatar({ user, size = 38 }) {
  return (
    <span className="avatar" style={{ '--size': `${size}px` }} aria-hidden="true">
      {initials(user)}
    </span>
  )
}

