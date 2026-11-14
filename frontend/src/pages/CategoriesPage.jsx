import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import FormField from '../components/FormField'

function buildTree(categories) {
  const byId = new Map(categories.map((category) => [category.id, { ...category, children: [] }]))
  const roots = []

  byId.forEach((category) => {
    const parent = category.parent ? byId.get(category.parent) : null
    if (parent) parent.children.push(category)
    else roots.push(category)
  })

  const sort = (items) => {
    items.sort((left, right) => left.name.localeCompare(right.name) || left.id - right.id)
    items.forEach((item) => sort(item.children))
    return items
  }
  return sort(roots)
}

function CategoryNode({ category, onCreate, onRename, onDeactivate }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(category.name)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setName(category.name)
  }, [category.name])

  async function saveName(event) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await onRename(category.id, name)
      setEditing(false)
    } catch (err) {
      setError(err)
    } finally {
      setSaving(false)
    }
  }

  async function deactivate() {
    setSaving(true)
    setError(null)
    try {
      await onDeactivate(category.id)
    } catch (err) {
      setError(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <li className="category-item">
      <div className="category-row">
        <span>
          {category.name}
          {!category.owner && <span className="category-badge">Global</span>}
        </span>
        <span className="category-actions">
          <button type="button" className="link-button" onClick={() => onCreate(category.id)}>
            Add subcategory
          </button>
          {category.owner && (
            <>
              <button type="button" className="link-button" onClick={() => setEditing(!editing)}>
                {editing ? 'Cancel' : 'Rename'}
              </button>
              <button type="button" className="link-button danger-button" disabled={saving} onClick={deactivate}>
                Deactivate
              </button>
            </>
          )}
        </span>
      </div>
      {editing && (
        <form className="category-edit-form" onSubmit={saveName} noValidate>
          <FormField
            label={`Name for ${category.name}`}
            name="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            error={error?.field === 'name' ? error.message : null}
          />
          <button type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Save name'}
          </button>
          {error && error.field !== 'name' && <p className="form-error" role="alert">{error.message}</p>}
        </form>
      )}
      {error && !editing && <p className="form-error" role="alert">{error.message}</p>}
      {category.children.length > 0 && (
        <ul className="category-tree">
          {category.children.map((child) => (
            <CategoryNode
              key={child.id}
              category={child}
              onCreate={onCreate}
              onRename={onRename}
              onDeactivate={onDeactivate}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

export default function CategoriesPage() {
  const [categories, setCategories] = useState([])
  const [name, setName] = useState('')
  const [parent, setParent] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function loadCategories() {
    setLoading(true)
    try {
      setCategories(await api('/categories/'))
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
  }, [])

  const tree = useMemo(() => buildTree(categories), [categories])

  async function createCategory(event) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api('/categories/', {
        method: 'POST',
        body: { name, ...(parent ? { parent: Number(parent) } : {}) },
      })
      setName('')
      setParent('')
      await loadCategories()
    } catch (err) {
      setError(err)
    } finally {
      setSaving(false)
    }
  }

  function chooseParent(categoryId) {
    setParent(String(categoryId))
  }

  async function renameCategory(categoryId, categoryName) {
    await api(`/categories/${categoryId}/`, {
      method: 'PATCH',
      body: { name: categoryName },
    })
    await loadCategories()
  }

  async function deactivateCategory(categoryId) {
    await api(`/categories/${categoryId}/`, { method: 'DELETE' })
    await loadCategories()
  }

  return (
    <section className="card">
      <h1>Categories</h1>
      <p className="muted">Global categories are read-only. You can manage your own categories and subcategories.</p>
      <form className="category-create-form" onSubmit={createCategory} noValidate>
        <FormField
          label="Category name"
          name="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={error?.field === 'name' ? error.message : null}
          required
        />
        <FormField
          as="select"
          label="Parent category"
          name="parent"
          value={parent}
          onChange={(event) => setParent(event.target.value)}
          error={error?.field === 'parent' ? error.message : null}
        >
          <option value="">No parent</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}{!category.owner ? ' (Global)' : ''}
            </option>
          ))}
        </FormField>
        <button type="submit" disabled={saving}>
          {saving ? 'Creating…' : 'Create category'}
        </button>
        {error && !error.field && <p className="form-error" role="alert">{error.message}</p>}
      </form>
      {loading ? (
        <p className="muted">Loading categories…</p>
      ) : tree.length === 0 ? (
        <p className="muted">No categories available.</p>
      ) : (
        <ul className="category-tree category-tree-root">
          {tree.map((category) => (
            <CategoryNode
              key={category.id}
              category={category}
              onCreate={chooseParent}
              onRename={renameCategory}
              onDeactivate={deactivateCategory}
            />
          ))}
        </ul>
      )}
    </section>
  )
}
