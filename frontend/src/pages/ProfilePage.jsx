import { useState } from 'react'
import { useAuth } from '../auth/context'
import FormField from '../components/FormField'

const timezones = Intl.supportedValuesOf('timeZone')

export default function ProfilePage() {
  const { user, updateProfile } = useAuth()
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    timezone: user.timezone,
  })
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const update = (event) => {
    setSaved(false)
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await updateProfile(form)
      setSaved(true)
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const fieldError = (name) => (error?.field === name ? error.message : null)
  const options = timezones.includes(form.timezone) ? timezones : [form.timezone, ...timezones]

  return (
    <section className="card">
      <h1>Profile</h1>
      <form onSubmit={handleSubmit} noValidate>
        {error && !error.field && (
          <p className="form-error" role="alert">
            {error.message}
          </p>
        )}
        <FormField label="Email" name="email" type="email" value={user.email} readOnly
          hint="Email cannot be changed." />
        <div className="field-row">
          <FormField label="First name" name="first_name" autoComplete="given-name"
            value={form.first_name} onChange={update} error={fieldError('first_name')} />
          <FormField label="Last name" name="last_name" autoComplete="family-name"
            value={form.last_name} onChange={update} error={fieldError('last_name')} />
        </div>
        <FormField as="select" label="Time zone" name="timezone" value={form.timezone} onChange={update}
          error={fieldError('timezone')} hint="Budget periods start and end in this time zone.">
          {options.map((tz) => (
            <option key={tz} value={tz}>
              {tz}
            </option>
          ))}
        </FormField>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save changes'}
        </button>
        {saved && (
          <p className="success" role="status">
            Profile saved.
          </p>
        )}
      </form>
    </section>
  )
}
