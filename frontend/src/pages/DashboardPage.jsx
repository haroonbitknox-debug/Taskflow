import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ArrowRight, CalendarDays, CheckCircle2, Circle, Clock3, ListTodo, Plus, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { taskApi } from '../services/api.js'
import { useAuth } from '../hooks/useAuth.js'
import { Button, EmptyState, Spinner, StatusBadge } from '../components/Ui.jsx'

const chartColors = ['#f59e0b', '#0ea5e9', '#10b981']

function StatCard({ label, value, detail, icon: Icon, tone = 'indigo' }) {
  const tones = {
    indigo: 'bg-indigo-50 text-indigo-700',
    amber: 'bg-amber-50 text-amber-700',
    sky: 'bg-sky-50 text-sky-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    rose: 'bg-rose-50 text-rose-700',
  }
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
    <div className="flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p></div><span className={`rounded-xl p-2.5 ${tones[tone]}`}><Icon aria-hidden="true" size={19} /></span></div>
    {detail && <p className="mt-2 text-xs text-slate-500">{detail}</p>}
  </article>
}

function formatDate(date) {
  if (!date) return 'No due date'
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(date))
}

function UserDashboard() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setError('')
    try {
      const response = await taskApi.summary()
      setSummary(response.data)
    } catch {
      setError('We could not load your dashboard. Check your connection and try again.')
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

  const chartData = useMemo(() => summary ? [
    { name: 'Pending', value: summary.status_counts.pending },
    { name: 'In progress', value: summary.status_counts.in_progress },
    { name: 'Completed', value: summary.status_counts.completed },
  ] : [], [summary])

  if (loading) return <Spinner label="Loading dashboard" />
  if (error) return <section className="rounded-2xl border border-rose-200 bg-white p-8 text-center"><AlertTriangle className="mx-auto text-rose-600" size={28} /><h1 className="mt-3 text-lg font-semibold">Dashboard unavailable</h1><p className="mt-2 text-sm text-slate-600">{error}</p><Button className="mt-5" onClick={() => { setLoading(true); load() }}><RefreshCw size={16} /> Try again</Button></section>

  const recent = summary?.recent_tasks ?? []
  const tasks = [
    { label: 'Total tasks', value: summary.task_total, icon: ListTodo, tone: 'indigo', detail: 'In your workspace' },
    { label: 'Pending', value: summary.status_counts.pending, icon: Circle, tone: 'amber', detail: 'Ready when you are' },
    { label: 'In progress', value: summary.status_counts.in_progress, icon: Clock3, tone: 'sky', detail: 'Currently underway' },
    { label: 'Completed', value: summary.status_counts.completed, icon: CheckCircle2, tone: 'emerald', detail: `${summary.completion_percentage}% completion rate` },
    { label: 'Overdue', value: summary.overdue_tasks, icon: AlertTriangle, tone: 'rose', detail: 'Needs your attention' },
    { label: 'Due today', value: summary.due_today, icon: CalendarDays, tone: 'amber', detail: `${summary.upcoming_tasks} upcoming` },
  ]
  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-sm font-semibold text-indigo-600">Your workspace</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Good to see you, {user?.full_name?.split(' ')[0]}</h1><p className="mt-2 text-sm text-slate-500">Here’s what’s happening with your tasks.</p></div>
        <Link to="/tasks/new"><Button><Plus size={17} /> Create task</Button></Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{tasks.map((item) => <StatCard {...item} key={item.label} />)}</div>
      <div className="grid gap-5 xl:grid-cols-[1fr_1.3fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div><h2 className="font-semibold text-slate-900">Task distribution</h2><p className="mt-1 text-sm text-slate-500">A breakdown of your current workload</p></div>
          {summary.task_total === 0 ? <EmptyState title="No tasks yet" description="Create a task to see your progress here." action={<Link className="text-sm font-semibold text-indigo-600" to="/tasks/new">Create your first task <ArrowRight className="inline" size={14} /></Link>} /> : <div className="mt-3 grid items-center gap-3 sm:grid-cols-[1fr_0.8fr]">
            <div className="h-56 min-w-0"><ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={chartData} dataKey="value" innerRadius={60} outerRadius={88} paddingAngle={3} stroke="none">{chartData.map((entry, index) => <Cell fill={chartColors[index]} key={entry.name} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
            <div className="space-y-4">{chartData.map((entry, index) => <div className="flex items-center justify-between gap-4" key={entry.name}><span className="flex items-center gap-2 text-sm text-slate-600"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: chartColors[index] }} />{entry.name}</span><span className="font-semibold text-slate-900">{entry.value}</span></div>)}<div className="border-t border-slate-100 pt-3"><p className="text-xs text-slate-500">Completion</p><p className="mt-1 text-2xl font-bold text-slate-900">{summary.completion_percentage}%</p></div></div>
          </div>}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-center justify-between"><div><h2 className="font-semibold text-slate-900">Recently updated</h2><p className="mt-1 text-sm text-slate-500">Your latest tasks</p></div><Link className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-700" to="/tasks">View all <ArrowRight size={15} /></Link></div>
          {recent.length === 0 ? <EmptyState title="Nothing to show yet" description="Your recent tasks will appear here." /> : <div className="mt-5 divide-y divide-slate-100">{recent.map((task) => <Link className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 hover:bg-slate-50/60" key={task.id} to={`/tasks/${task.id}`}><div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{task.title}</p><p className="mt-1 text-xs text-slate-500">{task.category || 'Uncategorized'} · Due {formatDate(task.due_date)}</p></div><StatusBadge status={task.status} /></Link>)}</div>}
        </section>
      </div>
    </div>
  )
}

export default UserDashboard
