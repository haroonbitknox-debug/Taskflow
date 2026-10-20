import { useState } from 'react'
import { useAuth } from '../hooks/useAuth.js'
import FormError from '../components/FormError.jsx'
import { usersApi } from '../services/api.js'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../hooks/useToast.js'

function ProfilePage() {
  const { user, refreshUser, changePassword, getApiErrorMessage } = useAuth()
  const navigate = useNavigate()
  const notify = useToast()
  const [fullName, setFullName] = useState(user.full_name)
  const [email, setEmail] = useState(user.email)
  const [profileError, setProfileError] = useState('')
  const [profileSuccess, setProfileSuccess] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)
  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })

  async function updateProfile(event) {
    event.preventDefault()
    setProfileError('')
    setProfileSuccess('')
    setSavingProfile(true)
    try {
      await usersApi.updateProfile({ full_name: fullName, email })
      await refreshUser()
      setProfileSuccess('Your profile was updated.')
      notify('Profile updated.')
    } catch (error) {
      setProfileError(getApiErrorMessage(error))
    } finally {
      setSavingProfile(false)
    }
  }

  async function submitPasswordChange(event) {
    event.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')
    if (passwords.new_password !== passwords.confirm_password) {
      setPasswordError('The new passwords do not match.')
      return
    }
    setSavingPassword(true)
    try {
      await changePassword({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
      })
      setPasswords({
        current_password: '',
        new_password: '',
        confirm_password: '',
      })
      setPasswordSuccess('Password changed. Sign in again with your new password.')
      navigate('/login', { replace: true })
    } catch (error) {
      setPasswordError(getApiErrorMessage(error))
    } finally {
      setSavingPassword(false)
    }
  }

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-semibold text-indigo-600">Account</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Profile & settings</h1><p className="mt-2 text-sm text-slate-500">Update your account details and password.</p></header>
      <div className="grid gap-6">
        <form
          className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          onSubmit={updateProfile}
        >
          <h2 className="text-lg font-semibold text-slate-900">Account details</h2>
          <FormError>{profileError}</FormError>
          {profileSuccess && (
            <p className="text-sm text-emerald-700" role="status">{profileSuccess}</p>
          )}
          <label className="block space-y-2 text-sm font-medium text-slate-700">
            Full name
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500"
              maxLength={120}
              minLength={2}
              onChange={(event) => setFullName(event.target.value)}
              required
              value={fullName}
            />
          </label>
          <label className="block space-y-2 text-sm font-medium text-slate-700">
            Email
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <p className="text-xs text-slate-500">
            Account role: {user.role}. Roles and account status cannot be edited here.
          </p>
          <button
            className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            disabled={savingProfile}
            type="submit"
          >
            {savingProfile ? 'Saving…' : 'Save profile'}
          </button>
        </form>

        <form
          className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          onSubmit={submitPasswordChange}
        >
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Change password</h2>
            <p className="mt-1 text-sm text-slate-600">
              Changing your password signs you out so you can sign in again.
            </p>
          </div>
          <FormError>{passwordError}</FormError>
          {passwordSuccess && (
            <p className="text-sm text-emerald-700" role="status">{passwordSuccess}</p>
          )}
          {[
            ['current_password', 'Current password', 'current-password'],
            ['new_password', 'New password', 'new-password'],
            ['confirm_password', 'Confirm new password', 'new-password'],
          ].map(([field, label, autocomplete]) => (
            <label className="block space-y-2 text-sm font-medium text-slate-700" key={field}>
              {label}
              <input
                autoComplete={autocomplete}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-indigo-500"
                minLength={field === 'current_password' ? undefined : 12}
                onChange={(event) =>
                  setPasswords((current) => ({ ...current, [field]: event.target.value }))
                }
                required
                type="password"
                value={passwords[field]}
              />
            </label>
          ))}
          <button
            className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            disabled={savingPassword}
            type="submit"
          >
            {savingPassword ? 'Updating…' : 'Change password'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default ProfilePage
