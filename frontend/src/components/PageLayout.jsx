import { ArrowLeft, ListTodo, LogOut, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import FormError from './FormError.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { useState } from 'react'

function PageLayout({ children, title, description }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [logoutError, setLogoutError] = useState('')

  async function handleLogout() {
    setLogoutError('')
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      setLogoutError('Could not sign out. Check your connection and try again.')
    }
  }

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <Link className="flex items-center gap-3" to="/">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <ListTodo aria-hidden="true" size={21} />
            </span>
            <span className="font-semibold text-slate-900">TaskFlow</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link
              className="inline-flex items-center gap-2 text-slate-600 hover:text-indigo-700"
              to="/profile"
            >
              <UserRound aria-hidden="true" size={16} />
              {user?.full_name}
            </Link>
            <button
              className="inline-flex items-center gap-2 text-slate-600 hover:text-indigo-700"
              onClick={handleLogout}
              type="button"
            >
              <LogOut aria-hidden="true" size={16} />
              Sign out
            </button>
          </nav>
        </header>

        <section className="mt-12">
          <FormError>{logoutError}</FormError>
          {title && (
            <div className="mb-8">
              <Link
                className="mb-4 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-indigo-700"
                to="/app"
              >
                <ArrowLeft aria-hidden="true" size={16} />
                Back to workspace
              </Link>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
                {title}
              </h1>
              {description && (
                <p className="mt-2 text-slate-600">{description}</p>
              )}
            </div>
          )}
          {children}
        </section>
      </div>
    </main>
  )
}

export default PageLayout
