import { Link } from 'react-router-dom'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import ProgressBar from '../../components/ui/ProgressBar'
import Skeleton from '../../components/ui/Skeleton'
import useBudgets from '../../hooks/useBudgets'
import { formatCurrency, formatShortDate, toneForPercent } from '../../lib/format'

const VISIBLE = 4

export default function BudgetOverview() {
  const { active, loading, error } = useBudgets()
  const shown = [...active].sort((a, b) => b.util.percent - a.util.percent).slice(0, VISIBLE)

  return (
    <Card
      title="Budgets"
      subtitle="Active budget periods"
      action={
        <Link to="/budgets" className="btn btn-ghost btn-sm">
          Manage
        </Link>
      }
    >
      {loading ? (
        <div className="stack">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={46} radius="12px" />
          ))}
        </div>
      ) : error ? (
        <p className="muted">Could not load budgets. {error.message}</p>
      ) : shown.length === 0 ? (
        <EmptyState
          icon="target"
          title="No active budgets"
          description="Set a weekly or monthly budget to track utilisation and get alerts."
          action={
            <Link to="/budgets" className="btn btn-primary btn-sm">
              Create a budget
            </Link>
          }
        />
      ) : (
        <ul className="stack budget-list">
          {shown.map((budget) => {
            const tone = toneForPercent(budget.util.percent)
            return (
              <li key={budget.id} className="budget-row">
                <div className="budget-row-head">
                  <div className="budget-row-name">
                    <strong>{budget.name}</strong>
                    <span className="cell-sub">
                      {budget.category_name ?? 'All categories'} · ends {formatShortDate(budget.end_date)}
                    </span>
                  </div>
                  <Badge tone={tone}>{Math.round(budget.util.percent)}%</Badge>
                </div>
                <ProgressBar percent={budget.util.percent} label={`${budget.name} utilisation`} />
                <div className="budget-row-foot">
                  <span>{formatCurrency(budget.util.spent, { whole: true })} spent</span>
                  <span>{formatCurrency(Math.max(budget.util.remaining, 0), { whole: true })} left</span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}
