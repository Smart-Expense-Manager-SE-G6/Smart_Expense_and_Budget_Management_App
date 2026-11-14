import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, query } from '../api'
import FormField from '../components/FormField'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import EmptyState from '../components/ui/EmptyState'
import Icon from '../components/ui/Icon'
import Notice from '../components/ui/Notice'
import Skeleton from '../components/ui/Skeleton'
import ExpenseForm from '../features/expenses/ExpenseForm'
import useAsync from '../hooks/useAsync'
import useCategories from '../hooks/useCategories'
import { categoryColor, formatCurrency, formatDate, paymentLabel } from '../lib/format'

const PAGE_SIZE = 15
const EMPTY_FILTERS = { category: '', start_date: '', end_date: '', ordering: '-date' }
const ORDERINGS = [
  { value: '-date', label: 'Newest first' },
  { value: 'date', label: 'Oldest first' },
  { value: '-amount', label: 'Highest amount' },
  { value: 'amount', label: 'Lowest amount' },
]

export default function ExpensesPage() {
  const { categories, byId } = useCategories()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [editor, setEditor] = useState({ open: false, expense: null, key: 0 })
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [flash, setFlash] = useState(null)

  // "+ Add expense" elsewhere in the app deep-links here with ?new=1.
  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setEditor((prev) => ({ open: true, expense: null, key: prev.key + 1 }))
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const load = useCallback(
    () => api(`/expenses/${query({ ...filters, page, page_size: PAGE_SIZE })}`),
    [filters, page],
  )
  const { data, loading, error, reload } = useAsync(load)
  const rows = data?.results ?? []
  const count = data?.count ?? 0
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE))
  const filtered = Object.entries(filters).some(([key, value]) => key !== 'ordering' && value) || filters.ordering !== '-date'

  function setFilter(event) {
    setPage(1)
    setFilters({ ...filters, [event.target.name]: event.target.value })
  }

  function openCreate() {
    setEditor((prev) => ({ open: true, expense: null, key: prev.key + 1 }))
  }

  function openEdit(expense) {
    setEditor((prev) => ({ open: true, expense, key: prev.key + 1 }))
  }

  function handleSaved({ created, warning }) {
    setEditor((prev) => ({ ...prev, open: false }))
    setFlash(warning ? { tone: 'warning', text: warning } : { tone: 'success', text: created ? 'Expense added.' : 'Expense updated.' })
    reload()
  }

  async function confirmDelete() {
    setDeleting(true)
    try {
      await api(`/expenses/${pendingDelete.id}/`, { method: 'DELETE' })
      setFlash({ tone: 'success', text: 'Expense deleted.' })
      // Stepping back a page when the last row of the final page is removed.
      if (rows.length === 1 && page > 1) setPage(page - 1)
      else reload()
    } catch (err) {
      setFlash({ tone: 'danger', text: err.message })
    } finally {
      setDeleting(false)
      setPendingDelete(null)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Expenses</h1>
          <p className="page-subtitle">Every transaction you have recorded, in one place.</p>
        </div>
        <div className="page-actions">
          <Button variant="primary" icon="plus" onClick={openCreate}>
            Add expense
          </Button>
        </div>
      </header>

      {flash && (
        <div className="flash">
          <Notice tone={flash.tone} action={<Button variant="ghost" size="sm" iconOnly icon="x" aria-label="Dismiss" onClick={() => setFlash(null)} />}>
            {flash.text}
          </Notice>
        </div>
      )}

      <Card className="table-card">
        <form className="toolbar" onSubmit={(event) => event.preventDefault()} aria-label="Filter expenses">
          <FormField as="select" label="Category" name="category" value={filters.category} onChange={setFilter}>
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </FormField>
          <FormField label="From" name="start_date" type="date" value={filters.start_date} max={filters.end_date || undefined} onChange={setFilter} />
          <FormField label="To" name="end_date" type="date" value={filters.end_date} min={filters.start_date || undefined} onChange={setFilter} />
          <FormField as="select" label="Sort by" name="ordering" value={filters.ordering} onChange={setFilter}>
            {ORDERINGS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </FormField>
          {filtered && (
            <Button
              variant="ghost"
              onClick={() => {
                setFilters(EMPTY_FILTERS)
                setPage(1)
              }}
            >
              Clear filters
            </Button>
          )}
        </form>

        {error ? (
          <div className="card-body">
            <Notice tone="danger" action={<Button size="sm" onClick={reload}>Retry</Button>}>
              {error.message}
            </Notice>
          </div>
        ) : loading ? (
          <div className="card-body stack">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} height={44} radius="10px" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            icon="receipt"
            title={filtered ? 'No expenses match these filters' : 'No expenses yet'}
            description={filtered ? 'Try widening the date range or clearing a filter.' : 'Add your first expense to start tracking where your money goes.'}
            action={
              filtered ? undefined : (
                <Button variant="primary" icon="plus" onClick={openCreate}>
                  Add expense
                </Button>
              )
            }
          />
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Description</th>
                    <th scope="col">Category</th>
                    <th scope="col">Payment</th>
                    <th scope="col" className="num">
                      Amount
                    </th>
                    <th scope="col">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((expense) => {
                    const category = byId.get(expense.category)
                    return (
                      <tr key={expense.id}>
                        <td className="nowrap">{formatDate(expense.date)}</td>
                        <td>
                          <span className="cell-title">{expense.description || '—'}</span>
                          {expense.has_receipt && (
                            <a className="receipt-link" href={`/api/v1/expenses/${expense.id}/receipt/`} target="_blank" rel="noreferrer" title="View receipt">
                              <Icon name="paperclip" size={14} />
                              <span className="sr-only">View receipt</span>
                            </a>
                          )}
                        </td>
                        <td>
                          {category ? (
                            <span className="chip">
                              <span className="dot" style={{ '--dot': categoryColor(category.id) }} />
                              {category.name}
                            </span>
                          ) : (
                            <span className="muted">Uncategorised</span>
                          )}
                        </td>
                        <td>
                          <Badge>{paymentLabel(expense.payment_method)}</Badge>
                        </td>
                        <td className="num">{formatCurrency(expense.amount)}</td>
                        <td className="actions">
                          <span className="row-actions">
                            <Button variant="ghost" size="sm" iconOnly icon="pencil" aria-label={`Edit ${expense.description || 'expense'}`} onClick={() => openEdit(expense)} />
                            <Button variant="ghost" size="sm" iconOnly icon="trash" aria-label={`Delete ${expense.description || 'expense'}`} onClick={() => setPendingDelete(expense)} />
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, count)} of {count}
              </span>
              <div className="pagination-actions">
                <Button size="sm" icon="chevronLeft" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  Previous
                </Button>
                <span className="pagination-page">
                  Page {page} / {totalPages}
                </span>
                <Button size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                  Next
                  <Icon name="chevronRight" size={15} />
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>

      <ExpenseForm
        key={editor.key}
        open={editor.open}
        expense={editor.expense}
        categories={categories}
        onClose={() => setEditor((prev) => ({ ...prev, open: false }))}
        onSaved={handleSaved}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete this expense?"
        message={pendingDelete ? `${formatCurrency(pendingDelete.amount)} on ${formatDate(pendingDelete.date)} will be removed from your totals and budgets.` : ''}
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )
}

