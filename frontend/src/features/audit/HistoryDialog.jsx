import { useEffect, useState } from 'react'
import { api } from '../../api'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Notice from '../../components/ui/Notice'

// FR21: who changed a record, when, and what changed (GET /api/v1/audit/).
const ACTION = {
  create: { label: 'Created', tone: 'success' },
  update: { label: 'Changed', tone: 'info' },
  delete: { label: 'Deleted', tone: 'danger' },
}

const FIELD_LABELS = {
  amount: 'Amount',
  date: 'Date',
  description: 'Description',
  merchant: 'Merchant',
  notes: 'Notes',
  payment_method: 'Payment method',
  category_id: 'Category',
  receipt: 'Receipt',
  is_deleted: 'Deleted',
  name: 'Name',
  limit_amount: 'Limit',
  base_limit_amount: 'Base limit',
  period: 'Period',
  start_date: 'Start date',
  end_date: 'End date',
  rollover_mode: 'At period end',
  role: 'Role',
  user_id: 'Person',
  budget_id: 'Budget',
  owner_id: 'Owner',
  recurring_rule_id: 'Recurring rule',
}

function show(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return String(value)
}

function when(timestamp) {
  return new Date(timestamp).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export default function HistoryDialog({ entity, entityId, title, onClose }) {
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let live = true
    api(`/audit/?entity=${entity}&entity_id=${entityId}&page_size=100`)
      .then((data) => live && setEntries(data.results ?? []))
      .catch((err) => live && setError(err))
    return () => {
      live = false
    }
  }, [entity, entityId])

  return (
    <Modal
      open
      title={`History: ${title}`}
      description="Every change to this record, newest first."
      onClose={onClose}
      footer={<Button onClick={onClose}>Close</Button>}
    >
      <div className="modal-body history-dialog">
        {error && <Notice tone="danger">{error.message}</Notice>}
        {!error && entries === null && <p className="muted">Loading history…</p>}
        {entries?.length === 0 && <p className="muted">No changes recorded yet.</p>}
        {entries?.length > 0 && (
          <ol className="history-list">
            {entries.map((entry) => {
              const action = ACTION[entry.action] ?? { label: entry.action, tone: 'info' }
              return (
                <li key={entry.id} className="history-entry">
                  <div className="history-head">
                    <Badge tone={action.tone}>{action.label}</Badge>
                    <span>
                      <strong>{entry.actor_email ?? 'System'}</strong>
                      <span className="muted"> · {when(entry.created_at)}</span>
                    </span>
                  </div>
                  {entry.action === 'update' && entry.changes.length > 0 && (
                    <table className="history-changes">
                      <caption className="sr-only">Changed fields</caption>
                      <thead>
                        <tr>
                          <th scope="col">Field</th>
                          <th scope="col">Before</th>
                          <th scope="col">After</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entry.changes.map((change) => (
                          <tr key={change.field}>
                            <th scope="row">{FIELD_LABELS[change.field] ?? change.field}</th>
                            <td>{show(change.old)}</td>
                            <td>{show(change.new)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </li>
              )
            })}
          </ol>
        )}
      </div>
    </Modal>
  )
}
