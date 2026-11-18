import { useState } from 'react'
import { formatCurrency } from '../../lib/format'

const SIZE = 200
const STROKE = 22
const R = (SIZE - STROKE) / 2
const C = 2 * Math.PI * R
const GAP = 3

// data: [{ label, value, color }]. Segments are drawn as dash arcs on one circle.
export default function DonutChart({ data, total, centerLabel = 'Total spent' }) {
  const [hovered, setHovered] = useState(null)
  const sum = data.reduce((acc, d) => acc + d.value, 0) || 1
  let offset = 0

  const active = hovered !== null ? data[hovered] : null
  const activePct = active ? ((active.value / sum) * 100).toFixed(1) : null

  return (
    <div className="donut" role="img" aria-label={`${centerLabel}: ${formatCurrency(total)}`}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%" height="100%">
        <circle cx={SIZE / 2} cy={SIZE / 2} r={R} fill="none" stroke="var(--surface-hover)" strokeWidth={STROKE} />
        <g transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
          {data.map((d, idx) => {
            const length = Math.max((d.value / sum) * C - (data.length > 1 ? GAP : 0), 0)
            const isHovered = hovered === idx
            const dimmed = hovered !== null && !isHovered
            const circle = (
              <circle
                key={d.label}
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={R}
                fill="none"
                stroke={d.color}
                strokeWidth={isHovered ? STROKE + 4 : STROKE}
                strokeLinecap="butt"
                strokeDasharray={`${length} ${C - length}`}
                strokeDashoffset={-offset}
                className="donut-seg"
                style={{ opacity: dimmed ? 0.35 : 1 }}
                onMouseEnter={() => setHovered(idx)}
                onMouseLeave={() => setHovered(null)}
              >
                <title>{`${d.label}: ${formatCurrency(d.value)} (${((d.value / sum) * 100).toFixed(1)}%)`}</title>
              </circle>
            )
            offset += (d.value / sum) * C
            return circle
          })}
        </g>
      </svg>
      <div className="donut-center">
        <span className="donut-center-label">{active ? active.label : centerLabel}</span>
        <strong className="donut-center-value">
          {formatCurrency(active ? active.value : total, { whole: true })}
        </strong>
        {activePct && <span className="donut-center-sub">{activePct}% of total</span>}
      </div>
      <ul className="sr-only">
        {data.map((d) => <li key={d.label}>{d.label}: {formatCurrency(d.value)}</li>)}
      </ul>
    </div>
  )
}

