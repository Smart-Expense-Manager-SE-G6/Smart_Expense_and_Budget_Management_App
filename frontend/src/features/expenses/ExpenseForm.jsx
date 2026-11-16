import { useEffect, useState } from 'react'
import { api, query } from '../../api'
import FormField from '../../components/FormField'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Notice from '../../components/ui/Notice'
import { PAYMENT_METHODS, toISODate } from '../../lib/format'

const FORM_ID = 'expense-form'
const MAX_RECEIPT_MB = 5

function initialState(expense) {
  return {
    amount: expense?.amount ?? '',
    date: expense?.date ?? toISODate(new Date()),
    category: expense?.category ? String(expense.category) : '',
    description: expense?.description ?? '',
    merchant: expense?.merchant ?? '',
    notes: expense?.notes ?? '',
    payment_method: expense?.payment_method ?? 'upi',
  }
}

// Create / edit an expense (FR4) with an optional receipt attachment (FR5).
// Mount with a `key` so the form resets whenever the target expense changes.
export default function ExpenseForm({ open, expense, categories, onClose, onSaved }) {
  const editing = Boolean(expense)
  const [form, setForm] = useState(() => initialState(expense))
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [hasReceipt, setHasReceipt] = useState(Boolean(expense?.has_receipt))
  const [suggestions, setSuggestions] = useState([])
  const [suggestionError, setSuggestionError] = useState(null)

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value })
  const fieldError = (name) => (error?.field === name ? error.message : null)

  useEffect(() => {
    const description = form.description.trim()
    const merchant = form.merchant.trim()
    if (!description && !merchant) {
      setSuggestions([])
      setSuggestionError(null)
      return undefined
    }

    let active = true
    setSuggestionError(null)
    const timer = setTimeout(() => {
      api(`/categories/suggestions/${query({ description, merchant })}`)
        .then((data) => {
          if (active) {
            setSuggestions(data.suggestions ?? [])
            setSuggestionError(null)
          }
        })
        .catch((err) => {
          if (active) {
            setSuggestions([])
            setSuggestionError(err)
          }
        })
    }, 300)

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [form.description, form.merchant])

  function acceptSuggestion(categoryId) {
    setForm((current) => ({ ...current, category: String(categoryId) }))
    setSuggestions([])
  }

  async function removeReceipt() {
    try {
      await api(`/expenses/${expense.id}/receipt/`, { method: 'DELETE' })
      setHasReceipt(false)
    } catch (err) {
      setError(err)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)

    if (file && file.size > MAX_RECEIPT_MB * 1024 * 1024) {
      setError({ field: 'receipt', message: `Receipt must be ${MAX_RECEIPT_MB} MB or smaller.` })
      return
    }

    setSubmitting(true)
    const body = {
      amount: form.amount,
      date: form.date,
      category: form.category ? Number(form.category) : null,
      description: form.description.trim(),
      merchant: form.merchant.trim(),
      notes: form.notes.trim(),
      payment_method: form.payment_method,
    }

    let saved
    try {
      saved = editing
        ? await api(`/expenses/${expense.id}/`, { method: 'PATCH', body })
        : await api('/expenses/', { method: 'POST', body })
    } catch (err) {
      setError(err)
      setSubmitting(false)
      return
    }

    // The expense exists now; a receipt failure must not trigger a duplicate create on retry.
    let warning = null
    if (file) {
      try {
        const data = new FormData()
        data.append('receipt', file)
        await api(`/expenses/${saved.id}/receipt/`, { method: 'POST', body: data })
      } catch (err) {
        warning = `Expense saved, but the receipt could not be uploaded: ${err.message}`
      }
    }
    setSubmitting(false)
    onSaved({ expense: saved, created: !editing, warning })
  }

  return (
    <Modal
      open={open}
      title={editing ? 'Edit expense' : 'Add expense'}
      description={editing ? 'Update the details of this transaction.' : 'Record a new transaction.'}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" loading={submitting}>
            {editing ? 'Save changes' : 'Add expense'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="modal-body form" onSubmit={handleSubmit} noValidate>
        {error && !['amount', 'date', 'category', 'description', 'merchant', 'notes', 'payment_method', 'receipt'].includes(error.field) && (
          <Notice tone="danger">{error.message}</Notice>
        )}
        <div className="field-row">
          <FormField label="Amount" name="amount" type="number" inputMode="decimal" step="0.01" min="0.01" placeholder="0.00" prefix="₹" required
            value={form.amount} onChange={update} error={fieldError('amount')} />
          <FormField label="Date" name="date" type="date" required max={toISODate(new Date())}
            value={form.date} onChange={update} error={fieldError('date')} />
        </div>
        <div className="field-row">
          <FormField as="select" label="Category" name="category" value={form.category} onChange={update} error={fieldError('category')}>
            <option value="">Uncategorised</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </FormField>
          <FormField as="select" label="Payment method" name="payment_method" value={form.payment_method} onChange={update} error={fieldError('payment_method')}>
            {PAYMENT_METHODS.map((method) => (
              <option key={method.value} value={method.value}>
                {method.label}
              </option>
            ))}
          </FormField>
        </div>
        <FormField label="Description" name="description" maxLength={255} placeholder="e.g. Dinner with the team"
          value={form.description} onChange={update} error={fieldError('description')} />
        <div className="field-row">
          <FormField label="Merchant" name="merchant" maxLength={255} placeholder="e.g. Acme Cafe"
            value={form.merchant} onChange={update} error={fieldError('merchant')} />
          <FormField label="Notes" name="notes" maxLength={255} placeholder="Optional details"
            value={form.notes} onChange={update} error={fieldError('notes')} />
        </div>
        {suggestions.length > 0 && (
          <div className="category-suggestions" role="status" aria-label="Category suggestions">
            <span className="muted">Suggestions (choose one):</span>
            {suggestions.map((suggestion) => (
              <Button key={suggestion.id} type="button" size="sm" variant="ghost" onClick={() => acceptSuggestion(suggestion.id)}>
                {suggestion.name}
              </Button>
            ))}
          </div>
        )}
        {suggestionError && <Notice tone="warning">Category suggestions unavailable: {suggestionError.message}</Notice>}

        {editing && hasReceipt ? (
          <div className="receipt-row">
            <span className="muted">A receipt is attached to this expense.</span>
            <span className="row-actions">
              <a className="btn btn-sm" href={`/api/v1/expenses/${expense.id}/receipt/`} target="_blank" rel="noreferrer">
                View
              </a>
              <Button size="sm" variant="ghost" onClick={removeReceipt}>
                Remove
              </Button>
            </span>
          </div>
        ) : (
          <FormField label="Receipt (optional)" name="receipt" type="file" accept=".jpg,.jpeg,.png,.pdf"
            hint={`JPG, PNG or PDF up to ${MAX_RECEIPT_MB} MB.`} onChange={(event) => setFile(event.target.files?.[0] ?? null)} error={fieldError('receipt')} />
        )}
      </form>
    </Modal>
  )
}

