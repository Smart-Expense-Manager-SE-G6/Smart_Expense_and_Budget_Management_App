import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/context'
import Segmented from '../components/ui/Segmented'
import AlertsPanel from '../features/dashboard/AlertsPanel'
import BudgetOverview from '../features/dashboard/BudgetOverview'
import CategoryBreakdown from '../features/dashboard/CategoryBreakdown'
import Forecast from '../features/dashboard/Forecast'
import RecentExpenses from '../features/dashboard/RecentExpenses'
import SpendingTrend from '../features/dashboard/SpendingTrend'
import SummaryCards from '../features/dashboard/SummaryCards'
import useCategories from '../hooks/useCategories'
import { displayName, formatDate, greeting, PERIODS, rangeFor } from '../lib/format'

const PERIOD_OPTIONS = Object.entries(PERIODS).map(([value, { label }]) => ({ value, label }))

export default function DashboardPage() {
  const { user } = useAuth()
  const [period, setPeriod] = useState('month')
  const { byId } = useCategories()
  const range = useMemo(() => rangeFor(period), [period])
  const firstName = user.first_name?.trim() || displayName(user)

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">
            {greeting()}, {firstName}
          </h1>
          <p className="page-subtitle">
            {formatDate(range.start_date)} – {formatDate(range.end_date)}
          </p>
        </div>
        <div className="page-actions">
          <Segmented label="Reporting period" options={PERIOD_OPTIONS} value={period} onChange={setPeriod} />
          <Link to="/expenses?new=1" className="btn btn-primary">
            + Add expense
          </Link>
        </div>
      </header>

      <SummaryCards start={range.start_date} end={range.end_date} />

      <div className="grid grid-main">
        <SpendingTrend />
        <Forecast />
      </div>

      <div className="grid grid-2">
        <CategoryBreakdown start={range.start_date} end={range.end_date} />
        <BudgetOverview />
      </div>

      <div className="grid grid-main-rev">
        <AlertsPanel />
        <RecentExpenses categoriesById={byId} />
      </div>
    </>
  )
}

