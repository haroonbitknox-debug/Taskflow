import { ArrowRight, Check, ListTodo } from 'lucide-react'
import { Link } from 'react-router-dom'
import ApiHealthCheck from '../components/ApiHealthCheck.jsx'
import { useAuth } from '../hooks/useAuth.js'

function HomePage() {
  const { user, loading } = useAuth()

  return (
    <main className="min-h-screen px-6 py-10 sm:px-10 sm:py-14">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl flex-col">
        <header className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <ListTodo aria-hidden="true" size={22} />
          </span>
          <span className="text-lg font-semibold tracking-tight text-slate-900">
            TaskFlow
          </span>
          <nav className="ml-auto flex items-center gap-4 text-sm font-medium">
            {!loading && user ? (
              <Link className="text-indigo-700 hover:text-indigo-900" to="/app">
                Open workspace
              </Link>
            ) : (
              <>
                <Link className="text-slate-600 hover:text-indigo-700" to="/login">
                  Sign in
                </Link>
                <Link
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700"
                  to="/register"
                >
                  Create account
                </Link>
              </>
            )}
          </nav>
        </header>

        <section className="grid flex-1 items-center gap-12 py-16 md:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white px-3 py-1.5 text-sm font-medium text-indigo-700">
              <Check aria-hidden="true" size={15} />
              Your workspace is ready
            </p>
            <h1 className="max-w-xl text-5xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
              Make space for work that matters.
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600">
              TaskFlow brings your tasks into focus. Your development
              workspace is set up and ready for the next phase.
            </p>
            <a
              className="mt-8 inline-flex items-center gap-2 font-medium text-indigo-700 transition hover:text-indigo-900"
              href="#api-status"
            >
              Check the API connection
              <ArrowRight aria-hidden="true" size={17} />
            </a>
          </div>

          <ApiHealthCheck />
        </section>

        <footer className="border-t border-slate-200 py-5 text-sm text-slate-500">
          TaskFlow · Development environment
        </footer>
      </div>
    </main>
  )
}

export default HomePage
