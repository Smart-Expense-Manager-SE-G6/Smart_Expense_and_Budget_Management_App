import { useState } from 'react'
import { api } from '../../api'
import FormField from '../../components/FormField'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Notice from '../../components/ui/Notice'
import { addDays, endOfMonth, parseISODate, toISODate } from '../../lib/format'

const FORM_ID = 'budget-form'
const FIELDS = ['name', 'category', 'limit_amount', 'period', 'start_date', 'end_date', 'rollover_mode']

// Derives the period dates the API requires (D2): weekly = 7 days, monthly = whole calendar month.
function periodDates(period, startValue) {
  if (!startValue) return { start_date: '', end_date: '' }
  if (period === 'monthly') {
    const start = parseISODate(`${startValue.slice(0, 7)}-01`)
    return { start_date: toISODate(start), end_date: toISODate(endOfMonth(start)) }
  }
  const start = parseISODate(startValue)
  return { start_date: toISODate(start), end_date: toISODate(addDays(start, 6)) }
}

function initialState(budget) {
  const period = budget?.period ?? 'monthly'
  const start = budget?.start_date ?? toISODate(new Date())
  return {
    name: budget?.name ?? '',
    category: budget?.category ? String(budget.category) : '',
    limit_amount: budget?.limit_amount ?? '',
    period,
    start: period === 'monthly' ? start.slice(0, 7) : start,
    rollover_mode: budget?.rollover_mode ?? 'reset',
  }
}

// Create / edit a budget (FR10, FR12). Mount with a `key` so it resets per target budget.
export default function BudgetForm({ open, budget, categories, onClose, onSaved }) {
  const editing = Boolean(budget)
  const [form, setForm] = useState(() => initialState(budget))
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const dates = periodDates(form.period, form.start)
  const fieldError = (name) => (error?.field === name ? error.message : null)
  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  function changePeriod(event) {
    const period = event.target.value
    // Keep the chosen day/month meaningful when switching input type.
    const start = period === 'monthly' ? (form.start || '').slice(0, 7) : form.start.length === 7 ? `${form.start}-01` : form.start
    setForm({ ...form, period, start })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    const body = {
      name: form.name.trim(),
      category: form.category ? Number(form.category) : null,
      limit_amount: form.limit_amount,
      period: form.period,
      rollover_mode: form.rollover_mode,
      ...dates,
    }
    try {
      const saved = editing
        ? await api(`/budgets/${budget.id}/`, { method: 'PATCH', body })
        : await api('/budgets/', { method: 'POST', body })
      onSaved({ budget: saved, created: !editing })
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      title={editing ? 'Edit budget' : 'New budget'}
      description="Set a spending limit for a category or your overall spend."
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" loading={submitting}>
            {editing ? 'Save changes' : 'Create budget'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="modal-body form" onSubmit={handleSubmit} noValidate>
        {error && (!FIELDS.includes(error.field) || !error.field) && <Notice tone="danger">{error.message}</Notice>}
        <FormField label="Budget name" name="name" required maxLength={100} placeholder="e.g. Monthly groceries"
          value={form.name} onChange={update} error={fieldError('name')} />
        <div className="field-row">
          <FormField as="select" label="Applies to" name="category" value={form.category} onChange={update} error={fieldError('category')}>
            <option value="">All categories (overall)</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </FormField>
          <FormField label="Limit" name="limit_amount" type="number" inputMode="decimal" step="0.01" min="0.01" prefix="₹" required placeholder="0.00"
            value={form.limit_amount} onChange={update} error={fieldError('limit_amount')} />
        </div>
        <div className="field-row">
          <FormField as="select" label="Period" name="period" value={form.period} onChange={changePeriod} error={fieldError('period')}>
            <option value="monthly">Monthly</option>
            <option value="weekly">Weekly</option>
          </FormField>
          <FormField
            label={form.period === 'monthly' ? 'Month' : 'Week starts on'}
            name="start"
            type={form.period === 'monthly' ? 'month' : 'date'}
            required
            value={form.start}
            onChange={update}
            error={fieldError('start_date') || fieldError('end_date')}
            hint={dates.start_date ? `Runs ${dates.start_date} to ${dates.end_date}` : undefined}
          />
        </div>
        <FormField as="select" label="At period end" name="rollover_mode" value={form.rollover_mode} onChange={update} error={fieldError('rollover_mode')}
          hint="Rollover carries unspent money into the next period; reset starts fresh.">
          <option value="reset">Reset to the original limit</option>
          <option value="rollover">Roll unspent amount over</option>
        </FormField>
      </form>
    </Modal>
  )
}

