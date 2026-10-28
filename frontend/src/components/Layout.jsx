import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <>
      <header className="topbar">
        <span className="brand">Smart Expense</span>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/profile">Profile</NavLink>
          <button type="button" className="link-button" onClick={handleLogout}>
            Log out
          </button>
        </nav>
      </header>
      <main className="page">
        <p className="muted">Signed in as {user.email}</p>
        <Outlet />
      </main>
    </>
  )
}
