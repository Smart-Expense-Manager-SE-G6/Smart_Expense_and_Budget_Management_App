import { useId, useState } from 'react'
import { formatCompact, formatCurrency } from '../../lib/format'

const W = 640
const H = 240
const PAD = { top: 20, right: 16, bottom: 32, left: 44 }

// Rounds the axis maximum up to 1, 2, 5 or 10 × a power of ten.
function niceCeil(max) {
  const exp = 10 ** Math.floor(Math.log10(max))
  const n = max / exp
  const factor = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10
  return factor * exp
}

// Smooth area/line chart. points: [{ label, value }]
export default function TrendChart({ points, ariaLabel = 'Spending trend' }) {
  const gradientId = useId()
  const [hover, setHover] = useState(null)

  if (points.length === 0) return null

  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const max = Math.max(...points.map((p) => p.value), 1)
  const niceMax = niceCeil(max)
  const step = points.length > 1 ? innerW / (points.length - 1) : 0

  const coords = points.map((p, i) => ({
    x: PAD.left + (points.length > 1 ? i * step : innerW / 2),
    y: PAD.top + innerH - (p.value / niceMax) * innerH,
    ...p,
  }))

  // Catmull-Rom → cubic Bézier for a smooth curve without overshoot dependencies.
  const linePath = coords.reduce((path, p, i, arr) => {
    if (i === 0) return `M ${p.x} ${p.y}`
    const p0 = arr[i - 2] ?? arr[i - 1]
    const p1 = arr[i - 1]
    const p3 = arr[i + 1] ?? p
    const c1x = p1.x + (p.x - p0.x) / 6
    const c1y = p1.y + (p.y - p0.y) / 6
    const c2x = p.x - (p3.x - p1.x) / 6
    const c2y = p.y - (p3.y - p1.y) / 6
    return `${path} C ${c1x} ${Math.min(Math.max(c1y, PAD.top), PAD.top + innerH)}, ${c2x} ${Math.min(Math.max(c2y, PAD.top), PAD.top + innerH)}, ${p.x} ${p.y}`
  }, '')
  const baseline = PAD.top + innerH
  const areaPath = `${linePath} L ${coords.at(-1).x} ${baseline} L ${coords[0].x} ${baseline} Z`

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => ({ y: PAD.top + innerH - t * innerH, value: t * niceMax }))
  const active = hover === null ? null : coords[hover]

  return (
    <div className="trend">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity="0.32" />
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {ticks.map((t) => (
          <g key={t.y}>
            <line x1={PAD.left} x2={W - PAD.right} y1={t.y} y2={t.y} stroke="var(--border)" strokeDasharray="3 5" />
            <text x={PAD.left - 10} y={t.y + 4} textAnchor="end" className="trend-axis">
              {formatCompact(t.value)}
            </text>
          </g>
        ))}

        <path d={areaPath} fill={`url(#${gradientId})`} />
        <path d={linePath} fill="none" stroke="var(--chart-1)" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round" />

        {coords.map((p, i) => (
          <g key={p.label}>
            <text x={p.x} y={H - 10} textAnchor="middle" className="trend-axis">
              {p.axisLabel ?? p.label}
            </text>
            <rect
              x={p.x - Math.max(step / 2, 14)}
              y={PAD.top}
              width={Math.max(step, 28)}
              height={innerH}
              fill="transparent"
              onMouseEnter={() => setHover(i)}
              onFocus={() => setHover(i)}
              tabIndex={0}
              aria-label={`${p.label}: ${formatCurrency(p.value)}`}
            />
            <circle
              cx={p.x}
              cy={p.y}
              r={hover === i ? 6 : 3.5}
              fill="var(--surface)"
              stroke="var(--chart-1)"
              strokeWidth="2.5"
              style={{ transition: 'r 120ms ease' }}
              pointerEvents="none"
            />
          </g>
        ))}

        {active && <line x1={active.x} x2={active.x} y1={PAD.top} y2={baseline} stroke="var(--chart-1)" strokeOpacity="0.35" strokeDasharray="3 4" pointerEvents="none" />}
      </svg>

      {active && (
        <div className="trend-tip" style={{ left: `${(active.x / W) * 100}%`, top: `${(active.y / H) * 100}%` }}>
          <span>{active.label}</span>
          <strong>{formatCurrency(active.value)}</strong>
        </div>
      )}
    </div>
  )
}
