import { useEffect, useState } from 'react'
import { api } from '../api'
import FormField from '../components/FormField'
import Button from '../components/ui/Button'
import Notice from '../components/ui/Notice'
import { PAYMENT_METHODS, toISODate } from '../lib/format'

const EMPTY = {
  amount: '',
  category: '',
  payment_method: 'upi',
  merchant: '',
  notes: '',
  frequency: 'monthly',
  start_date: toISODate(new Date()),
  end_date: '',
}

function ruleState(rule) {
  return {
    amount: rule?.amount ?? '',
    category: rule?.category ? String(rule.category) : '',
    payment_method: rule?.payment_method ?? 'upi',
    merchant: rule?.merchant ?? '',
    notes: rule?.notes ?? '',
    frequency: rule?.frequency ?? 'monthly',
    start_date: rule?.start_date ?? toISODate(new Date()),
    end_date: rule?.end_date ?? '',
  }
}

export default function RecurringRulesPage() {
  const [rules, setRules] = useState([])
  const [categories, setCategories] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function load() {
    setLoading(true)
    try {
      const [ruleData, categoryData] = await Promise.all([api('/recurring-rules/'), api('/categories/')])
      setRules(ruleData.results ?? ruleData)
      setCategories(categoryData.results ?? categoryData)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function update(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  function startEdit(rule) {
    setEditing(rule.id)
    setForm(ruleState(rule))
  }

  function reset() {
    setEditing(null)
    setForm(EMPTY)
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const body = { ...form, category: form.category ? Number(form.category) : null, end_date: form.end_date || null }
      if (editing) await api(`/recurring-rules/${editing}/`, { method: 'PATCH', body })
      else await api('/recurring-rules/', { method: 'POST', body })
      reset()
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setSaving(false)
    }
  }

  async function toggle(rule) {
    try {
      await api(`/recurring-rules/${rule.id}/`, { method: 'PATCH', body: { is_active: !rule.is_active } })
      await load()
    } catch (err) {
      setError(err)
    }
  }

  async function end(rule) {
    if (!window.confirm('End this recurring expense rule?')) return
    try {
      await api(`/recurring-rules/${rule.id}/`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Recurring expenses</h1>
          <p className="page-subtitle">Automate expenses that repeat on a schedule.</p>
        </div>
        <Button variant="primary" onClick={reset}>New recurring rule</Button>
      </header>
      {error && <Notice tone="danger">{error.message}</Notice>}

      <section className="card recurring-form-card">
        <h2>{editing ? 'Edit recurring rule' : 'Create recurring rule'}</h2>
        <form className="form" onSubmit={save} noValidate>
          <div className="field-row">
            <FormField label="Amount" name="amount" type="number" min="0.01" step="0.01" prefix="₹" required value={form.amount} onChange={update} />
            <FormField as="select" label="Frequency" name="frequency" value={form.frequency} onChange={update}>
              {['daily', 'weekly', 'monthly', 'yearly'].map((value) => <option key={value} value={value}>{value[0].toUpperCase() + value.slice(1)}</option>)}
            </FormField>
          </div>
          <div className="field-row">
            <FormField as="select" label="Category" name="category" value={form.category} onChange={update}>
              <option value="">Uncategorised</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </FormField>
            <FormField as="select" label="Payment method" name="payment_method" value={form.payment_method} onChange={update}>
              {PAYMENT_METHODS.map((method) => <option key={method.value} value={method.value}>{method.label}</option>)}
            </FormField>
          </div>
          <div className="field-row">
            <FormField label="Start date" name="start_date" type="date" required value={form.start_date} onChange={update} />
            <FormField label="End date (optional)" name="end_date" type="date" min={form.start_date} value={form.end_date} onChange={update} />
          </div>
          <div className="field-row">
            <FormField label="Merchant" name="merchant" maxLength={255} value={form.merchant} onChange={update} />
            <FormField label="Notes" name="notes" maxLength={255} value={form.notes} onChange={update} />
          </div>
          <div className="recurring-form-actions">
            <Button type="submit" variant="primary" loading={saving}>{editing ? 'Save changes' : 'Create rule'}</Button>
            {editing && <Button type="button" onClick={reset}>Cancel</Button>}
          </div>
        </form>
      </section>

      <section className="card recurring-list">
        <h2>Your rules</h2>
        {loading ? <p className="muted">Loading recurring rules…</p> : rules.length === 0 ? <p className="muted">No recurring rules yet.</p> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Details</th><th>Cadence</th><th>Next run</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td><span className="cell-title">₹{rule.amount}</span><span className="cell-sub">{rule.merchant || rule.notes || 'Recurring expense'}</span></td>
                    <td>{rule.frequency}</td>
                    <td>{rule.next_run_date || '—'}</td>
                    <td>{rule.is_active ? 'Active' : 'Paused'}</td>
                    <td className="actions"><span className="row-actions">
                      <Button size="sm" variant="ghost" onClick={() => startEdit(rule)}>Edit</Button>
                      <Button size="sm" variant="ghost" onClick={() => toggle(rule)}>{rule.is_active ? 'Pause' : 'Resume'}</Button>
                      <Button size="sm" variant="ghost" onClick={() => end(rule)}>End</Button>
                    </span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
