import { useCallback, useEffect, useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth/context'
import FormField from '../../components/FormField'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Notice from '../../components/ui/Notice'
import { formatCurrency, formatDate } from '../../lib/format'

const ROLE_LABEL = { owner: 'Owner', admin: 'Admin', member: 'Member' }

// Shared budgets (FR3): who shares a budget, what they spent, and member management.
// Owners and admins add, re-role and remove members; members can see everything and leave.
export default function BudgetMembersDialog({ budget, onClose, onChanged }) {
  const { user } = useAuth()
  const [members, setMembers] = useState([])
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ email: '', role: 'member' })
  const [busy, setBusy] = useState(false)

  const canManage = budget?.role === 'owner' || budget?.role === 'admin'

  const load = useCallback(async () => {
    if (!budget) return
    setLoading(true)
    try {
      const [memberList, spend] = await Promise.all([
        api(`/budgets/${budget.id}/members/`),
        api(`/budgets/${budget.id}/expenses/?page_size=5`),
      ])
      setMembers(memberList)
      setExpenses(spend?.results ?? [])
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [budget])

  useEffect(() => {
    load()
  }, [load])

  async function run(action) {
    setBusy(true)
    setError(null)
    try {
      await action()
      await load()
      onChanged?.()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  function addMember(event) {
    event.preventDefault()
    run(async () => {
      await api(`/budgets/${budget.id}/members/`, { method: 'POST', body: form })
      setForm({ email: '', role: 'member' })
    })
  }

  const changeRole = (member, role) =>
    run(() => api(`/budgets/${budget.id}/members/${member.id}/`, { method: 'PATCH', body: { role } }))

  const removeMember = (member) => run(() => api(`/budgets/${budget.id}/members/${member.id}/`, { method: 'DELETE' }))

  async function leave(member) {
    setBusy(true)
    try {
      await api(`/budgets/${budget.id}/members/${member.id}/`, { method: 'DELETE' })
      onChanged?.()
      onClose()
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  if (!budget) return null
  const fieldError = (name) => (error?.field === name ? error.message : null)

  return (
    <Modal
      open
      title={`Sharing: ${budget.name}`}
      description="Everyone here can see this budget. Their expenses count towards it."
      onClose={onClose}
      footer={<Button onClick={onClose}>Close</Button>}
    >
      <div className="modal-body share-dialog">
        {error && !['email', 'role'].includes(error.field) && <Notice tone="danger">{error.message}</Notice>}

        <section aria-labelledby="share-people">
          <h3 id="share-people" className="share-heading">
            People
          </h3>
          <ul className="share-list">
            <li className="share-row">
              <span className="share-person">
                <strong>{budget.owner_email}</strong>
                {budget.role === 'owner' && <span className="muted"> (you)</span>}
              </span>
              <Badge tone="primary">{ROLE_LABEL.owner}</Badge>
            </li>
            {loading ? (
              <li className="share-row muted">Loading members…</li>
            ) : (
              members.map((member) => {
                const isMe = member.user === user?.id
                return (
                  <li key={member.id} className="share-row">
                    <span className="share-person">
                      <strong>{member.email}</strong>
                      {member.name && <span className="muted"> · {member.name}</span>}
                      {isMe && <span className="muted"> (you)</span>}
                    </span>
                    <span className="share-actions">
                      {canManage ? (
                        <>
                          <label className="sr-only" htmlFor={`role-${member.id}`}>
                            Role for {member.email}
                          </label>
                          <select
                            id={`role-${member.id}`}
                            value={member.role}
                            disabled={busy}
                            onChange={(event) => changeRole(member, event.target.value)}
                          >
                            <option value="member">Member</option>
                            <option value="admin">Admin</option>
                          </select>
                          <Button variant="ghost" size="sm" disabled={busy} onClick={() => removeMember(member)}
                            aria-label={`Remove ${member.email}`}>
                            Remove
                          </Button>
                        </>
                      ) : (
                        <>
                          <Badge>{ROLE_LABEL[member.role]}</Badge>
                          {isMe && (
                            <Button variant="ghost" size="sm" disabled={busy} onClick={() => leave(member)}>
                              Leave budget
                            </Button>
                          )}
                        </>
                      )}
                    </span>
                  </li>
                )
              })
            )}
          </ul>
          {!loading && members.length === 0 && <p className="muted">Not shared with anyone yet.</p>}
        </section>

        {canManage && (
          <form className="share-add form" onSubmit={addMember} noValidate>
            <h3 className="share-heading">Add someone</h3>
            <div className="field-row">
              <FormField label="Email" name="email" type="email" autoComplete="off" required placeholder="name@example.com"
                value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })}
                error={fieldError('email')} hint="They need an account already." />
              <FormField as="select" label="Role" name="role" value={form.role}
                onChange={(event) => setForm({ ...form, role: event.target.value })} error={fieldError('role')}>
                <option value="member">Member: view and add expenses</option>
                <option value="admin">Admin: also edit and manage members</option>
              </FormField>
            </div>
            <Button type="submit" variant="primary" icon="plus" loading={busy}>
              Add to budget
            </Button>
          </form>
        )}

        <section aria-labelledby="share-spend">
          <h3 id="share-spend" className="share-heading">
            Recent spending on this budget
          </h3>
          {expenses.length === 0 ? (
            <p className="muted">No expenses in this period yet.</p>
          ) : (
            <ul className="share-list">
              {expenses.map((expense) => (
                <li key={expense.id} className="share-row">
                  <span className="share-person">
                    <strong>{expense.description || expense.category_name || 'Expense'}</strong>
                    <span className="muted">
                      {' '}
                      · {expense.owner_email} · {formatDate(expense.date, { day: 'numeric', month: 'short' })}
                    </span>
                  </span>
                  <span>{formatCurrency(expense.amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </Modal>
  )
}
