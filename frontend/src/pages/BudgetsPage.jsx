
import { useEffect, useState } from 'react'
import { api } from '../api'
import './BudgetsPage.css'

const emptyForm = {
  name: '',
  category: '',
  limit_amount: '',
  period: 'monthly',
  start_date: '',
  end_date: '',
  rollover_mode: 'reset',
}

function getList(data) {
  if (Array.isArray(data)) return data
  return data?.results ?? []
}

function getErrorMessage(error) {
  if (error?.message) return error.message
  return 'Something went wrong. Please try again.'
}

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState([])
  const [categories, setCategories] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [utilisations, setUtilisations] = useState({})

  async function loadData() {
    setLoading(true)
    setError('')

    try {
      const [budgetData, categoryData] = await Promise.all([
        api('/budgets/'),
        api('/categories/'),
      ])

      const budgetList = getList(budgetData)
      setBudgets(budgetList)
      setCategories(getList(categoryData))

      const results = await Promise.all(
        budgetList.map(async (budget) => {
          try {
            const data = await api(
              `/budgets/${budget.id}/utilization/`
            )
            return [budget.id, data]
          } catch {
            return [budget.id, null]
          }
        })
      )

      setUtilisations(Object.fromEntries(results))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  function handleChange(event) {
    const { name, value } = event.target

    setForm((current) => ({
      ...current,
      [name]: value,
    }))
  }

  function resetForm() {
    setForm(emptyForm)
    setEditingId(null)
  }

  function handleEdit(budget) {
    setForm({
      name: budget.name ?? '',
      category: budget.category_name ?? '',
      limit_amount: budget.limit_amount ?? '',
      period: budget.period ?? 'monthly',
      start_date: budget.start_date ?? '',
      end_date: budget.end_date ?? '',
      rollover_mode: budget.rollover_mode ?? 'reset',
    })

    setEditingId(budget.id)
    setError('')
    setMessage('')

    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    })
  }

  async function getOrCreateCategory(categoryName) {
    const name = categoryName.trim()

    if (!name) return null

    const existingCategory = categories.find(
      (category) =>
        category.name.trim().toLowerCase() ===
        name.toLowerCase()
    )

    if (existingCategory) {
      return existingCategory.id
    }

    const createdCategory = await api('/categories/', {
      method: 'POST',
      body: { name },
    })

    setCategories((current) => {
      const alreadyExists = current.some(
        (category) => category.id === createdCategory.id
      )

      if (alreadyExists) return current

      return [...current, createdCategory].sort((a, b) =>
        a.name.localeCompare(b.name)
      )
    })

    return createdCategory.id
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')

    if (!form.name.trim()) {
      setError('Please enter a budget name.')
      return
    }

    if (
      !form.limit_amount ||
      Number(form.limit_amount) <= 0
    ) {
      setError('Budget limit must be greater than zero.')
      return
    }

    if (!form.start_date || !form.end_date) {
      setError('Please select both start and end dates.')
      return
    }

    if (form.start_date > form.end_date) {
      setError(
        'End date must be on or after the start date.'
      )
      return
    }

    setSaving(true)

    try {
      const categoryId = await getOrCreateCategory(
        form.category
      )

      const payload = {
        name: form.name.trim(),
        category: categoryId,
        limit_amount: form.limit_amount,
        period: form.period,
        start_date: form.start_date,
        end_date: form.end_date,
        rollover_mode: form.rollover_mode,
      }

      if (editingId) {
        await api(`/budgets/${editingId}/`, {
          method: 'PATCH',
          body: payload,
        })

        setMessage('Budget updated successfully.')
      } else {
        await api('/budgets/', {
          method: 'POST',
          body: payload,
        })

        setMessage('Budget created successfully.')
      }

      resetForm()
      await loadData()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id) {
    if (
      !window.confirm(
        'Are you sure you want to delete this budget?'
      )
    ) {
      return
    }

    setError('')
    setMessage('')

    try {
      await api(`/budgets/${id}/`, {
        method: 'DELETE',
      })

      setMessage('Budget deleted successfully.')
      await loadData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  function formatMoney(value) {
    const amount = Number(value ?? 0)

    return `₹${amount.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`
  }

  return (
    <section className="budgets-page">
      <div className="budget-heading">
        <div>
          <h1>Budget Management</h1>
          <p className="muted">
            Create and manage your spending limits.
          </p>
        </div>

        <span className="budget-count">
          {budgets.length} budgets
        </span>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {message && (
        <p className="success" role="status">
          {message}
        </p>
      )}

      <section className="card budget-form-card">
        <h2>
          {editingId ? 'Edit Budget' : 'Create New Budget'}
        </h2>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="budget-name">
              Budget Name
            </label>

            <input
              id="budget-name"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="Example: Monthly Food Budget"
              maxLength={100}
              required
            />
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="budget-category">
                Category
              </label>

              <input
                id="budget-category"
                name="category"
                type="text"
                value={form.category}
                onChange={handleChange}
                placeholder="Enter any category (e.g. Shopping, Rent, EMI)"
                maxLength={100}
                list="budget-category-suggestions"
              />

              <datalist id="budget-category-suggestions">
                {categories.map((category) => (
                  <option
                    key={category.id}
                    value={category.name}
                  />
                ))}
              </datalist>

              <small className="muted">
                Enter your own category or choose a suggestion.
              </small>
            </div>

            <div className="field">
              <label htmlFor="budget-limit">
                Budget Limit (₹)
              </label>

              <input
                id="budget-limit"
                name="limit_amount"
                type="number"
                min="0.01"
                step="0.01"
                value={form.limit_amount}
                onChange={handleChange}
                placeholder="Enter amount"
                required
              />
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="budget-period">
                Period
              </label>

              <select
                id="budget-period"
                name="period"
                value={form.period}
                onChange={handleChange}
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="budget-rollover">
                Rollover Mode
              </label>

              <select
                id="budget-rollover"
                name="rollover_mode"
                value={form.rollover_mode}
                onChange={handleChange}
              >
                <option value="reset">Reset</option>
                <option value="rollover">Rollover</option>
              </select>
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="budget-start">
                Start Date
              </label>

              <input
                id="budget-start"
                name="start_date"
                type="date"
                value={form.start_date}
                onChange={handleChange}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="budget-end">
                End Date
              </label>

              <input
                id="budget-end"
                name="end_date"
                type="date"
                value={form.end_date}
                onChange={handleChange}
                min={form.start_date || undefined}
                required
              />
            </div>
          </div>

          <div className="budget-form-actions">
            <button type="submit" disabled={saving}>
              {saving
                ? 'Saving...'
                : editingId
                  ? 'Update Budget'
                  : 'Create Budget'}
            </button>

            {editingId && (
              <button
                type="button"
                className="budget-secondary-button"
                onClick={resetForm}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="budget-list-section">
        <h2>Your Budgets</h2>

        {loading ? (
          <p className="muted">Loading budgets...</p>
        ) : budgets.length === 0 ? (
          <div className="card">
            <p>
              No budgets found. Create your first budget above.
            </p>
          </div>
        ) : (
          <div className="budget-grid">
            {budgets.map((budget) => {
              const usage = utilisations[budget.id]

              const percentage = Number(
                usage?.percentage_used ?? 0
              )

              const progress = Math.max(
                0,
                Math.min(percentage, 100)
              )

              return (
                <article
                  className="card budget-card"
                  key={budget.id}
                >
                  <div className="budget-card-heading">
                    <div>
                      <h3>{budget.name}</h3>

                      <p className="muted">
                        {budget.category_name ||
                          'All categories'}{' '}
                        · {budget.period}
                      </p>
                    </div>

                    <span className="budget-mode">
                      {budget.rollover_mode}
                    </span>
                  </div>

                  <div className="budget-amount">
                    <strong>
                      {formatMoney(usage?.amount_spent)}
                    </strong>

                    <span className="muted">
                      {' '}/ {formatMoney(budget.limit_amount)} spent
                    </span>
                  </div>

                  <div
                    className="budget-progress"
                    role="progressbar"
                    aria-label={`${budget.name} usage`}
                    aria-valuenow={Math.max(0, percentage)}
                    aria-valuemin="0"
                    aria-valuemax="100"
                  >
                    <div
                      className={
                        percentage > 100 ? 'over-limit' : ''
                      }
                      style={{ width: `${progress}%` }}
                    />
                  </div>

                  <div className="budget-stats">
                    <span>
                      {percentage.toFixed(2)}% used
                    </span>

                    <span>
                      {usage
                        ? `${formatMoney(
                            usage.remaining_amount
                          )} remaining`
                        : 'Usage unavailable'}
                    </span>
                  </div>

                  <p className="muted budget-dates">
                    {budget.start_date} to {budget.end_date}
                  </p>

                  <div className="budget-card-actions">
                    <button
                      type="button"
                      onClick={() => handleEdit(budget)}
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      className="budget-delete-button"
                      onClick={() => handleDelete(budget.id)}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>
    </section>
  )
}
