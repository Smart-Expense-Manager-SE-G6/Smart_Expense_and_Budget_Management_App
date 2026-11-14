import { useEffect, useRef } from 'react'
import Button from './Button'

// Accessible modal on the native <dialog>: focus trap, Esc to close and inert backdrop come for free.
export default function Modal({ open, title, description, onClose, footer, children }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  if (!open) return null

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onMouseDown={(event) => event.target === ref.current && onClose()}
    >
      <div className="modal-header">
        <div>
          <h2 id="modal-title" className="modal-title">
            {title}
          </h2>
          {description && <p className="card-subtitle">{description}</p>}
        </div>
        <Button variant="ghost" size="sm" iconOnly icon="x" aria-label="Close dialog" onClick={onClose} />
      </div>
      {children}
      {footer && <div className="modal-footer">{footer}</div>}
    </dialog>
  )
}

