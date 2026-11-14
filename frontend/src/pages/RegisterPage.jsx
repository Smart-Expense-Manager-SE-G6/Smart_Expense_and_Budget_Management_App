import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import AuthShell from '../components/layout/AuthShell'
import FormField from '../components/FormField'
import Button from '../components/ui/Button'
import Notice from '../components/ui/Notice'

const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone
const FIELDS = ['first_name', 'last_name', 'email', 'password']

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await register({ ...form, timezone: browserTimezone })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const fieldError = (name) => (error?.field === name ? error.message : null)

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start tracking your spending in under a minute."
      footer={
        <>
          Already have an account? <Link to="/login">Sign in</Link>
        </>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        {error && !FIELDS.includes(error.field) && <Notice tone="danger">{error.message}</Notice>}
        <div className="field-row">
          <FormField label="First name" name="first_name" autoComplete="given-name" placeholder="Asha" autoFocus
            value={form.first_name} onChange={update} error={fieldError('first_name')} />
          <FormField label="Last name" name="last_name" autoComplete="family-name" placeholder="Rao"
            value={form.last_name} onChange={update} error={fieldError('last_name')} />
        </div>
        <FormField label="Email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required
          value={form.email} onChange={update} error={fieldError('email')} />
        <FormField label="Password" name="password" type="password" autoComplete="new-password" required
          hint="At least 8 characters; not too common or similar to your name or email."
          value={form.password} onChange={update} error={fieldError('password')} />
        <Button type="submit" variant="primary" size="lg" block loading={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthShell>
  )
}
