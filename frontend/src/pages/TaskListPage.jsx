import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, Eye, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { taskApi } from '../services/api.js'
import { useAuth } from '../hooks/useAuth.js'
import { useToast } from '../hooks/useToast.js'
import { Button, EmptyState, Modal, PriorityBadge, SelectField, Spinner, StatusBadge } from '../components/Ui.jsx'

const PAGE_SIZE = 10
const defaultFilters = { search: '', status: '', priority: '', overdue: false, sort_by: 'created_at', sort_direction: 'desc', due_from: '', due_to: '' }

function filterParams(filters) {
  const params = { page_size: PAGE_SIZE, ...filters }
  if (!params.status) delete params.status
  if (!params.priority) delete params.priority
  if (!params.search) delete params.search
  if (!params.due_from) delete params.due_from
  else params.due_from = new Date(`${params.due_from}T00:00:00`).toISOString()
  if (!params.due_to) delete params.due_to
  else params.due_to = new Date(`${params.due_to}T23:59:59.999`).toISOString()
  if (!params.overdue) delete params.overdue
  return params
}

function TaskListPage() {
  const { user } = useAuth()
  const notify = useToast()
  const location = useLocation()
  const admin = user?.role === 'admin' && location.pathname.startsWith('/admin')
  const [filters, setFilters] = useState(defaultFilters)
  const [query, setQuery] = useState(defaultFilters)
  const [page, setPage] = useState(1)
  const [pageData, setPageData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [removeTarget, setRemoveTarget] = useState(null)
  const [removing, setRemoving] = useState(false)
  const [currentTime] = useState(() => Date.now())

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    const timer = window.setTimeout(() => { setQuery(filters); setPage(1) }, 300)
    return () => window.clearTimeout(timer)
  }, [filters])

  useEffect(() => {
    const controller = new AbortController()
    // oxlint-disable-next-line react/set-state-in-effect
    setLoading(true)
    setError('')
    const params = { ...filterParams(query), page }
    const request = admin ? taskApi.adminList(params, { signal: controller.signal }) : taskApi.list(params, { signal: controller.signal })
    request.then(({ data }) => setPageData(data))
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.response?.status === 403 ? 'Administrator permission is required.' : 'Unable to load tasks. Please retry.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [admin, page, query])

  const tasks = pageData?.items ?? []
  const pageCount = Math.max(1, Math.ceil((pageData?.total ?? 0) / PAGE_SIZE))
  const sortOptions = useMemo(() => [['created_at', 'Created date'], ['due_date', 'Due date'], ['priority', 'Priority'], ['title', 'Title']], [])

  function changeFilter(name, value) { setFilters((current) => ({ ...current, [name]: value })) }

  async function toggleCompleted(task) {
    try {
      if (admin) await taskApi.adminUpdate(task.id, { status: task.status === 'completed' ? 'pending' : 'completed' })
      else await taskApi.update(task.id, { status: task.status === 'completed' ? 'pending' : 'completed' })
      notify(task.status === 'completed' ? 'Task reopened.' : 'Task completed.')
      const response = admin ? await taskApi.adminList({ ...filterParams(query), page }) : await taskApi.list({ ...filterParams(query), page })
      setPageData(response.data)
      window.dispatchEvent(new Event('taskflow:data-changed'))
    } catch (failure) { notify(failure.response?.data?.detail || 'Could not update task.', 'error') }
  }

  async function deleteTask() {
    if (!removeTarget) return
    setRemoving(true)
    try {
      if (admin) await taskApi.adminRemove(removeTarget.id)
      else await taskApi.remove(removeTarget.id)
      notify('Task deleted.')
      setRemoveTarget(null)
      setPageData((current) => current ? { ...current, items: current.items.filter((item) => item.id !== removeTarget.id), total: current.total - 1 } : current)
      if (tasks.length === 1 && page > 1) setPage((current) => current - 1)
      window.dispatchEvent(new Event('taskflow:data-changed'))
    } catch (failure) { notify(failure.response?.data?.detail || 'Could not delete the task.', 'error') }
    finally { setRemoving(false) }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold text-indigo-600">{admin ? 'Workspace' : 'Your workspace'}</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{admin ? 'All tasks' : 'My tasks'}</h1><p className="mt-2 text-sm text-slate-500">{pageData?.total ?? 0} tasks · Find and organize work with flexible filters.</p></div><Link to={admin ? '/admin/tasks/new' : '/tasks/new'}><Button><Plus size={17} /> New task</Button></Link></div>
    <section aria-label="Task filters" className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6">
      <label className="relative block sm:col-span-2"><span className="sr-only">Search tasks</span><Search aria-hidden="true" className="absolute left-3 top-3 text-slate-400" size={17} /><input className="field-input pl-9" onChange={(event) => changeFilter('search', event.target.value)} placeholder="Search tasks, tags, categories…" value={filters.search} /></label>
      <SelectField id="status-filter" label="Status" onChange={(event) => changeFilter('status', event.target.value)} options={ [['', 'All statuses'], ['pending', 'Pending'], ['in_progress', 'In progress'], ['completed', 'Completed']] } value={filters.status} />
      <SelectField id="priority-filter" label="Priority" onChange={(event) => changeFilter('priority', event.target.value)} options={ [['', 'All priorities'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']] } value={filters.priority} />
      <SelectField id="sort-filter" label="Sort by" onChange={(event) => changeFilter('sort_by', event.target.value)} options={sortOptions} value={filters.sort_by} />
      <SelectField id="direction-filter" label="Direction" onChange={(event) => changeFilter('sort_direction', event.target.value)} options={ [['desc', 'Newest first'], ['asc', 'Oldest first']] } value={filters.sort_direction} />
      <label className="flex items-center gap-2 self-end rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-700"><input checked={filters.overdue} onChange={(event) => changeFilter('overdue', event.target.checked)} type="checkbox" /> Overdue only</label>
      <label className="text-xs font-medium text-slate-600">Due from<input aria-label="Due from" className="field-input mt-1" onChange={(event) => changeFilter('due_from', event.target.value)} type="date" value={filters.due_from} /></label>
      <label className="text-xs font-medium text-slate-600">Due to<input aria-label="Due to" className="field-input mt-1" onChange={(event) => changeFilter('due_to', event.target.value)} type="date" value={filters.due_to} /></label>
    </section>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">{error}</div>}
    {loading ? <Spinner label="Loading tasks" /> : tasks.length === 0 ? <EmptyState title="No tasks found" description={query.search || query.status || query.priority ? 'Try changing the search or filters.' : 'Create a task to start organizing your work.'} action={!admin && <Link to="/tasks/new"><Button><Plus size={16} /> Create task</Button></Link>} /> :
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="hidden overflow-x-auto md:block"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 font-semibold">Task</th>{admin && <th className="px-4 py-3 font-semibold">Owner</th>}<th className="px-4 py-3 font-semibold">Status</th><th className="px-4 py-3 font-semibold">Priority</th><th className="px-4 py-3 font-semibold">Due date</th><th className="px-4 py-3 text-right font-semibold">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{tasks.map((task) => { const overdue = task.due_date && new Date(task.due_date).getTime() < currentTime && task.status !== 'completed'; return <tr className="transition hover:bg-slate-50/70" key={task.id}><td className="max-w-[26rem] px-5 py-4"><div className="flex items-start gap-3"><button aria-label={task.status === 'completed' ? `Reopen ${task.title}` : `Complete ${task.title}`} className="mt-0.5 rounded-full text-slate-400 hover:text-emerald-600 focus-visible:outline-2 focus-visible:outline-indigo-600" onClick={() => toggleCompleted(task)} type="button"><CheckCircle2 size={18} /></button><div className="min-w-0"><Link className="font-semibold text-slate-900 hover:text-indigo-700" to={`${admin ? '/admin/tasks' : '/tasks'}/${task.id}`}>{task.title}</Link><p className="mt-1 truncate text-xs text-slate-500">{task.category || 'Uncategorized'}{task.tags?.length ? ` · ${task.tags.join(', ')}` : ''}</p></div></div></td>{admin && <td className="px-4 py-4 text-slate-600">User #{task.user_id}</td>}<td className="px-4 py-4"><StatusBadge status={task.status} /></td><td className="px-4 py-4"><PriorityBadge priority={task.priority} /></td><td className={`px-4 py-4 ${overdue ? 'font-semibold text-rose-700' : 'text-slate-600'}`}>{task.due_date ? new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(task.due_date)) : '—'}{overdue && <AlertTriangle aria-label="Overdue" className="ml-1 inline" size={13} />}</td><td className="px-4 py-4"><div className="flex justify-end gap-1"><Link aria-label={`View ${task.title}`} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-indigo-700" to={`${admin ? '/admin/tasks' : '/tasks'}/${task.id}`}><Eye size={16} /></Link><Link aria-label={`Edit ${task.title}`} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-indigo-700" to={`${admin ? '/admin/tasks' : '/tasks'}/${task.id}/edit`}><Pencil size={16} /></Link><button aria-label={`Delete ${task.title}`} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-700" onClick={() => setRemoveTarget(task)} type="button"><Trash2 size={16} /></button></div></td></tr>})}</tbody></table></div>
        <div className="divide-y divide-slate-100 md:hidden">{tasks.map((task) => <article className="p-4" key={task.id}><div className="flex items-start justify-between gap-2"><div className="min-w-0"><Link className="font-semibold text-slate-900" to={`${admin ? '/admin/tasks' : '/tasks'}/${task.id}`}>{task.title}</Link><p className="mt-1 text-xs text-slate-500">{admin && `User #${task.user_id} · `}{task.category || 'Uncategorized'}</p></div><StatusBadge status={task.status} /></div><div className="mt-3 flex items-center justify-between"><span className="text-xs text-slate-500">Due {task.due_date ? new Date(task.due_date).toLocaleDateString() : '—'} · <PriorityBadge priority={task.priority} /></span><div className="flex gap-1"><button aria-label={task.status === 'completed' ? 'Reopen task' : 'Complete task'} className="rounded p-2 text-emerald-700" onClick={() => toggleCompleted(task)} type="button"><CheckCircle2 size={17} /></button><Link aria-label="Edit task" className="rounded p-2 text-indigo-700" to={`${admin ? '/admin/tasks' : '/tasks'}/${task.id}/edit`}><Pencil size={17} /></Link><button aria-label="Delete task" className="rounded p-2 text-rose-700" onClick={() => setRemoveTarget(task)} type="button"><Trash2 size={17} /></button></div></div></article>)}</div>
        <footer className="flex items-center justify-between border-t border-slate-100 px-4 py-3 sm:px-5"><p className="text-xs text-slate-500">Page {page} of {pageCount} · {pageData.total} results</p><div className="flex gap-2"><Button disabled={page <= 1} onClick={() => setPage((current) => current - 1)} variant="secondary"><ChevronLeft size={16} /> Previous</Button><Button disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)} variant="secondary">Next <ChevronRight size={16} /></Button></div></footer>
      </div>}
    {removeTarget && <Modal footer={<><Button disabled={removing} onClick={() => setRemoveTarget(null)} variant="secondary">Cancel</Button><Button disabled={removing} onClick={deleteTask} variant="danger">{removing ? 'Deleting…' : 'Delete task'}</Button></>} onClose={() => setRemoveTarget(null)} title="Delete task?"><p className="text-sm leading-6 text-slate-600">“{removeTarget.title}” will be permanently deleted. This action cannot be undone.</p></Modal>}
  </div>
}

export default TaskListPage
