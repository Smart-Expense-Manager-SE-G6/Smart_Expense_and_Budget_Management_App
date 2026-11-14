import { toneForPercent } from '../../lib/format'

export default function ProgressBar({ percent, tone, label }) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0))
  return (
    <div
      className="progress"
      data-tone={tone ?? toneForPercent(percent)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
      aria-label={label}
    >
      <div className="progress-bar" style={{ '--value': `${clamped}%` }} />
    </div>
  )
}
