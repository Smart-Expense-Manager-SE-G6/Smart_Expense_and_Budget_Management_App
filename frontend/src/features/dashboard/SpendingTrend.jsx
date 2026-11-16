import { useCallback, useMemo, useState } from 'react'
import { api } from '../../api'
import TrendChart from '../../components/charts/TrendChart'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import Icon from '../../components/ui/Icon'
import Segmented from '../../components/ui/Segmented'
import Skeleton from '../../components/ui/Skeleton'
import useAsync from '../../hooks/useAsync'
import { formatMonthLabel, toNumber } from '../../lib/format'

const MONTHS = 6
const YEARS = 3

const GRANULARITY_OPTIONS = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'yearly', label: 'Yearly' },
]

// Month-over-month and year-over-year spending comparison (FR13, FR15).
export default function SpendingTrend() {
  const [granularity, setGranularity] = useState('monthly')

  const load = useCallback(
    () =>
      granularity === 'yearly'
        ? api(`/analytics/comparison/?granularity=yearly&years=${YEARS}`)
        : api(`/analytics/comparison/?granularity=monthly&months=${MONTHS}`),
    [granularity],
  )
  const { data, loading, error } = useAsync(load)

  const { points, latest } = useMemo(() => {
    const periods = data?.periods ?? []
    return {
      points: periods.map((p) => {
        const isYear = granularity === 'yearly' || /^\d{4}$/.test(String(p.period))
        return {
          label: isYear
            ? String(p.period)
            : new Date(`${p.period}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }),
          axisLabel: isYear ? String(p.period) : formatMonthLabel(p.period),
          value: toNumber(p.total_amount),
        }
      }),
      latest: periods.at(-1),
    }
  }, [data, granularity])

  const hasSpend = points.some((p) => p.value > 0)
  const change = latest?.change_percentage
  const unitLabel = granularity === 'yearly' ? 'last year' : 'last month'

  return (
    <Card
      title="Spending trend"
      subtitle={granularity === 'yearly' ? `Last ${YEARS} years` : `Last ${MONTHS} months`}
      action={
        <div className="toolbar-inline">
          {change !== null && change !== undefined && (
            <Badge tone={change > 0 ? 'danger' : 'success'} icon={<Icon name={change > 0 ? 'trendUp' : 'trendDown'} size={13} />}>
              {Math.abs(change).toFixed(1)}% vs {unitLabel}
            </Badge>
          )}
          <Segmented value={granularity} onChange={setGranularity} options={GRANULARITY_OPTIONS} ariaLabel="Comparison granularity" />
        </div>
      }
    >
      {loading ? (
        <Skeleton height={240} radius="12px" />
      ) : error ? (
        <p className="muted">Could not load the trend. {error.message}</p>
      ) : !hasSpend ? (
        <EmptyState
          icon="bars"
          title="No spending history yet"
          description={`Add a few expenses and your ${granularity} trend will appear here.`}
        />
      ) : (
        <TrendChart
          points={points}
          ariaLabel={granularity === 'yearly' ? 'Yearly spending for the last three years' : 'Monthly spending for the last six months'}
        />
      )}
    </Card>
  )
}

