import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'
import FormError from '../components/FormError.jsx'
import { useAuth } from '../hooks/useAuth.js'

function RegisterPage() {
  const { register, getApiErrorMessage } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function update(field) {
    return (event) =>
      setForm((current) => ({ ...current, [field]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (form.password !== form.confirmPassword) {
      setError('The passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await register({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      })
      navigate('/app', { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Start organizing work with a personal TaskFlow account."
      footer={
        <>
          Already have an account?{' '}
          <Link className="font-medium text-indigo-700 hover:text-indigo-900" to="/login">
            Sign in
          </Link>
        </>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormError>{error}</FormError>
        <label className="block space-y-2 text-sm font-medium text-slate-700">
          Full name
          <input
            autoComplete="name"
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            maxLength={120}
            minLength={2}
            onChange={update('full_name')}
            required
            value={form.full_name}
          />
        </label>
        <label className="block space-y-2 text-sm font-medium text-slate-700">
          Email
          <input
            autoComplete="email"
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            onChange={update('email')}
            required
            type="email"
            value={form.email}
          />
        </label>
        <label className="block space-y-2 text-sm font-medium text-slate-700">
          Password
          <input
            autoComplete="new-password"
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            minLength={12}
            onChange={update('password')}
            required
            type="password"
            value={form.password}
          />
          <span className="block text-xs font-normal text-slate-500">
            Use at least 12 characters.
          </span>
        </label>
        <label className="block space-y-2 text-sm font-medium text-slate-700">
          Confirm password
          <input
            autoComplete="new-password"
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            onChange={update('confirmPassword')}
            required
            type="password"
            value={form.confirmPassword}
          />
        </label>
        <button
          className="w-full rounded-lg bg-indigo-600 px-4 py-3 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
          disabled={submitting}
          type="submit"
        >
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}

export default RegisterPage
