import { Link } from 'react-router-dom'

function AuthLayout({ title, description, children, footer }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-5 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-sm sm:p-9">
        <Link className="text-sm font-semibold text-indigo-700" to="/">
          TaskFlow
        </Link>
        <h1 className="mt-7 text-3xl font-semibold tracking-tight text-slate-950">
          {title}
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
        <div className="mt-7">{children}</div>
        <div className="mt-6 border-t border-slate-100 pt-5 text-sm text-slate-600">
          {footer}
        </div>
      </section>
    </main>
  )
}

export default AuthLayout
