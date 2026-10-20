import { ArrowRight, ShieldCheck, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import PageLayout from '../components/PageLayout.jsx'
import { useAuth } from '../hooks/useAuth.js'

function AppHomePage() {
  const { user } = useAuth()

  return (
    <PageLayout>
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <p className="text-sm font-medium text-indigo-700">Your workspace</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          Welcome, {user.full_name}
        </h1>
        <p className="mt-3 max-w-xl leading-7 text-slate-600">
          You are signed in. Task management features will be added in a later
          phase; your account and profile settings are ready here.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Link
            className="flex items-center justify-between rounded-xl border border-slate-200 p-5 transition hover:border-indigo-300 hover:bg-indigo-50/40"
            to="/profile"
          >
            <span className="flex items-center gap-3 text-sm font-medium text-slate-800">
              <UserRound aria-hidden="true" className="text-indigo-600" size={19} />
              Manage your profile
            </span>
            <ArrowRight aria-hidden="true" className="text-slate-400" size={17} />
          </Link>
          {user.role === 'admin' && (
            <Link
              className="flex items-center justify-between rounded-xl border border-slate-200 p-5 transition hover:border-indigo-300 hover:bg-indigo-50/40"
              to="/admin"
            >
              <span className="flex items-center gap-3 text-sm font-medium text-slate-800">
                <ShieldCheck aria-hidden="true" className="text-indigo-600" size={19} />
                Verify administrator access
              </span>
              <ArrowRight aria-hidden="true" className="text-slate-400" size={17} />
            </Link>
          )}
        </div>
      </div>
    </PageLayout>
  )
}

export default AppHomePage
