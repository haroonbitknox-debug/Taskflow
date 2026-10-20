import { useEffect, useState } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { taskApi } from '../services/api.js'
import { useToast } from '../hooks/useToast.js'
import { Button, Field, SelectField, Spinner } from '../components/Ui.jsx'

const blank = { title: '', description: '', status: 'pending', priority: 'medium', category: '', tags: '', due_date: '', user_id: '' }

function localDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  const pad = (part) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function TaskFormPage() {
  const { taskId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const notify = useToast()
  const admin = location.pathname.startsWith('/admin')
  const basePath = admin ? '/admin/tasks' : '/tasks'
  const [form, setForm] = useState(blank)
  const [loading, setLoading] = useState(Boolean(taskId))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!taskId) return
    let active = true
    const request = admin ? taskApi.adminGet(taskId) : taskApi.get(taskId)
    request.then(({ data }) => {
      if (active) setForm({
        title: data.title,
        description: data.description ?? '',
        status: data.status,
        priority: data.priority,
        category: data.category ?? '',
        tags: data.tags.join(', '),
        due_date: localDateTime(data.due_date),
        user_id: String(data.user_id),
      })
    }).catch((reason) => setError(reason.response?.status === 404 ? 'Task not found or you do not have access.' : 'Could not load this task.'))
      .finally(() => setLoading(false))
    return () => { active = false }
  }, [admin, taskId])

  function update(field, value) { setForm((current) => ({ ...current, [field]: value })) }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setSaving(true)
    const payload = {
      title: form.title.trim(),
      description: form.description || null,
      status: form.status,
      priority: form.priority,
      category: form.category.trim() || null,
      tags: form.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
      due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
    }
    if (admin) payload.user_id = Number(form.user_id)
    try {
      const response = taskId
        ? (admin ? await taskApi.adminUpdate(taskId, payload) : await taskApi.update(taskId, payload))
        : (admin ? await taskApi.adminCreate(payload) : await taskApi.create(payload))
      notify(taskId ? 'Task updated.' : 'Task created.')
      window.dispatchEvent(new Event('taskflow:data-changed'))
      navigate(`${basePath}/${response.data.id}`, { replace: true })
    } catch (reason) {
      const detail = reason.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map((item) => `${item.loc?.slice(-1)[0]}: ${item.msg}`).join(' · ') : detail || 'Could not save this task.')
    } finally { setSaving(false) }
  }

  if (loading) return <Spinner label="Loading task" />
  return <div className="mx-auto max-w-3xl space-y-6">
    <Link className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-700" to={taskId ? `${basePath}/${taskId}` : basePath}><ArrowLeft size={16} /> Back to {taskId ? 'task' : 'tasks'}</Link>
    <header><p className="text-sm font-semibold text-indigo-600">{admin ? 'Administrator task' : 'Task workspace'}</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">{taskId ? 'Edit task' : 'Create a task'}</h1><p className="mt-2 text-sm text-slate-500">{taskId ? 'Update task details and progress.' : 'Add the details to keep work moving forward.'}</p></header>
    <form className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7" onSubmit={submit}>
      {error && <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-800" role="alert">{error}</p>}
      <Field id="task-title" label="Task title"><input autoFocus className="field-input" id="task-title" maxLength={200} onChange={(event) => update('title', event.target.value)} placeholder="e.g. Prepare project proposal" required value={form.title} /></Field>
      <Field id="task-description" label="Description"><textarea className="field-input min-h-28 resize-y" id="task-description" maxLength={10000} onChange={(event) => update('description', event.target.value)} placeholder="Add context, notes, or next steps…" value={form.description} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField id="task-status" label="Status" onChange={(event) => update('status', event.target.value)} options={ [['pending', 'Pending'], ['in_progress', 'In progress'], ['completed', 'Completed']] } value={form.status} />
        <SelectField id="task-priority" label="Priority" onChange={(event) => update('priority', event.target.value)} options={ [['low', 'Low'], ['medium', 'Medium'], ['high', 'High']] } value={form.priority} />
        <Field id="task-category" label="Category"><input className="field-input" id="task-category" maxLength={80} onChange={(event) => update('category', event.target.value)} placeholder="e.g. Work" value={form.category} /></Field>
        <Field id="task-due" label="Due date"><input className="field-input" id="task-due" onChange={(event) => update('due_date', event.target.value)} type="datetime-local" value={form.due_date} /></Field>
      </div>
      <Field id="task-tags" label="Tags"><input className="field-input" id="task-tags" onChange={(event) => update('tags', event.target.value)} placeholder="Design, research, Q4 (comma separated)" value={form.tags} /></Field>
      {admin && <Field id="task-owner" label="Owner user ID"><input className="field-input" id="task-owner" min="1" onChange={(event) => update('user_id', event.target.value)} required type="number" value={form.user_id} /><span className="block text-xs font-normal text-slate-500">The target account must exist and be active.</span></Field>}
      <div className="flex flex-wrap justify-end gap-3 border-t border-slate-100 pt-5"><Link to={taskId ? `${basePath}/${taskId}` : basePath}><Button type="button" variant="secondary">Cancel</Button></Link><Button disabled={saving}>{saving ? 'Saving…' : <><Save size={16} /> Save task</>}</Button></div>
    </form>
  </div>
}

export default TaskFormPage
