import Icon from './Icon'
import Skeleton from './Skeleton'

// KPI tile. `delta` is a % change vs the previous period (null hides it);
// `invertDelta` marks an increase as bad (e.g. spending).
export default function StatCard({ label, value, hint, icon, tone = 'primary', delta = null, invertDelta = false, loading = false }) {
  const up = delta !== null && delta >= 0
  const good = invertDelta ? !up : up

  return (
    <article className="card stat">
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        {icon && (
          <span className="stat-icon" data-tone={tone}>
            <Icon name={icon} size={18} />
          </span>
        )}
      </div>
      {loading ? (
        <>
          <Skeleton height={32} width="60%" style={{ marginTop: 14 }} />
          <Skeleton height={14} width="45%" style={{ marginTop: 12 }} />
        </>
      ) : (
        <>
          <div className="stat-value" title={typeof value === 'string' ? value : undefined}>
            {value}
          </div>
          <div className="stat-foot">
            {delta !== null && (
              <span className="badge" data-tone={good ? 'success' : 'danger'}>
                <Icon name={up ? 'trendUp' : 'trendDown'} size={13} />
                {Math.abs(delta).toFixed(1)}%
              </span>
            )}
            {hint && <span>{hint}</span>}
          </div>
        </>
      )}
    </article>
  )
}

