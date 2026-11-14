import { useCallback, useMemo } from 'react'
import { api } from '../../api'
import TrendChart from '../../components/charts/TrendChart'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import EmptyState from '../../components/ui/EmptyState'
import Icon from '../../components/ui/Icon'
import Skeleton from '../../components/ui/Skeleton'
import useAsync from '../../hooks/useAsync'
import { formatMonthLabel, toNumber } from '../../lib/format'

const MONTHS = 6

// Month-over-month spending (FR13, FR15).
export default function SpendingTrend() {
  const load = useCallback(() => api(`/analytics/comparison/?granularity=monthly&months=${MONTHS}`), [])
  const { data, loading, error } = useAsync(load)

  const { points, latest } = useMemo(() => {
    const periods = data?.periods ?? []
    return {
      points: periods.map((p) => ({
        label: new Date(`${p.period}-01T00:00:00`).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }),
        axisLabel: formatMonthLabel(p.period),
        value: toNumber(p.total_amount),
      })),
      latest: periods.at(-1),
    }
  }, [data])

  const hasSpend = points.some((p) => p.value > 0)
  const change = latest?.change_percentage

  return (
    <Card
      title="Spending trend"
      subtitle={`Last ${MONTHS} months`}
      action={
        change !== null && change !== undefined ? (
          <Badge tone={change > 0 ? 'danger' : 'success'} icon={<Icon name={change > 0 ? 'trendUp' : 'trendDown'} size={13} />}>
            {Math.abs(change).toFixed(1)}% vs last month
          </Badge>
        ) : null
      }
    >
      {loading ? (
        <Skeleton height={240} radius="12px" />
      ) : error ? (
        <p className="muted">Could not load the trend. {error.message}</p>
      ) : !hasSpend ? (
        <EmptyState icon="bars" title="No spending history yet" description="Add a few expenses and your monthly trend will appear here." />
      ) : (
        <TrendChart points={points} ariaLabel="Monthly spending for the last six months" />
      )}
    </Card>
  )
}

