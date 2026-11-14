import { useCallback, useState } from 'react'
import { api, apiDownload, query } from '../api'
import FormField from '../components/FormField'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import ProgressBar from '../components/ui/ProgressBar'
import Skeleton from '../components/ui/Skeleton'
import StatCard from '../components/ui/StatCard'
import useAsync from '../hooks/useAsync'
import {
  addDays,
  endOfMonth,
  formatCurrency,
  formatDate,
  parseISODate,
  startOfMonth,
  toISODate,
  toNumber,
  toneForPercent,
} from '../lib/format'

const MAX_DAYS = 366 // report window cap (NFR2 / ADR 0002)

const PRESETS = [
  { key: 'month', label: 'This month', range: (n) => [startOfMonth(n), n] },
  {
    key: 'last-month',
    label: 'Last month',
    range: (n) => {
      const prev = new Date(n.getFullYear(), n.getMonth() - 1, 1)
      return [prev, endOfMonth(prev)]
    },
  },
  { key: '90d', label: 'Last 90 days', range: (n) => [addDays(n, -89), n] },
  { key: 'ytd', label: 'Year to date', range: (n) => [new Date(n.getFullYear(), 0, 1), n] },
  { key: '12m', label: 'Last 12 months', range: (n) => [addDays(n, -364), n] },
]

function presetRange(key) {
  const [start, end] = PRESETS.find((p) => p.key === key).range(new Date())
  return { start: toISODate(start), end: toISODate(end) }
}

function validate({ start, end }) {
  if (!start || !end) return 'Choose both a start and an end date.'
  if (start > end) return 'The start date cannot be after the end date.'
  const days = Math.round((parseISODate(end) - parseISODate(start)) / 86400000) + 1
  if (days > MAX_DAYS) return 'Reports can cover at most one year (366 days).'
  return null
}

