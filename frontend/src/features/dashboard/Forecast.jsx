import { useCallback } from 'react'
import { api } from '../../api'
import Badge from '../../components/ui/Badge'
import Card from '../../components/ui/Card'
import Icon from '../../components/ui/Icon'
import ProgressBar from '../../components/ui/ProgressBar'
import Skeleton from '../../components/ui/Skeleton'
import useAsync from '../../hooks/useAsync'
import { formatCurrency, toNumber } from '../../lib/format'

const STATUS = {
  on_track: { tone: 'success', label: 'On track' },
  at_risk: { tone: 'warning', label: 'At risk' },
  over_budget: { tone: 'danger', label: 'Over budget' },
  no_budget: { tone: 'info', label: 'No monthly budget' },
}

// Projected month-end spend from the current daily burn rate (FR14).
export default function Forecast() {
  const load = useCallback(() => api('/analytics/predictive-insights/'), [])
  const { data, loading, error } = useAsync(load)
  const status = STATUS[data?.status] ?? STATUS.no_budget

  const limit = toNumber(data?.active_monthly_budget_limit)
  const projected = toNumber(data?.projected_month_end_spend)
  const percent = limit > 0 ? (projected / limit) * 100 : 0
  const overrun = toNumber(data?.projected_overrun)

  return (
    <Card
      title="Month-end forecast"
      subtitle="Based on your current daily spend"
      action={data && <Badge tone={status.tone}>{status.label}</Badge>}
    >
      {loading ? (
        <>
          <Skeleton height={40} width="55%" />
          <Skeleton height={12} style={{ marginTop: 20 }} />
          <Skeleton height={64} style={{ marginTop: 20 }} />
        </>
      ) : error ? (
        <p className="muted">Could not load the forecast. {error.message}</p>
      ) : (
        <div className="forecast">
          <div className="forecast-hero">
            <span className="forecast-icon">
              <Icon name="zap" size={20} />
            </span>
            <div>
              <p className="forecast-label">Projected spend by month end</p>
              <p className="forecast-value">{formatCurrency(projected, { whole: true })}</p>
            </div>
          </div>

          {limit > 0 ? (
            <div className="forecast-budget">
              <div className="forecast-budget-row">
                <span>Monthly budget {formatCurrency(limit, { whole: true })}</span>
                <strong data-over={overrun > 0}>
                  {overrun > 0 ? `${formatCurrency(overrun, { whole: true })} over` : `${formatCurrency(Math.abs(overrun), { whole: true })} spare`}
                </strong>
              </div>
              <ProgressBar percent={percent} label="Projected share of monthly budget" />
            </div>
          ) : (
            <p className="muted forecast-note">Create a monthly budget to see how your forecast compares.</p>
          )}

          <dl className="mini-stats">
            <div>
              <dt>Spent so far</dt>
              <dd>{formatCurrency(data.total_spent_so_far, { whole: true })}</dd>
            </div>
            <div>
              <dt>Daily average</dt>
              <dd>{formatCurrency(data.daily_average_spend, { whole: true })}</dd>
            </div>
            <div>
              <dt>Days left</dt>
              <dd>{data.days_remaining}</dd>
            </div>
          </dl>
        </div>
      )}
    </Card>
  )
}

