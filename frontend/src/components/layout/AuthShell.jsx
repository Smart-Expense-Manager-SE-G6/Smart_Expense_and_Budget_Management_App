import { Link } from 'react-router-dom'
import BrandMark from '../ui/BrandMark'
import Icon from '../ui/Icon'
import ThemeToggle from './ThemeToggle'

const POINTS = [
  { icon: 'target', text: 'Budgets with live 80% and 100% alerts' },
  { icon: 'bars', text: 'Analytics, forecasts and month-on-month trends' },
  { icon: 'file', text: 'One-click PDF and Excel reports' },
]

// Split-screen layout shared by the sign-in and registration screens.
export default function AuthShell({ title, subtitle, footer, children }) {
  return (
    <div className="auth">
      <aside className="auth-hero" aria-hidden="false">
        <Link to="/login" className="brand">
          <BrandMark size={22} />
          <span className="brand-name">
            Smart Expense
            <span className="brand-tag">Budget manager</span>
          </span>
        </Link>

        <div>
          <h2 className="auth-headline">Know where every rupee goes.</h2>
          <p className="auth-lede">Track spending, stay inside your budgets and get ahead of overspending before it happens.</p>
          <ul className="auth-points">
            {POINTS.map((point) => (
              <li key={point.text}>
                <span className="pt-icon">
                  <Icon name={point.icon} size={18} />
                </span>
                {point.text}
              </li>
            ))}
          </ul>
        </div>

        <p className="auth-foot">
          <Icon name="shield" size={14} style={{ display: 'inline', verticalAlign: '-2px', marginRight: 6 }} />
          Passwords are hashed with bcrypt. Your data is never shared.
        </p>
      </aside>

      <main className="auth-panel">
        <ThemeToggle className="auth-theme" />
        <div className="auth-card">
          <h1>{title}</h1>
          <p className="lede">{subtitle}</p>
          {children}
          <p className="auth-switch">{footer}</p>
        </div>
      </main>
    </div>
  )
}

