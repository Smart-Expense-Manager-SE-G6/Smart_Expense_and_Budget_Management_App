import { useCallback } from 'react'
import { api, query } from '../../api'
import StatCard from '../../components/ui/StatCard'
import useAsync from '../../hooks/useAsync'
import { formatCurrency, pctChange, previousRange } from '../../lib/format'

// Headline KPIs for the selected period, with a delta against the preceding period of equal length.
export default function SummaryCards({ start, end }) {
  const load = useCallback(async () => {
    const range = { start_date: start, end_date: end }
    const [current, previous] = await Promise.all([
      api(`/analytics/summary/${query(range)}`),
      api(`/analytics/summary/${query(previousRange(range))}`).catch(() => null),
    ])
    return { current, previous }
  }, [start, end])

  const { data, loading, error } = useAsync(load)
  const current = data?.current
  const previous = data?.previous

  if (error) {
    return (
      <section className="grid grid-4" aria-label="Key metrics">
        <p className="muted">Could not load your summary. {error.message}</p>
      </section>
    )
  }

  return (
    <section className="grid grid-4" aria-label="Key metrics">
      <StatCard
        label="Total spending"
        icon="wallet"
        loading={loading}
        value={formatCurrency(current?.total_spend)}
        delta={previous ? pctChange(current?.total_spend, previous.total_spend) : null}
        invertDelta
        hint="vs previous period"
      />
      <StatCard
        label="Average expense"
        icon="bars"
        tone="info"
        loading={loading}
        value={formatCurrency(current?.average_expense)}
        delta={previous ? pctChange(current?.average_expense, previous.average_expense) : null}
        invertDelta
        hint="per transaction"
      />
      <StatCard
        label="Transactions"
        icon="receipt"
        tone="success"
        loading={loading}
        value={current?.transaction_count ?? 0}
        delta={previous ? pctChange(current?.transaction_count, previous.transaction_count) : null}
        invertDelta
        hint="logged this period"
      />
      <StatCard
        label="Top category"
        icon="trophy"
        tone="warning"
        loading={loading}
        value={current?.top_category?.name ?? '—'}
        hint={current?.top_category ? `${formatCurrency(current.top_category.total_amount)} spent` : 'No expenses yet'}
      />
    </section>
  )
}

