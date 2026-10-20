import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, ArrowRight, CheckCircle2, Clock3, ListTodo, RefreshCw, UserCheck, Users, UserX } from 'lucide-react'
import { Link } from 'react-router-dom'
import { taskApi } from '../services/api.js'
import { Button, EmptyState, Spinner, StatusBadge } from '../components/Ui.jsx'

function Metric({ label, value, icon: Icon, color }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><p className="text-sm font-medium text-slate-500">{label}</p><span className={`rounded-xl p-2.5 ${color}`}><Icon size={18} /></span></div><p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p></div>
}

function AdminDashboardPage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setError('')
    try {
      setSummary((await taskApi.adminSummary()).data)
    } catch {
      setError('Could not load system statistics. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    load()
    window.addEventListener('taskflow:data-changed', load)
    return () => window.removeEventListener('taskflow:data-changed', load)
  }, [load])
  if (loading) return <Spinner label="Loading administrator dashboard" />
  if (error) return <div className="rounded-2xl border border-rose-200 bg-white p-8 text-center"><p className="text-rose-700">{error}</p><Button className="mt-4" onClick={() => { setLoading(true); load() }}><RefreshCw size={16} /> Retry</Button></div>
  const statuses = [
    ['Pending', summary.task_status_counts.pending, Clock3, 'text-amber-700 bg-amber-50'],
    ['In progress', summary.task_status_counts.in_progress, Activity, 'text-sky-700 bg-sky-50'],
    ['Completed', summary.task_status_counts.completed, CheckCircle2, 'text-emerald-700 bg-emerald-50'],
  ]
  return <div className="space-y-7">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold text-indigo-600">Administration</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">System overview</h1><p className="mt-2 text-sm text-slate-500">Live statistics from across the TaskFlow workspace.</p></div><div className="flex gap-2"><Link to="/admin/users"><Button variant="secondary"><Users size={16} /> Manage users</Button></Link><Link to="/admin/tasks"><Button><ListTodo size={16} /> Manage tasks</Button></Link></div></div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Total users" value={summary.user_total} icon={Users} color="bg-indigo-50 text-indigo-700" />
      <Metric label="Active users" value={summary.active_users} icon={UserCheck} color="bg-emerald-50 text-emerald-700" />
      <Metric label="Inactive accounts" value={summary.inactive_users} icon={UserX} color="bg-slate-100 text-slate-700" />
      <Metric label="All tasks" value={summary.task_total} icon={ListTodo} color="bg-sky-50 text-sky-700" />
    </div>
    <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><Activity className="text-indigo-600" size={18} /><h2 className="font-semibold text-slate-900">Task status</h2></div><div className="mt-5 space-y-4">{statuses.map(([label, value, Icon, style]) => <div className="flex items-center justify-between" key={label}><span className="flex items-center gap-2 text-sm text-slate-600"><span className={`rounded-lg p-2 ${style}`}><Icon size={16} /></span>{label}</span><span className="font-bold text-slate-900">{value}</span></div>)}</div><div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4"><span className="flex items-center gap-2 text-sm text-rose-700"><AlertTriangle size={17} /> Overdue tasks</span><span className="font-bold text-rose-700">{summary.overdue_tasks}</span></div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Recent registrations</h2><p className="mt-1 text-sm text-slate-500">Latest accounts added</p></div><Link className="flex items-center gap-1 text-sm font-semibold text-indigo-600" to="/admin/users">All users <ArrowRight size={15} /></Link></div>{summary.recent_registrations.length === 0 ? <EmptyState title="No registrations" description="New accounts will appear here." /> : <div className="mt-4 divide-y divide-slate-100">{summary.recent_registrations.map((person) => <div className="flex items-center justify-between gap-3 py-3" key={person.id}><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{person.full_name}</p><p className="truncate text-xs text-slate-500">{person.email}</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize text-slate-600">{person.role}</span></div>)}</div>}</section>
    </div>
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Recent tasks</h2><p className="mt-1 text-sm text-slate-500">Latest task activity across all users</p></div><Link className="flex items-center gap-1 text-sm font-semibold text-indigo-600" to="/admin/tasks">All tasks <ArrowRight size={15} /></Link></div>{summary.recent_tasks.length === 0 ? <EmptyState title="No tasks yet" description="Tasks created in the workspace will appear here." /> : <div className="mt-4 divide-y divide-slate-100">{summary.recent_tasks.map((task) => <div className="flex items-center justify-between gap-3 py-3" key={task.id}><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{task.title}</p><p className="text-xs text-slate-500">Owner #{task.user_id} · {task.category || 'Uncategorized'}</p></div><StatusBadge status={task.status} /></div>)}</div>}</section>
  </div>
}

export default AdminDashboardPage
