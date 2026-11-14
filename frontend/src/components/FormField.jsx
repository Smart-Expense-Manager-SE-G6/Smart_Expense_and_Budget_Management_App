import { useId } from 'react'

// Labelled input with an accessible error message (NFR7, NFR8).
export default function FormField({ label, error, hint, as = 'input', children, ...inputProps }) {
  const id = useId()
  const describedBy = [error && `${id}-error`, hint && `${id}-hint`].filter(Boolean).join(' ') || undefined
  const Control = as

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <Control id={id} aria-invalid={Boolean(error)} aria-describedby={describedBy} {...inputProps}>
        {children}
      </Control>
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
