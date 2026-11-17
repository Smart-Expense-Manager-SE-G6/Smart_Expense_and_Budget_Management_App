import { useRef, useState } from 'react'
import { api } from '../api'
import Button from '../components/ui/Button'
import Notice from '../components/ui/Notice'

export default function ExpenseImportPage() {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)

  function chooseFile(nextFile) {
    setError(null)
    setPreview(null)
    if (!nextFile) return
    if (!nextFile.name.toLowerCase().endsWith('.csv')) {
      setError({ message: 'Please choose a CSV file.' })
      return
    }
    setFile(nextFile)
  }

  async function submit(dryRun) {
    if (!file) {
      setError({ message: 'Choose a CSV file first.' })
      return
    }
    setBusy(true)
    setError(null)
    try {
      const body = new FormData()
      body.append('file', file)
      const result = await api(`/expenses/import/${dryRun ? '?dry_run=true' : ''}`, { method: 'POST', body })
      setPreview({ ...result, imported: !dryRun })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">Import expenses</h1>
          <p className="page-subtitle">Preview your CSV before adding valid transactions.</p>
        </div>
        <a className="btn btn-ghost" href="/expense-import-template.csv" download>
          Download CSV template
        </a>
      </header>

      <section className="card import-card">
        <div
          className={`import-dropzone${dragging ? ' is-dragging' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            chooseFile(event.dataTransfer.files?.[0])
          }}
        >
          <p><strong>Drop a CSV file here</strong></p>
          <p className="muted">or</p>
          <Button type="button" onClick={() => inputRef.current?.click()}>Choose file</Button>
          <input
            ref={inputRef}
            className="sr-only"
            type="file"
            accept=".csv,text/csv"
            aria-label="CSV file"
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />
          {file && <p className="import-file">{file.name}</p>}
        </div>

        {error && <Notice tone="danger">{error.message}</Notice>}
        <div className="import-actions">
          <Button type="button" variant="primary" loading={busy} disabled={!file} onClick={() => submit(true)}>
            Preview import
          </Button>
          {preview && !preview.imported && (
            <Button type="button" loading={busy} disabled={preview.accepted_count === 0} onClick={() => submit(false)}>
              Import valid rows
            </Button>
          )}
        </div>

        {preview && (
          <div className="import-results" aria-live="polite">
            <h2>{preview.imported ? 'Import complete' : 'Preview results'}</h2>
            <p>
              {preview.accepted_count} valid row{preview.accepted_count === 1 ? '' : 's'}; {preview.rejected_count} rejected.
            </p>
            {preview.errors?.length > 0 && (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Row</th><th>Field</th><th>Reason</th><th>Value</th></tr></thead>
                  <tbody>
                    {preview.errors.map((item, index) => (
                      <tr key={`${item.row_number}-${item.field}-${index}`}>
                        <td>{item.row_number}</td>
                        <td>{item.field}</td>
                        <td>{item.message}</td>
                        <td>{item.raw_value || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {preview.imported && <a href="/expenses">View expenses</a>}
          </div>
        )}
      </section>
    </>
  )
}
