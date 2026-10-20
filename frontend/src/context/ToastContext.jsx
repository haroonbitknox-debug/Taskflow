import { useCallback, useState } from 'react'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'
import ToastContext from './toast-context.js'

const toastStyles = {
  success: { icon: CheckCircle2, className: 'border-emerald-200 text-emerald-800' },
  error: { icon: AlertCircle, className: 'border-rose-200 text-rose-800' },
  info: { icon: Info, className: 'border-sky-200 text-sky-800' },
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const dismiss = useCallback((id) => {
    setToasts((items) => items.filter((item) => item.id !== id))
  }, [])
  const notify = useCallback((message, type = 'success') => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((items) => [...items, { id, message, type }])
    window.setTimeout(() => dismiss(id), 4500)
  }, [dismiss])

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div aria-live="polite" className="fixed right-4 top-4 z-[60] flex w-[min(92vw,24rem)] flex-col gap-2">
        {toasts.map((toast) => {
          const style = toastStyles[toast.type] ?? toastStyles.info
          const Icon = style.icon
          return (
            <div className={`flex items-start gap-3 rounded-xl border bg-white p-4 shadow-lg ${style.className}`} key={toast.id} role="status">
              <Icon aria-hidden="true" className="mt-0.5 shrink-0" size={18} />
              <p className="flex-1 text-sm leading-5">{toast.message}</p>
              <button aria-label="Dismiss notification" className="rounded p-1 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-indigo-600" onClick={() => dismiss(toast.id)} type="button">
                <X size={15} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
