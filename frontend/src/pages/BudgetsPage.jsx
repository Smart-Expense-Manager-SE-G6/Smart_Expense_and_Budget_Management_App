import { useState } from 'react'
import { api } from '../api'
import Button from '../components/ui/Button'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import EmptyState from '../components/ui/EmptyState'
import Notice from '../components/ui/Notice'
import Skeleton from '../components/ui/Skeleton'
import BudgetCard from '../features/budgets/BudgetCard'
import BudgetForm from '../features/budgets/BudgetForm'
import useBudgets from '../hooks/useBudgets'
import useCategories from '../hooks/useCategories'

export default function BudgetsPage() {
  const { categories } = useCategories()
  const { active, past, loading, error, reload } = useBudgets()
  const [editor, setEditor] = useState({ open: false, budget: null, key: 0 })
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [flash, setFlash] = useState(null)

  const openEditor = (budget = null) => setEditor((prev) => ({ open: true, budget, key: prev.key + 1 }))

  function handleSaved({ created }) {
    setEditor((prev) => ({ ...prev, open: false }))
    setFlash({ tone: 'success', text: created ? 'Budget created.' : 'Budget updated.' })
    reload()
  }

  async function confirmDelete() {
    setDeleting(true)
    try {
      await api(`/budgets/${pendingDelete.id}/`, { method: 'DELETE' })
      setFlash({ tone: 'success', text: 'Budget deleted.' })
      reload()
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
          <h1 className="page-title">Budgets</h1>
          <p className="page-subtitle">Weekly and monthly limits, tracked against your spending in real time.</p>
        </div>
        <div className="page-actions">
          <Button variant="primary" icon="plus" onClick={() => openEditor()}>
            New budget
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

      {error ? (
        <Notice tone="danger" action={<Button size="sm" onClick={reload}>Retry</Button>}>
          {error.message}
        </Notice>
      ) : loading ? (
        <div className="grid grid-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={280} radius="22px" />
          ))}
        </div>
      ) : active.length === 0 && past.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="target"
            title="No budgets yet"
            description="Create a budget to see how much you have left and get alerted at 80% and 100%."
            action={
              <Button variant="primary" icon="plus" onClick={() => openEditor()}>
                New budget
              </Button>
            }
          />
        </div>
      ) : (
        <>
          <section aria-labelledby="active-budgets">
            <h2 id="active-budgets" className="section-title">
              Active <span className="section-count">{active.length}</span>
            </h2>
            {active.length === 0 ? (
              <p className="muted section-empty">No budget covers today. Create one to start tracking.</p>
            ) : (
              <div className="grid grid-3">
                {active.map((budget) => (
                  <BudgetCard key={budget.id} budget={budget} onEdit={openEditor} onDelete={setPendingDelete} />
                ))}
              </div>
            )}
          </section>

          {past.length > 0 && (
            <section aria-labelledby="past-budgets">
              <h2 id="past-budgets" className="section-title">
                Past &amp; upcoming <span className="section-count">{past.length}</span>
              </h2>
              <div className="grid grid-3">
                {past.map((budget) => (
                  <BudgetCard key={budget.id} budget={budget} muted onEdit={openEditor} onDelete={setPendingDelete} />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <BudgetForm
        key={editor.key}
        open={editor.open}
        budget={editor.budget}
        categories={categories}
        onClose={() => setEditor((prev) => ({ ...prev, open: false }))}
        onSaved={handleSaved}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete this budget?"
        message={pendingDelete ? `"${pendingDelete.name}" and its alerts will be removed. Your expenses are not affected.` : ''}
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )
}

