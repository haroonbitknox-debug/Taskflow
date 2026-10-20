import { useEffect } from 'react'
import { LoaderCircle, X } from 'lucide-react'

export function Button({ children, className = '', variant = 'primary', ...props }) {
  const variants = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
    secondary: 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50',
    danger: 'bg-rose-600 text-white hover:bg-rose-700',
    ghost: 'text-slate-600 hover:bg-slate-100',
  }
  return (
    <button className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Field({ label, id, className = '', children, ...props }) {
  return (
    <label className={`block space-y-1.5 text-sm font-medium text-slate-700 ${className}`} htmlFor={id}>
      {label}
      {children ?? <input className="field-input" id={id} {...props} />}
    </label>
  )
}

export function SelectField({ label, id, options, ...props }) {
  return (
    <Field id={id} label={label}>
      <select className="field-input" id={id} {...props}>
        {options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
      </select>
    </Field>
  )
}

export function Spinner({ label = 'Loading' }) {
  return <div aria-label={label} className="flex min-h-40 items-center justify-center text-indigo-600" role="status"><LoaderCircle className="animate-spin" size={25} /><span className="sr-only">{label}</span></div>
}

export function EmptyState({ title, description, action }) {
  return <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"><p className="font-semibold text-slate-900">{title}</p><p className="mt-2 text-sm text-slate-500">{description}</p>{action && <div className="mt-5">{action}</div>}</div>
}

export function Modal({ title, onClose, children, footer }) {
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/45 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section aria-labelledby="modal-title" aria-modal="true" className="my-auto max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white shadow-2xl" role="dialog">
        <header className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900" id="modal-title">{title}</h2>
          <button aria-label="Close dialog" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-600" onClick={onClose} type="button"><X size={18} /></button>
        </header>
        <div className="p-6">{children}</div>
        {footer && <footer className="flex justify-end gap-2 border-t border-slate-100 px-6 py-4">{footer}</footer>}
      </section>
    </div>
  )
}

export function StatusBadge({ status }) {
  const styles = {
    pending: 'bg-amber-50 text-amber-700 ring-amber-600/15',
    in_progress: 'bg-sky-50 text-sky-700 ring-sky-600/15',
    completed: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  }
  const label = status?.replace('_', ' ') ?? 'Unknown'
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${styles[status] ?? 'bg-slate-100 text-slate-700 ring-slate-500/10'}`}>{label}</span>
}

export function PriorityBadge({ priority }) {
  const styles = { high: 'text-rose-700', medium: 'text-amber-700', low: 'text-slate-500' }
  return <span className={`text-sm font-medium capitalize ${styles[priority] ?? 'text-slate-500'}`}>{priority}</span>
}
