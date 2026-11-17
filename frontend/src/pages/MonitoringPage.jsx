import { useCallback } from 'react'
import { api } from '../api'
import useAsync from '../hooks/useAsync'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { statusLabel, statusTone } from '../features/monitoring/status'

function Status({ status }) {
  return <Badge tone={statusTone(status)}>{statusLabel(status)}</Badge>
}

function JobCard({ title, job }) {
  return (
    <Card title={title} action={<Status status={job?.status ?? 'unknown'} />}>
      <p>{job?.message ?? 'No status is available.'}</p>
      {job?.job && <p className="muted">Last job: {job.job}</p>}
      {job?.updated_at && <p className="muted">Updated: {new Date(job.updated_at).toLocaleString()}</p>}
    </Card>
  )
}

export default function MonitoringPage() {
  const load = useCallback(() => api('/monitoring/'), [])
  const { data, error, loading, reload } = useAsync(load)

  if (loading && !data) return <p role="status">Loading monitoring status…</p>
  if (error) {
    return (
      <Card title="Monitoring unavailable">
        <p role="alert">{error.message}</p>
        <Button onClick={reload}>Retry</Button>
      </Card>
    )
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <h1>System monitoring</h1>
          <p className="muted">Operational status and recent service signals.</p>
        </div>
        <Button variant="secondary" onClick={reload}>Refresh</Button>
      </div>

      <div className="monitoring-grid">
        <Card title="Backend application" action={<Status status={data.backend.status} />}>
          <p>Health endpoint responds to API requests.</p>
          <p className="muted">Checked: {new Date(data.checked_at).toLocaleString()}</p>
        </Card>
        <Card title="Database" action={<Status status={data.database.status} />}>
          <p>Connectivity is verified with a database query.</p>
        </Card>
        <JobCard title="Budget scheduler" job={data.budget_scheduler} />
        <JobCard title="Database backup" job={data.backup} />
        <Card title="HTTP error monitoring">
          <p>
            {data.errors.error_count} of {data.errors.request_count} requests failed with HTTP 5xx
            ({data.errors.error_rate_percent}%) in the last {data.errors.window_seconds}s.
          </p>
          <p>{data.errors.slow_request_count} slow requests in the same window.</p>
        </Card>
        <Card title="Failed email delivery">
          {data.email.latest_failures.length ? (
            <ul className="monitoring-failures">
              {data.email.latest_failures.map((failure) => (
                <li key={`${failure.created_at}-${failure.request_id}`}>
                  <strong>{failure.subject || 'Email delivery failure'}</strong>
                  <span>{failure.reason}</span>
                  {failure.recipient && <span>Recipient: {failure.recipient}</span>}
                  {failure.request_id && <code>Request ID: {failure.request_id}</code>}
                  <time dateTime={failure.created_at}>{new Date(failure.created_at).toLocaleString()}</time>
                </li>
              ))}
            </ul>
          ) : (
            <p>No recorded email delivery failures.</p>
          )}
        </Card>
      </div>
    </div>
  )
}
