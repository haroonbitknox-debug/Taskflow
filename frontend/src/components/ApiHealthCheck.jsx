import { useEffect, useState } from 'react'
import { Activity, AlertCircle, CheckCircle2, LoaderCircle } from 'lucide-react'
import { getHealth } from '../services/api.js'

function ApiHealthCheck() {
  const [status, setStatus] = useState({ state: 'loading' })

  useEffect(() => {
    let isMounted = true

    getHealth()
      .then((response) => {
        if (isMounted) {
          setStatus({ state: 'success', message: response.data.status })
        }
      })
      .catch((error) => {
        if (isMounted) {
          setStatus({
            state: 'error',
            message: error.message || 'The API could not be reached.',
          })
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  const statusDetails = {
    loading: {
      Icon: LoaderCircle,
      label: 'Connecting to the backend',
      text: 'Waiting for the health-check response…',
      iconClass: 'animate-spin text-indigo-600',
    },
    success: {
      Icon: CheckCircle2,
      label: 'Backend is online',
      text: `Health check returned: ${status.message}`,
      iconClass: 'text-emerald-600',
    },
    error: {
      Icon: AlertCircle,
      label: 'Backend connection failed',
      text: status.message,
      iconClass: 'text-rose-600',
    },
  }
  const { Icon, label, text, iconClass } = statusDetails[status.state]

  return (
    <aside
      id="api-status"
      aria-live="polite"
      className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm sm:p-8"
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
        <Activity aria-hidden="true" size={21} />
      </div>
      <h2 className="mt-6 text-lg font-semibold text-slate-900">
        API connection
      </h2>
      <div className="mt-5 flex items-start gap-3">
        <Icon
          aria-hidden="true"
          className={`mt-0.5 shrink-0 ${iconClass}`}
          size={20}
        />
        <div>
          <p className="font-medium text-slate-800">{label}</p>
          <p className="mt-1 break-words text-sm leading-6 text-slate-500">
            {text}
          </p>
        </div>
      </div>
      <p className="mt-6 border-t border-slate-100 pt-4 text-xs text-slate-400">
        GET /api/health
      </p>
    </aside>
  )
}

export default ApiHealthCheck
