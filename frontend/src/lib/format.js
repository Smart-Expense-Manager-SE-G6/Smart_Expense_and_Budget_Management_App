// Formatting + date helpers shared across the app. All dates are handled as local
// calendar days (YYYY-MM-DD), never via toISOString(), which shifts the day for
// users ahead of UTC (e.g. India after 18:30 UTC).

const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const currencyWhole = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const compactFormatter = new Intl.NumberFormat('en-IN', {
  notation: 'compact',
  maximumFractionDigits: 1,
})

export function toNumber(value) {
  const n = typeof value === 'number' ? value : parseFloat(value)
  return Number.isFinite(n) ? n : 0
}

export function formatCurrency(value, { whole = false } = {}) {
  return (whole ? currencyWhole : currencyFormatter).format(toNumber(value))
}

export function formatCompact(value) {
  return compactFormatter.format(toNumber(value))
}

export function formatPercent(value, digits = 0) {
  return `${toNumber(value).toFixed(digits)}%`
}

export function toISODate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function parseISODate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function addDays(date, days) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

export function formatDate(iso, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!iso) return ''
  return parseISODate(iso.slice(0, 10)).toLocaleDateString('en-IN', options)
}

export function formatShortDate(iso) {
  return formatDate(iso, { day: 'numeric', month: 'short' })
}

export function formatMonthLabel(label) {
  // "2026-09" -> "Sep"; "2026" -> "2026"
  if (!/^\d{4}-\d{2}$/.test(label)) return label
  const [y, m] = label.split('-').map(Number)
  return new Date(y, m - 1, 1).toLocaleDateString('en-IN', { month: 'short' })
}

export function timeAgo(isoTimestamp) {
  const seconds = Math.round((Date.now() - new Date(isoTimestamp).getTime()) / 1000)
  if (!Number.isFinite(seconds)) return ''
  const steps = [
    [60, 'second'],
    [3600, 'minute', 60],
    [86400, 'hour', 3600],
    [604800, 'day', 86400],
  ]
  if (seconds < 45) return 'just now'
  for (const [limit, unit, divisor = 1] of steps) {
    if (seconds < limit) {
      const value = Math.max(1, Math.round(seconds / divisor))
      return `${value} ${unit}${value > 1 ? 's' : ''} ago`
    }
  }
  return formatDate(isoTimestamp)
}

export function greeting(date = new Date()) {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export function startOfMonth(date = new Date()) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

export function endOfMonth(date = new Date()) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0)
}

// Date range presets used by the dashboard and reports pages.
export const PERIODS = {
  month: { label: 'This month', range: (now) => [startOfMonth(now), now] },
  '30d': { label: 'Last 30 days', range: (now) => [addDays(now, -29), now] },
  ytd: { label: 'Year to date', range: (now) => [new Date(now.getFullYear(), 0, 1), now] },
}

export function rangeFor(periodKey, now = new Date()) {
  const [start, end] = PERIODS[periodKey].range(now)
  return { start_date: toISODate(start), end_date: toISODate(end) }
}

// The window of equal length immediately before the given one (for period-over-period deltas).
export function previousRange({ start_date, end_date }) {
  const start = parseISODate(start_date)
  const end = parseISODate(end_date)
  const days = Math.round((end - start) / 86400000) + 1
  return {
    start_date: toISODate(addDays(start, -days)),
    end_date: toISODate(addDays(start, -1)),
  }
}

export function pctChange(current, previous) {
  const prev = toNumber(previous)
  if (prev <= 0) return null
  return ((toNumber(current) - prev) / prev) * 100
}

export const PAYMENT_METHODS = [
  { value: 'upi', label: 'UPI' },
  { value: 'credit_card', label: 'Credit card' },
  { value: 'debit_card', label: 'Debit card' },
  { value: 'net_banking', label: 'Net banking' },
  { value: 'cash', label: 'Cash' },
  { value: 'other', label: 'Other' },
]

export function paymentLabel(value) {
  if (!value) return '—'
  return PAYMENT_METHODS.find((m) => m.value === value)?.label ?? value.replace(/_/g, ' ')
}

const PALETTE = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--chart-6)',
  'var(--chart-7)',
  'var(--chart-8)',
]

// Stable colour per category id so the same category looks the same on every screen.
export function categoryColor(key) {
  const str = String(key ?? 'none')
  let hash = 0
  for (let i = 0; i < str.length; i += 1) hash = (hash * 31 + str.charCodeAt(i)) >>> 0
  return PALETTE[hash % PALETTE.length]
}

export function paletteColor(index) {
  return PALETTE[index % PALETTE.length]
}

export function initials(user) {
  const first = user?.first_name?.trim()?.[0]
  const last = user?.last_name?.trim()?.[0]
  if (first || last) return `${first ?? ''}${last ?? ''}`.toUpperCase()
  return (user?.email?.[0] ?? '?').toUpperCase()
}

export function displayName(user) {
  const full = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return full || user?.email?.split('@')[0] || 'there'
}

// Budget thresholds follow FR16: 80% = warning, 100% = exceeded.
export function toneForPercent(percent) {
  if (percent >= 100) return 'danger'
  if (percent >= 80) return 'warning'
  return 'success'
}
