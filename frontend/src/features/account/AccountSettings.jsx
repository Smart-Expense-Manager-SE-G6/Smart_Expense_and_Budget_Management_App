import { useState } from 'react'
import { api, apiDownload } from '../../api'
import { useAuth } from '../../auth/context'
import FormField from '../../components/FormField'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import Modal from '../../components/ui/Modal'
import Notice from '../../components/ui/Notice'

// FR2 "manage account settings" and NFR14 (S3-09): notifications, password, data export, account deletion.

function saveBlob({ blob, filename }) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function EmailAlertsCard() {
  const { user, updateProfile } = useAuth()
  const [checked, setChecked] = useState(user.email_alerts)
  const [error, setError] = useState(null)

  // Show the change at once; put it back if saving fails.
  async function toggle(event) {
    const value = event.target.checked
    setChecked(value)
    setError(null)
    try {
      await updateProfile({ email_alerts: value })
    } catch (err) {
      setChecked(!value)
      setError(err)
    }
  }

  return (
    <Card title="Notifications" subtitle="Budget and unusual-spending alerts always appear in the app.">
      {error && <Notice tone="danger">{error.message}</Notice>}
      <label className="toggle-row">
        <input type="checkbox" checked={checked} onChange={toggle} />
        <span>
          <strong>Email me my alerts</strong>
          <span className="muted"> Sent to {user.email} through our email provider.</span>
        </span>
      </label>
    </Card>
  )
}

function PasswordCard() {
  const empty = { current_password: '', new_password: '', confirm: '' }
  const [form, setForm] = useState(empty)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const update = (event) => {
    setDone(false)
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    if (form.new_password !== form.confirm) {
      setError({ field: 'confirm', message: 'The new passwords do not match.' })
      return
    }
    setBusy(true)
    setError(null)
    try {
      await api('/me/password/', {
        method: 'POST',
        body: { current_password: form.current_password, new_password: form.new_password },
      })
      setForm(empty)
      setDone(true)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const fieldError = (name) => (error?.field === name ? error.message : null)
  return (
    <Card title="Password" subtitle="Changing it signs you out on every other device.">
      <form className="form" onSubmit={submit} noValidate>
        {error && !['current_password', 'new_password', 'confirm'].includes(error.field) && (
          <Notice tone="danger">{error.message}</Notice>
        )}
        {done && <Notice tone="success">Password changed. Other devices have been signed out.</Notice>}
        <FormField label="Current password" name="current_password" type="password" autoComplete="current-password"
          value={form.current_password} onChange={update} error={fieldError('current_password')} required />
        <div className="field-row">
          <FormField label="New password" name="new_password" type="password" autoComplete="new-password"
            value={form.new_password} onChange={update} error={fieldError('new_password')} required
            hint="At least 8 characters; not a common password." />
          <FormField label="Confirm new password" name="confirm" type="password" autoComplete="new-password"
            value={form.confirm} onChange={update} error={fieldError('confirm')} required />
        </div>
        <div>
          <Button type="submit" variant="primary" loading={busy}>
            Change password
          </Button>
        </div>
      </form>
    </Card>
  )
}

function DataCard() {
  const { logout } = useAuth()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [password, setPassword] = useState('')
  const [deleteError, setDeleteError] = useState(null)
  const [deleting, setDeleting] = useState(false)

  async function download() {
    setBusy(true)
    setError(null)
    try {
      saveBlob(await apiDownload('/me/export/'))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  async function deleteAccount(event) {
    event.preventDefault()
    setDeleting(true)
    setDeleteError(null)
    try {
      await api('/me/', { method: 'DELETE', body: { password } })
      await logout()
    } catch (err) {
      setDeleteError(err)
      setDeleting(false)
    }
  }

  function close() {
    setConfirming(false)
    setPassword('')
    setDeleteError(null)
  }

  return (
    <Card title="Your data" subtitle="Your financial data is never shared with anyone else.">
      {error && <Notice tone="danger">{error.message}</Notice>}
      <div className="data-actions">
        <div>
          <p className="data-action-title">Download my data</p>
          <p className="muted">A ZIP with your profile, expenses, receipts, budgets, alerts and history.</p>
          <Button icon="download" loading={busy} onClick={download}>
            Download ZIP
          </Button>
        </div>
        <div>
          <p className="data-action-title">Delete my account</p>
          <p className="muted">Permanently removes your account and everything in it.</p>
          <Button variant="danger" icon="trash" onClick={() => setConfirming(true)}>
            Delete account
          </Button>
        </div>
      </div>

      {confirming && (
        <Modal
          open
          title="Delete your account?"
          description="This cannot be undone."
          onClose={close}
          footer={
            <>
              <Button onClick={close} disabled={deleting}>
                Cancel
              </Button>
              <Button variant="danger" type="submit" form="delete-account-form" loading={deleting}>
                Delete everything
              </Button>
            </>
          }
        >
          <form id="delete-account-form" className="modal-body form" onSubmit={deleteAccount} noValidate>
            <p>
              Your expenses, receipts, categories, recurring rules, budgets, alerts and history will be deleted.
              Budgets you share with others are deleted for them too; download your data first if you need it.
            </p>
            {deleteError && deleteError.field !== 'password' && <Notice tone="danger">{deleteError.message}</Notice>}
            <FormField label="Enter your password to confirm" name="password" type="password"
              autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)}
              error={deleteError?.field === 'password' ? deleteError.message : null} required />
          </form>
        </Modal>
      )}
    </Card>
  )
}

export default function AccountSettings() {
  return (
    <>
      <EmailAlertsCard />
      <PasswordCard />
      <DataCard />
    </>
  )
}
