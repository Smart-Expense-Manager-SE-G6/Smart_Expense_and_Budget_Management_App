import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import FormField from '../components/FormField'

const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone

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
    <main className="auth-card">
      <h1>Create your account</h1>
      <form onSubmit={handleSubmit} noValidate>
        {error && !['first_name', 'last_name', 'email', 'password'].includes(error.field) && (
          <p className="form-error" role="alert">
            {error.message}
          </p>
        )}
        <div className="field-row">
          <FormField label="First name" name="first_name" autoComplete="given-name"
            value={form.first_name} onChange={update} error={fieldError('first_name')} />
          <FormField label="Last name" name="last_name" autoComplete="family-name"
            value={form.last_name} onChange={update} error={fieldError('last_name')} />
        </div>
        <FormField label="Email" name="email" type="email" autoComplete="email" required
          value={form.email} onChange={update} error={fieldError('email')} />
        <FormField label="Password" name="password" type="password" autoComplete="new-password" required
          hint="At least 8 characters; not too common or similar to your name or email."
          value={form.password} onChange={update} error={fieldError('password')} />
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </main>
  )
}
