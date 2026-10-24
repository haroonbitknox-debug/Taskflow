import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'
import FormError from '../components/FormError.jsx'
import { authApi } from '../services/api.js'
import { getApiErrorMessage } from '../utils/auth-errors.js'

function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('The passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await authApi.csrf()
      await authApi.confirmPasswordReset({ token, new_password: password })
      setSubmitted(true)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Set a new password"
      description="Choose a new password with at least 12 characters."
      footer={
        <Link className="font-medium text-indigo-700 hover:text-indigo-900" to="/login">
          Return to sign in
        </Link>
      }
    >
      {submitted ? (
        <div className="space-y-4">
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm leading-6 text-emerald-800" role="status">
            Your password has been reset. You can now sign in with your new password.
          </p>
          <Link className="block w-full rounded-lg bg-indigo-600 px-4 py-3 text-center font-medium text-white transition hover:bg-indigo-700" to="/login">
            Sign in
          </Link>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit}>
          <FormError>{error || (!token ? 'This reset link is missing its token. Request a new link to continue.' : '')}</FormError>
          <label className="block space-y-2 text-sm font-medium text-slate-700">
            New password
            <span className="relative block">
              <input
                autoComplete="new-password"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 pr-11 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                maxLength={128}
                minLength={12}
                onChange={(event) => setPassword(event.target.value)}
                required
                type={showPassword ? 'text' : 'password'}
                value={password}
              />
              <button
                aria-label={showPassword ? 'Hide new password' : 'Show new password'}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 hover:text-slate-700"
                onClick={() => setShowPassword((visible) => !visible)}
                type="button"
              >
                {showPassword ? <EyeOff aria-hidden="true" size={18} /> : <Eye aria-hidden="true" size={18} />}
              </button>
            </span>
          </label>
          <label className="block space-y-2 text-sm font-medium text-slate-700">
            Confirm new password
            <span className="relative block">
              <input
                autoComplete="new-password"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 pr-11 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                maxLength={128}
                minLength={12}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                type={showConfirmation ? 'text' : 'password'}
                value={confirmPassword}
              />
              <button
                aria-label={showConfirmation ? 'Hide password confirmation' : 'Show password confirmation'}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-500 hover:text-slate-700"
                onClick={() => setShowConfirmation((visible) => !visible)}
                type="button"
              >
                {showConfirmation ? <EyeOff aria-hidden="true" size={18} /> : <Eye aria-hidden="true" size={18} />}
              </button>
            </span>
          </label>
          <button
            className="w-full rounded-lg bg-indigo-600 px-4 py-3 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
            disabled={submitting || !token}
            type="submit"
          >
            {submitting ? 'Resetting password…' : 'Reset password'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}

export default ResetPasswordPage
