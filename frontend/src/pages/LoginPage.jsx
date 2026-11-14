import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import AuthShell from '../components/layout/AuthShell'
import FormField from '../components/FormField'
import Button from '../components/ui/Button'
import Notice from '../components/ui/Notice'

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
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your account to continue."
      footer={
        <>
          New here? <Link to="/register">Create an account</Link>
        </>
      }
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        {error && !error.field && <Notice tone="danger">{error.message}</Notice>}
        <FormField label="Email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required autoFocus
          value={form.email} onChange={update} error={fieldError('email')} />
        <FormField label="Password" name="password" type="password" autoComplete="current-password" placeholder="••••••••" required
          value={form.password} onChange={update} error={fieldError('password')} />
        <Button type="submit" variant="primary" size="lg" block loading={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthShell>
  )
}