function saveBlob({ blob, filename }) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function ReportsPage() {
  const [preset, setPreset] = useState('month')
  const [draft, setDraft] = useState(() => presetRange('month'))
  const [applied, setApplied] = useState(() => presetRange('month'))
  const [validation, setValidation] = useState(null)
  const [exporting, setExporting] = useState(null)
  const [exportError, setExportError] = useState(null)

  const load = useCallback(
    () => api(`/analytics/reports/${query({ start_date: applied.start, end_date: applied.end })}`),
    [applied],
  )
  const { data, loading, error, reload } = useAsync(load)

  function choosePreset(key) {
    const range = presetRange(key)
    setPreset(key)
    setDraft(range)
    setValidation(null)
    setApplied(range)
  }

  function updateDate(event) {
    setPreset(null)
    setDraft({ ...draft, [event.target.name]: event.target.value })
  }

  function apply(event) {
    event.preventDefault()
    const problem = validate(draft)
    setValidation(problem)
    if (!problem) setApplied(draft)
  }

  async function exportReport(format) {
    setExporting(format)
    setExportError(null)
    try {
      const params = query({ start_date: applied.start, end_date: applied.end, export_format: format })
      saveBlob(await apiDownload(`/analytics/reports/export/${params}`))
    } catch (err) {
      setExportError(err)
    } finally {
      setExporting(null)
    }
  }

  const summary = data?.summary
  const categoryBreakdown = data?.category_breakdown ?? []
  const budgetVsActual = data?.budget_vs_actual ?? []
  const empty = data && toNumber(summary?.total_spend) === 0 && budgetVsActual.length === 0

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Summary, category breakdown and budget vs. actual for any date range.</p>
        </div>
        <div className="page-actions">
          <Button icon="file" loading={exporting === 'pdf'} disabled={Boolean(exporting) || loading || Boolean(error)} onClick={() => exportReport('pdf')}>
            Export PDF
          </Button>
          <Button icon="sheet" loading={exporting === 'xlsx'} disabled={Boolean(exporting) || loading || Boolean(error)} onClick={() => exportReport('xlsx')}>
            Export Excel
          </Button>
        </div>
      </header>

      {exportError && (
        <div className="flash">
          <Notice tone="danger">{exportError.message}</Notice>
        </div>
      )}

      <Card className="report-controls" title="Date range" subtitle="Pick a preset or choose custom dates (up to one year).">
        <div className="chip-row" role="group" aria-label="Date range presets">
          {PRESETS.map((p) => (
            <button key={p.key} type="button" className="pill" aria-pressed={preset === p.key} onClick={() => choosePreset(p.key)}>
              {p.label}
            </button>
          ))}
        </div>
        <form className="toolbar toolbar-inline" onSubmit={apply}>
          <FormField label="From" name="start" type="date" value={draft.start} max={draft.end || undefined} onChange={updateDate} />
          <FormField label="To" name="end" type="date" value={draft.end} min={draft.start || undefined} onChange={updateDate} />
          <Button type="submit" variant="primary">
            Generate report
          </Button>
        </form>
        {validation && <Notice tone="danger">{validation}</Notice>}
      </Card>

      {error ? (
        <Notice tone="danger" action={<Button size="sm" onClick={reload}>Retry</Button>}>
          {error.message}
        </Notice>
      ) : (
        <>
          <section className="grid grid-3 report-stats" aria-label="Report summary">
            <StatCard label="Total spend" icon="wallet" loading={loading} value={formatCurrency(summary?.total_spend)} hint={`${formatDate(applied.start)} – ${formatDate(applied.end)}`} />
            <StatCard label="Transactions" icon="receipt" tone="success" loading={loading} value={summary?.transaction_count ?? 0} hint="in range" />
            <StatCard label="Average spend" icon="bars" tone="info" loading={loading} value={formatCurrency(summary?.average_spend)} hint="per transaction" />
          </section>

          {loading || !data ? (
            <Skeleton height={260} radius="22px" />
          ) : empty ? (
            <div className="card">
              <EmptyState icon="file" title="Nothing to report for this range" description="There are no expenses or budgets in the selected dates. Try a wider range." />
            </div>
          ) : (
            <div className="grid grid-2">
              <Card title="Category breakdown" flush>
                {categoryBreakdown.length === 0 ? (
                  <p className="muted pad">No expenses in this range.</p>
                ) : (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th scope="col">Category</th>
                          <th scope="col" className="num">Txns</th>
                          <th scope="col" className="num">Amount</th>
                          <th scope="col" className="num">Share</th>
                        </tr>
                      </thead>
                      <tbody>
                        {categoryBreakdown.map((row) => (
                          <tr key={row.category_id ?? row.category_name}>
                            <td className="cell-title">{row.category_name}</td>
                            <td className="num">{row.transaction_count}</td>
                            <td className="num">{formatCurrency(row.total_amount)}</td>
                            <td className="num">{toNumber(row.percentage).toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>

              <Card title="Budget vs. actual" flush>
                {budgetVsActual.length === 0 ? (
                  <p className="muted pad">No budgets overlap this range.</p>
                ) : (
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th scope="col">Budget</th>
                          <th scope="col" className="num">Limit</th>
                          <th scope="col" className="num">Actual</th>
                          <th scope="col">Used</th>
                        </tr>
                      </thead>
                      <tbody>
                        {budgetVsActual.map((row) => (
                          <tr key={row.budget_id}>
                            <td>
                              <span className="cell-title">{row.name}</span>
                              <span className="cell-sub block">{row.category_name}</span>
                            </td>
                            <td className="num">{formatCurrency(row.limit_amount, { whole: true })}</td>
                            <td className="num">{formatCurrency(row.actual_spent, { whole: true })}</td>
                            <td className="used-cell">
                              <ProgressBar percent={row.utilization_percentage} label={`${row.name} used`} />
                              <Badge tone={toneForPercent(row.utilization_percentage)}>{Math.round(row.utilization_percentage)}%</Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </div>
          )}
        </>
      )}
    </>
  )
}

