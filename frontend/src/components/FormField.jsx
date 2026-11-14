import { useId } from 'react'

// Labelled input with an accessible error message (NFR7, NFR8).
// `prefix` renders a leading symbol inside the control (e.g. the rupee sign).
export default function FormField({ label, error, hint, prefix, as = 'input', children, ...inputProps }) {
  const id = useId()
  const describedBy = [error && `${id}-error`, hint && `${id}-hint`].filter(Boolean).join(' ') || undefined
  const Control = as
  const control = (
    <Control id={id} aria-invalid={Boolean(error)} aria-describedby={describedBy} {...inputProps}>
      {children}
    </Control>
  )

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {prefix ? (
        <div className="input-prefix">
          <span aria-hidden="true">{prefix}</span>
          {control}
        </div>
      ) : (
        control
      )}
      {hint && (
        <p id={`${id}-hint`} className="hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
