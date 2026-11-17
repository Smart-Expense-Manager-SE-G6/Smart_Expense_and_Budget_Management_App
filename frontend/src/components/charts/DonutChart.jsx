import { formatCurrency } from '../../lib/format'

const SIZE = 200
const STROKE = 22
const R = (SIZE - STROKE) / 2
const C = 2 * Math.PI * R
const GAP = 3

// data: [{ label, value, color }]. Segments are drawn as dash arcs on one circle.
export default function DonutChart({ data, total, centerLabel = 'Total spent' }) {
  const sum = data.reduce((acc, d) => acc + d.value, 0) || 1
  let offset = 0

  return (
    <div className="donut" role="img" aria-label={`${centerLabel}: ${formatCurrency(total)}`}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%" height="100%">
        <circle cx={SIZE / 2} cy={SIZE / 2} r={R} fill="none" stroke="var(--surface-hover)" strokeWidth={STROKE} />
        <g transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
          {data.map((d) => {
            const length = Math.max((d.value / sum) * C - (data.length > 1 ? GAP : 0), 0)
            const circle = (
              <circle
                key={d.label}
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={R}
                fill="none"
                stroke={d.color}
                strokeWidth={STROKE}
                strokeLinecap="butt"
                strokeDasharray={`${length} ${C - length}`}
                strokeDashoffset={-offset}
                className="donut-seg"
              >
                <title>{`${d.label}: ${formatCurrency(d.value)}`}</title>
              </circle>
            )
            offset += (d.value / sum) * C
            return circle
          })}
        </g>
      </svg>
      <div className="donut-center">
        <span className="donut-center-label">{centerLabel}</span>
        <strong className="donut-center-value">{formatCurrency(total, { whole: true })}</strong>
      </div>
    </div>
  )
}

