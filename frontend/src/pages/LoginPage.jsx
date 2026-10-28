import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import FormField from '../components/FormField'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login(form.email, form.password)
      navigate(location.state?.from ?? '/', { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const fieldError = (name) => (error?.field === name ? error.message : null)

  return (
    <main className="auth-card">
      <h1>Sign in</h1>
      <form onSubmit={handleSubmit} noValidate>
        {error && !error.field && (
          <p className="form-error" role="alert">
            {error.message}
          </p>
        )}
        <FormField label="Email" name="email" type="email" autoComplete="email" required
          value={form.email} onChange={update} error={fieldError('email')} />
        <FormField label="Password" name="password" type="password" autoComplete="current-password" required
          value={form.password} onChange={update} error={fieldError('password')} />
        <button type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p>
        New here? <Link to="/register">Create an account</Link>
      </p>
    </main>
  )
}
