import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import Skeleton from '../../components/ui/Skeleton'
import useAsync from '../../hooks/useAsync'
import { categoryColor, formatCurrency, formatShortDate, paymentLabel } from '../../lib/format'

export default function RecentExpenses({ categoriesById }) {
  const load = useCallback(() => api('/expenses/?page_size=6&ordering=-date'), [])
  const { data, loading, error } = useAsync(load)
  const rows = data?.results ?? []

  return (
    <Card
      title="Recent expenses"
      subtitle="Your latest transactions"
      action={
        <Link to="/expenses" className="btn btn-ghost btn-sm">
          View all
        </Link>
      }
    >
      {loading ? (
        <div className="stack">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} height={44} radius="12px" />
          ))}
        </div>
      ) : error ? (
        <p className="muted">Could not load expenses. {error.message}</p>
      ) : rows.length === 0 ? (
        <EmptyState
          icon="receipt"
          title="No expenses yet"
          description="Record your first expense to start building insight."
          action={
            <Link to="/expenses?new=1" className="btn btn-primary btn-sm">
              Add expense
            </Link>
          }
        />
      ) : (
        <ul className="tx-list">
          {rows.map((expense) => {
            const category = categoriesById.get(expense.category)
            return (
              <li key={expense.id} className="tx">
                <span className="tx-icon" style={{ '--dot': categoryColor(expense.category) }}>
                  {(category?.name ?? '?')[0].toUpperCase()}
                </span>
                <div className="tx-main">
                  <strong>{expense.description || category?.name || 'Expense'}</strong>
                  <span className="cell-sub">
                    {category?.name ?? 'Uncategorised'} · {formatShortDate(expense.date)} · {paymentLabel(expense.payment_method)}
                  </span>
                </div>
                <span className="tx-amount">−{formatCurrency(expense.amount)}</span>
              </li>
            )
          })}
        </ul>
      )}
    </Card>
  )
}

