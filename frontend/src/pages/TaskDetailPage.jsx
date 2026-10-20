import { useEffect, useState } from 'react'
import { AlertTriangle, ArrowLeft, CalendarDays, Pencil, Trash2 } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { taskApi } from '../services/api.js'
import { useToast } from '../hooks/useToast.js'
import { Button, Modal, PriorityBadge, Spinner, StatusBadge } from '../components/Ui.jsx'

function TaskDetailPage() {
  const { taskId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const notify = useToast()
  const admin = location.pathname.startsWith('/admin')
  const basePath = admin ? '/admin/tasks' : '/tasks'
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [saving, setSaving] = useState(false)
  const [currentTime] = useState(() => Date.now())
  useEffect(() => {
    let active = true
    const request = admin ? taskApi.adminGet(taskId) : taskApi.get(taskId)
    request.then(({ data }) => { if (active) setTask(data) })
      .catch((reason) => setError(reason.response?.status === 404 ? 'Task not found or you do not have access.' : 'Could not load the task.'))
      .finally(() => setLoading(false))
    return () => { active = false }
  }, [admin, taskId])

  async function toggleStatus() {
    const status = task.status === 'completed' ? 'pending' : 'completed'
    setSaving(true)
    try {
      const response = admin ? await taskApi.adminUpdate(task.id, { status }) : await taskApi.update(task.id, { status })
      setTask(response.data)
      notify(status === 'completed' ? 'Task completed.' : 'Task reopened.')
      window.dispatchEvent(new Event('taskflow:data-changed'))
    } catch (reason) { notify(reason.response?.data?.detail || 'Could not update task.', 'error') }
    finally { setSaving(false) }
  }
  async function removeTask() {
    setSaving(true)
    try {
      if (admin) await taskApi.adminRemove(task.id)
      else await taskApi.remove(task.id)
      notify('Task deleted.')
      window.dispatchEvent(new Event('taskflow:data-changed'))
      navigate(basePath, { replace: true })
    } catch (reason) { notify(reason.response?.data?.detail || 'Could not delete task.', 'error') }
    finally { setSaving(false); setConfirmDelete(false) }
  }

  if (loading) return <Spinner label="Loading task" />
  if (error || !task) return <div className="mx-auto max-w-2xl rounded-2xl border border-rose-200 bg-white p-8 text-center"><p className="text-rose-700" role="alert">{error || 'Task not found.'}</p><Link className="mt-4 inline-block text-sm font-semibold text-indigo-700" to={basePath}>Back to tasks</Link></div>
  const isOverdue = task.due_date && new Date(task.due_date).getTime() < currentTime && task.status !== 'completed'
  return <div className="mx-auto max-w-3xl space-y-6">
    <Link className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-700" to={basePath}><ArrowLeft size={16} /> Back to tasks</Link>
    <article className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-5 sm:p-7">
        <div className="flex flex-wrap items-center gap-2"><StatusBadge status={task.status} /><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold capitalize text-slate-600">{task.category || 'Uncategorized'}</span>{isOverdue && <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700"><AlertTriangle size={13} /> Overdue</span>}</div>
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{task.title}</h1>
        <p className="mt-2 text-sm text-slate-500">Created {new Date(task.created_at).toLocaleString()}{admin && ` · Owner user #${task.user_id}`}</p>
      </div>
      <div className="space-y-6 p-5 sm:p-7">
        {task.description ? <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{task.description}</p> : <p className="text-sm italic text-slate-400">No description was added.</p>}
        <div className="grid gap-4 rounded-xl bg-slate-50 p-4 sm:grid-cols-2">
          <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Priority</p><div className="mt-2"><PriorityBadge priority={task.priority} /></div></div>
          <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Due date</p><p className={`mt-2 flex items-center gap-2 text-sm font-medium ${isOverdue ? 'text-rose-700' : 'text-slate-800'}`}><CalendarDays size={16} />{task.due_date ? new Date(task.due_date).toLocaleString() : 'No due date'}</p></div>
        </div>
        {task.tags?.length > 0 && <div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Tags</p><div className="flex flex-wrap gap-2">{task.tags.map((tag) => <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700" key={tag}>{tag}</span>)}</div></div>}
        <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-5">
          <Button disabled={saving} onClick={toggleStatus} variant="secondary">{task.status === 'completed' ? 'Reopen task' : 'Mark complete'}</Button>
          <Link to={`${basePath}/${task.id}/edit`}><Button variant="secondary"><Pencil size={16} /> Edit</Button></Link>
          <Button disabled={saving} onClick={() => setConfirmDelete(true)} variant="danger"><Trash2 size={16} /> Delete</Button>
        </div>
      </div>
    </article>
    {confirmDelete && <Modal footer={<><Button onClick={() => setConfirmDelete(false)} variant="secondary">Cancel</Button><Button disabled={saving} onClick={removeTask} variant="danger">Delete task</Button></>} onClose={() => setConfirmDelete(false)} title="Delete task?"><p className="text-sm text-slate-600">This will permanently delete “{task.title}”.</p></Modal>}
  </div>
}

export default TaskDetailPage
