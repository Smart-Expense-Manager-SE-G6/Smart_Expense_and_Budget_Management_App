import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import AlertsProvider from '../../alerts/AlertsProvider'
import { useAlerts } from '../../alerts/context'
import { useAuth } from '../../auth/context'
import { displayName } from '../../lib/format'
import Avatar from '../ui/Avatar'
import BrandMark from '../ui/BrandMark'
import Button from '../ui/Button'
import Icon from '../ui/Icon'
import ThemeToggle from './ThemeToggle'

const NAV = [
  { to: '/', label: 'Dashboard', icon: 'grid', end: true },
  { to: '/expenses', label: 'Expenses', icon: 'wallet' },
  { to: '/budgets', label: 'Budgets', icon: 'target' },
  { to: '/reports', label: 'Reports', icon: 'file' },
  { to: '/alerts', label: 'Alerts', icon: 'bell', badge: true },
]

const TITLES = {
  '/': 'Dashboard',
  '/expenses': 'Expenses',
  '/budgets': 'Budgets',
  '/reports': 'Reports',
  '/alerts': 'Alerts',
  '/profile': 'Profile',
}



function Shell() {
  const { user, logout } = useAuth()
  const { unreadCount } = useAlerts()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [navOpen, setNavOpen] = useState(false)

  // Close the mobile drawer after navigating.
  useEffect(() => setNavOpen(false), [pathname])

  async function handleLogout() {
    try {
      await logout()
    } finally {
      // The local session is cleared either way, so always land on the sign-in page.
      navigate('/login')
    }
  }

  return (
    <div className="app" data-nav-open={navOpen}>
      <aside className="sidebar" aria-label="Primary">
        <Link to="/" className="brand">
          <BrandMark />
          <span className="brand-name">
            Smart Expense
            <span className="brand-tag">Budget manager</span>
          </span>
        </Link>

        <p className="nav-label">Menu</p>
        <nav className="nav" aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
              <Icon name={item.icon} size={19} />
              {item.label}
              {item.badge && unreadCount > 0 && (
                <span className="nav-count" aria-label={`${unreadCount} unread`}>
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <Avatar user={user} />
          <Link to="/profile" className="sidebar-user" title="Your profile">
            <strong>{displayName(user)}</strong>
            <span>{user.email}</span>
          </Link>
          <Button variant="ghost" size="sm" iconOnly icon="logout" aria-label="Sign out" title="Sign out" onClick={handleLogout} />
        </div>
      </aside>

      <button type="button" className="scrim" aria-label="Close menu" onClick={() => setNavOpen(false)} />

      <div className="main">
        <header className="topbar">
          <button type="button" className="icon-btn menu-btn" aria-label="Open menu" onClick={() => setNavOpen(true)}>
            <Icon name="menu" size={19} />
          </button>
          <p className="topbar-title">{TITLES[pathname] ?? 'Smart Expense'}</p>
          <span className="topbar-spacer" />
          <ThemeToggle />
          <Link to="/alerts" className="icon-btn" aria-label={`Alerts, ${unreadCount} unread`}>
            <Icon name="bell" size={18} />
            {unreadCount > 0 && <span className="pip" />}
          </Link>
        </header>
        <main className="page" key={pathname}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default function AppShell() {
  return (
    <AlertsProvider>
      <Shell />
    </AlertsProvider>
  )
}
