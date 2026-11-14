import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/context'

function Loading() {
  return (
    <p className="page muted" role="status">
      Loading…
    </p>
  )
}

// Only for signed-in users; others go to /login and come back afterwards.
export function RequireAuth() {
  const { user } = useAuth()
  const location = useLocation()
  if (user === undefined) return <Loading />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

// Only for signed-out users (login, register).
export function GuestOnly() {
  const { user } = useAuth()
  if (user === undefined) return <Loading />
  if (user) return <Navigate to="/" replace />
  return <Outlet />
}
