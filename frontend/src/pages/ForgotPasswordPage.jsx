import { useState } from 'react'
import { Link } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'
import FormError from '../components/FormError.jsx'
import { authApi } from '../services/api.js'
import { getApiErrorMessage } from '../utils/auth-errors.js'

function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await authApi.csrf()
      await authApi.requestPasswordReset({ email })
      setSubmitted(true)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      description="Enter the email address on your account and we’ll send reset instructions if it matches an account."
      footer={
        <Link className="font-medium text-indigo-700 hover:text-indigo-900" to="/login">
          Return to sign in
        </Link>
      }
    >
      {submitted ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm leading-6 text-emerald-800" role="status">
          If an account exists for that email, password reset instructions will be sent. Check your inbox, including spam.
        </p>
      ) : (
        <form className="space-y-5" onSubmit={handleSubmit}>
          <FormError>{error}</FormError>
          <label className="block space-y-2 text-sm font-medium text-slate-700">
            Email
            <input
              autoComplete="email"
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              maxLength={254}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <button
            className="w-full rounded-lg bg-indigo-600 px-4 py-3 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
            disabled={submitting}
            type="submit"
          >
            {submitting ? 'Sending…' : 'Send reset instructions'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}

export default ForgotPasswordPage
