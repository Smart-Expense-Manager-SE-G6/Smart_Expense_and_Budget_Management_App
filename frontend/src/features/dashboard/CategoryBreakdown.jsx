import { useCallback, useMemo } from 'react'
import { api, query } from '../../api'
import DonutChart from '../../components/charts/DonutChart'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import Skeleton from '../../components/ui/Skeleton'
import useAsync from '../../hooks/useAsync'
import { formatCurrency, paletteColor, toNumber } from '../../lib/format'

const MAX_SLICES = 6

// Spending split by category (FR13). Smaller categories are grouped into "Other".
export default function CategoryBreakdown({ start, end }) {
  const load = useCallback(() => api(`/analytics/by-category/${query({ start_date: start, end_date: end })}`), [start, end])
  const { data, loading, error } = useAsync(load)

  const slices = useMemo(() => {
    const rows = (data?.categories ?? []).map((c) => ({
      label: c.category_name,
      value: toNumber(c.total_amount),
      percentage: c.percentage,
      count: c.transaction_count,
    }))
    const head = rows.slice(0, MAX_SLICES)
    const rest = rows.slice(MAX_SLICES)
    if (rest.length) {
      head.push({
        label: 'Other',
        value: rest.reduce((sum, r) => sum + r.value, 0),
        percentage: rest.reduce((sum, r) => sum + r.percentage, 0),
        count: rest.reduce((sum, r) => sum + r.count, 0),
      })
    }
    return head.map((slice, i) => ({ ...slice, color: paletteColor(i) }))
  }, [data])

  return (
    <Card title="Spending by category" subtitle="Share of total spend in the selected period">
      {loading ? (
        <div className="donut-layout">
          <Skeleton height={200} width={200} radius="50%" />
          <div className="legend">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} height={18} />
            ))}
          </div>
        </div>
      ) : error ? (
        <p className="muted">Could not load the breakdown. {error.message}</p>
      ) : slices.length === 0 ? (
        <EmptyState icon="tag" title="No expenses in this period" description="Pick a longer period or add an expense to see your category split." />
      ) : (
        <div className="donut-layout">
          <DonutChart data={slices} total={toNumber(data.total_spend)} />
          <ul className="legend">
            {slices.map((slice) => (
              <li key={slice.label} className="legend-item">
                <span className="dot" style={{ '--dot': slice.color }} />
                <span className="legend-name">{slice.label}</span>
                <span className="legend-pct">{slice.percentage.toFixed(1)}%</span>
                <span className="legend-amt">{formatCurrency(slice.value, { whole: true })}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}

