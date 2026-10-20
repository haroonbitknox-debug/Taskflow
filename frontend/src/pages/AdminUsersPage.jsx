import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Eye, Pencil, Plus, Search, Trash2, UserRound, UserRoundCheck } from 'lucide-react'
import { adminUserApi } from '../services/api.js'
import { useAuth } from '../hooks/useAuth.js'
import { useToast } from '../hooks/useToast.js'
import { Button, Field, Modal, SelectField, Spinner } from '../components/Ui.jsx'

const PAGE_SIZE = 10
const emptyForm = { full_name: '', email: '', password: '', role: 'user', is_active: true }

function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const notify = useToast()
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('')
  const [active, setActive] = useState('')
  const [page, setPage] = useState(1)
  const [users, setUsers] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [removeTarget, setRemoveTarget] = useState(null)

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    const timer = window.setTimeout(() => setQuery(search), 300)
    return () => window.clearTimeout(timer)
  }, [search])
  useEffect(() => {
    const controller = new AbortController()
    // oxlint-disable-next-line react/set-state-in-effect
    setLoading(true)
    setError('')
    const params = { page, page_size: PAGE_SIZE }
    if (query.trim()) params.search = query.trim()
    if (role) params.role = role
    if (active) params.is_active = active === 'active'
    adminUserApi.list(params, { signal: controller.signal }).then(({ data }) => setUsers(data))
      .catch((reason) => { if (!controller.signal.aborted) setError(reason.response?.data?.detail || 'Could not load user accounts.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [page, query, role, active])

  const pageCount = Math.max(1, Math.ceil((users?.total ?? 0) / PAGE_SIZE))
  function openCreate() { setForm(emptyForm); setModal({ mode: 'create' }) }
  function openEdit(person) { setForm({ ...person, password: '' }); setModal({ mode: 'edit', user: person }) }
  async function openView(person) {
    setSaving(true)
    try { setModal({ mode: 'view', user: (await adminUserApi.get(person.id)).data }) }
    catch (reason) { notify(reason.response?.data?.detail || 'Could not load account details.', 'error') }
    finally { setSaving(false) }
  }
  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    const payload = { full_name: form.full_name, email: form.email }
    if (modal.mode === 'create') Object.assign(payload, { password: form.password, role: form.role, is_active: form.is_active })
    else Object.assign(payload, { role: form.role, is_active: form.is_active })
    try {
      if (modal.mode === 'create') await adminUserApi.create(payload)
      else await adminUserApi.update(modal.user.id, payload)
      notify(modal.mode === 'create' ? 'User account created.' : 'User account updated.')
      setModal(null)
      const response = await adminUserApi.list({ page, page_size: PAGE_SIZE, ...(query ? { search: query } : {}), ...(role ? { role } : {}), ...(active ? { is_active: active === 'active' } : {}) })
      setUsers(response.data)
    } catch (reason) {
      const detail = reason.response?.data?.detail
      notify(Array.isArray(detail) ? detail.map((issue) => issue.msg).join(' ') : detail || 'Could not save user account.', 'error')
    } finally { setSaving(false) }
  }
  async function toggleActive(person) {
    try {
      await adminUserApi.update(person.id, { is_active: !person.is_active })
      notify(`Account ${person.is_active ? 'deactivated' : 'activated'}.`)
      const response = await adminUserApi.list({ page, page_size: PAGE_SIZE, ...(query ? { search: query } : {}), ...(role ? { role } : {}), ...(active ? { is_active: active === 'active' } : {}) })
      setUsers(response.data)
    } catch (reason) { notify(reason.response?.data?.detail || 'Could not update account status.', 'error') }
  }
  async function deleteUser() {
    if (!removeTarget) return
    setSaving(true)
    try {
      await adminUserApi.remove(removeTarget.id)
      notify('User account and associated private files deleted.')
      setRemoveTarget(null)
      setUsers((current) => current ? { ...current, items: current.items.filter((item) => item.id !== removeTarget.id), total: current.total - 1 } : current)
      if ((users?.items.length ?? 0) === 1 && page > 1) setPage((value) => value - 1)
    } catch (reason) { notify(reason.response?.data?.detail || 'Could not delete user account.', 'error') }
    finally { setSaving(false) }
  }
  function update(field, value) { setForm((current) => ({ ...current, [field]: value })) }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold text-indigo-600">Administration</p><h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">User management</h1><p className="mt-2 text-sm text-slate-500">Search accounts, manage roles, and control account access.</p></div><Button onClick={openCreate}><Plus size={17} /> Add user</Button></div>
    <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-[1fr_12rem_12rem]">
      <label className="relative"><span className="sr-only">Search users</span><Search className="absolute left-3 top-3 text-slate-400" size={17} /><input className="field-input pl-9" onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Search name or email…" value={search} /></label>
      <SelectField id="user-role-filter" label="Role" onChange={(event) => { setRole(event.target.value); setPage(1) }} options={ [['', 'All roles'], ['user', 'User'], ['admin', 'Admin']] } value={role} />
      <SelectField id="user-active-filter" label="Account status" onChange={(event) => { setActive(event.target.value); setPage(1) }} options={ [['', 'All accounts'], ['active', 'Active'], ['inactive', 'Inactive']] } value={active} />
    </div>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">{error}</div>}
    {loading ? <Spinner label="Loading user accounts" /> : (users?.items.length ?? 0) === 0 ? <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center"><UserRound className="mx-auto text-slate-400" size={28} /><h2 className="mt-3 font-semibold text-slate-900">No users found</h2><p className="mt-1 text-sm text-slate-500">Adjust the filters or create an account.</p></div> :
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="hidden overflow-x-auto md:block"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">User</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Joined</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{users.items.map((person) => <tr className="hover:bg-slate-50/70" key={person.id}><td className="px-5 py-4"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-50 text-xs font-bold text-indigo-700">{person.full_name.split(/\s+/).slice(0, 2).map((item) => item[0]).join('').toUpperCase()}</span><div><p className="font-semibold text-slate-900">{person.full_name}{person.id === currentUser.id && <span className="ml-2 text-xs font-normal text-slate-400">You</span>}</p><p className="text-xs text-slate-500">{person.email}</p></div></div></td><td className="px-4 py-4"><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize text-slate-700">{person.role}</span></td><td className="px-4 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${person.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{person.is_active ? 'Active' : 'Inactive'}</span></td><td className="px-4 py-4 text-slate-500">{new Date(person.created_at).toLocaleDateString()}</td><td className="px-4 py-4"><div className="flex justify-end gap-1"><button aria-label={`View ${person.full_name}`} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-indigo-700" onClick={() => openView(person)} type="button"><Eye size={16} /></button><button aria-label={`Edit ${person.full_name}`} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-indigo-700" onClick={() => openEdit(person)} type="button"><Pencil size={16} /></button><button className="rounded-lg px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50" disabled={person.id === currentUser.id} onClick={() => toggleActive(person)} type="button">{person.is_active ? 'Deactivate' : 'Activate'}</button><button aria-label={`Delete ${person.full_name}`} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-700 disabled:opacity-40" disabled={person.id === currentUser.id} onClick={() => setRemoveTarget(person)} type="button"><Trash2 size={16} /></button></div></td></tr>)}</tbody></table></div>
        <div className="divide-y divide-slate-100 md:hidden">{users.items.map((person) => <article className="p-4" key={person.id}><div className="flex items-start justify-between"><div><p className="font-semibold text-slate-900">{person.full_name}</p><p className="text-xs text-slate-500">{person.email}</p></div><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${person.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{person.is_active ? 'Active' : 'Inactive'}</span></div><div className="mt-3 flex items-center justify-between gap-2"><span className="text-xs capitalize text-slate-500">{person.role} · joined {new Date(person.created_at).toLocaleDateString()}</span><div className="flex gap-1"><button aria-label={`View ${person.full_name}`} className="rounded p-2 text-slate-500" onClick={() => openView(person)} type="button"><Eye size={16} /></button><button aria-label={`Edit ${person.full_name}`} className="rounded p-2 text-indigo-600" onClick={() => openEdit(person)} type="button"><Pencil size={16} /></button><button className="rounded px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50" disabled={person.id === currentUser.id} onClick={() => toggleActive(person)} type="button">{person.is_active ? 'Deactivate' : 'Activate'}</button><button aria-label={`Delete ${person.full_name}`} className="rounded p-2 text-rose-600 disabled:opacity-40" disabled={person.id === currentUser.id} onClick={() => setRemoveTarget(person)} type="button"><Trash2 size={16} /></button></div></div></article>)}</div>
        <footer className="flex items-center justify-between border-t border-slate-100 px-4 py-3"><p className="text-xs text-slate-500">{users.total} accounts · Page {page} of {pageCount}</p><div className="flex gap-2"><Button disabled={page <= 1} onClick={() => setPage((value) => value - 1)} variant="secondary"><ChevronLeft size={16} /> Previous</Button><Button disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)} variant="secondary">Next <ChevronRight size={16} /></Button></div></footer>
      </div>}
    {modal?.mode === 'view' && <Modal onClose={() => setModal(null)} title="User account"><div className="space-y-4"><div className="flex items-center gap-3"><span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-700"><UserRoundCheck size={22} /></span><div><p className="font-semibold text-slate-900">{modal.user.full_name}</p><p className="text-sm text-slate-500">{modal.user.email}</p></div></div><div className="grid grid-cols-2 gap-3 text-sm"><p className="rounded-lg bg-slate-50 p-3"><span className="block text-xs text-slate-500">Role</span><span className="mt-1 block font-medium capitalize">{modal.user.role}</span></p><p className="rounded-lg bg-slate-50 p-3"><span className="block text-xs text-slate-500">Status</span><span className="mt-1 block font-medium">{modal.user.is_active ? 'Active' : 'Inactive'}</span></p><p className="col-span-2 rounded-lg bg-slate-50 p-3"><span className="block text-xs text-slate-500">Member since</span><span className="mt-1 block font-medium">{new Date(modal.user.created_at).toLocaleString()}</span></p></div></div></Modal>}
    {(modal?.mode === 'create' || modal?.mode === 'edit') && <Modal onClose={() => setModal(null)} title={modal.mode === 'create' ? 'Create user' : 'Edit user'}><form className="space-y-4" onSubmit={submit}>
      <Field id="user-full-name" label="Full name"><input autoComplete="name" className="field-input" id="user-full-name" maxLength={120} minLength={2} onChange={(event) => update('full_name', event.target.value)} required value={form.full_name} /></Field>
      <Field id="user-email" label="Email"><input autoComplete="email" className="field-input" id="user-email" onChange={(event) => update('email', event.target.value)} required type="email" value={form.email} /></Field>
      {modal.mode === 'create' && <Field id="user-password" label="Temporary password"><input autoComplete="new-password" className="field-input" id="user-password" minLength={12} onChange={(event) => update('password', event.target.value)} required type="password" value={form.password} /><span className="block text-xs font-normal text-slate-500">At least 12 characters; share this securely with the user.</span></Field>}
      <SelectField id="user-role" label="Role" onChange={(event) => update('role', event.target.value)} options={ [['user', 'User'], ['admin', 'Administrator']] } value={form.role} />
      <label className="flex items-center gap-2 text-sm text-slate-700"><input checked={form.is_active} onChange={(event) => update('is_active', event.target.checked)} type="checkbox" /> Account active</label>
      <div className="flex justify-end gap-2 pt-2"><Button onClick={() => setModal(null)} type="button" variant="secondary">Cancel</Button><Button disabled={saving}>{saving ? 'Saving…' : modal.mode === 'create' ? 'Create account' : 'Save changes'}</Button></div>
    </form></Modal>}
    {removeTarget && <Modal onClose={() => setRemoveTarget(null)} title="Delete user account"><p className="text-sm leading-6 text-slate-600">Delete <strong>{removeTarget.full_name}</strong> and their tasks, conversations, uploaded-file records, and private files? This cannot be undone.</p><div className="mt-5 flex justify-end gap-2"><Button onClick={() => setRemoveTarget(null)} variant="secondary">Cancel</Button><Button disabled={saving} onClick={deleteUser} variant="danger">{saving ? 'Deleting…' : 'Delete account'}</Button></div></Modal>}
  </div>
}

export default AdminUsersPage
