export function statusLabel(status) {
  const labels = {
    healthy: 'Healthy',
    failed: 'Failed',
    unhealthy: 'Unhealthy',
    running: 'Running',
    starting: 'Starting',
    stale: 'Stale',
    unknown: 'Unknown',
  }
  return labels[status] ?? 'Unknown'
}

export function statusTone(status) {
  if (status === 'healthy') return 'success'
  if (status === 'failed' || status === 'unhealthy') return 'danger'
  if (status === 'stale' || status === 'running') return 'warning'
  return 'info'
}
