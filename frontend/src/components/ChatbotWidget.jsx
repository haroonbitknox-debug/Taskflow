import { useEffect, useRef, useState } from 'react'
import { Bot, Check, ChevronDown, FileSpreadsheet, LoaderCircle, MessageCircle, Send, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import { chatApi } from '../services/api.js'

const SUGGESTIONS = [
  'Find my pending tasks.',
  'Show overdue tasks.',
  'Find task ID 788.',
  "Change task 25's priority to high.",
  'Search my Excel files for invoice 1045.',
  'Create a task to submit my report tomorrow.',
]

function ChatbotWidget() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [actingOn, setActingOn] = useState('')
  const [error, setError] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, sending, open])

  async function sendMessage(message = draft) {
    const content = message.trim()
    if (!content || sending) return
    setSending(true)
    setError('')
    setDraft('')
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', content }])
    try {
      const { data } = await chatApi.send({ conversation_id: conversationId, message: content })
      setConversationId(data.conversation_id)
      setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'assistant', ...data }])
    } catch (reason) {
      setError(reason.response?.data?.detail || 'The assistant could not reach TaskFlow. Please try again.')
      setMessages((current) => [...current, {
        id: crypto.randomUUID(),
        role: 'assistant',
        assistant_message: reason.response?.data?.detail || 'I could not process that request. Please try again.',
      }])
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  async function confirmAction(message) {
    const challenge = message.pending_action?.challenge
    if (!challenge || actingOn) return
    setActingOn(challenge)
    setError('')
    try {
      const { data } = await chatApi.confirm(challenge)
      setMessages((current) => [
        ...current.map((item) => item.id === message.id ? { ...item, pending_action: null } : item),
        { id: crypto.randomUUID(), role: 'assistant', ...data },
      ])
    } catch (reason) {
      setError(reason.response?.data?.detail || 'Confirmation failed. Review the task and try again.')
    } finally {
      setActingOn('')
    }
  }

  async function cancelAction(message) {
    const challenge = message.pending_action?.challenge
    if (!challenge || actingOn) return
    setActingOn(challenge)
    try {
      await chatApi.cancel(challenge)
      setMessages((current) => [
        ...current.map((item) => item.id === message.id ? { ...item, pending_action: null } : item),
        { id: crypto.randomUUID(), role: 'assistant', assistant_message: 'I cancelled that pending action.' },
      ])
    } catch (reason) {
      setError(reason.response?.data?.detail || 'Could not cancel that action.')
    } finally {
      setActingOn('')
    }
  }

  function fileSearchUrl(file, query) {
    const params = new URLSearchParams({ search: query || file.original_filename, file_id: String(file.file_id) })
    return `/files?${params.toString()}`
  }

  return <div className="fixed bottom-4 right-4 z-40 sm:bottom-5 sm:right-5">
    {open && <section aria-label="TaskFlow assistant" className="mb-3 flex h-[min(70vh,640px)] w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl sm:w-[min(420px,calc(100vw-3rem))]">
      <header className="flex items-center gap-3 bg-indigo-700 px-4 py-3.5 text-white">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15"><Bot size={20} /></span>
        <div className="min-w-0 flex-1"><h2 className="text-sm font-semibold">TaskFlow assistant</h2><p className="text-xs text-indigo-100">Search and manage your workspace</p></div>
        <button aria-label="Minimize chat" className="rounded-lg p-2 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-white" onClick={() => setOpen(false)} type="button"><ChevronDown size={19} /></button>
      </header>

      <div aria-live="polite" className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-3.5 sm:p-4">
        {messages.length === 0 && <div className="space-y-3">
          <div className="max-w-[90%] rounded-2xl rounded-tl-sm bg-white px-3.5 py-3 text-sm leading-5 text-slate-700 shadow-sm">Hi {user?.full_name?.split(' ')[0] ?? 'there'}! I can search your tasks and private spreadsheets, or prepare a task change for you to review.</div>
          <div className="space-y-2"><p className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Try asking</p><div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((prompt) => <button className="rounded-full border border-indigo-100 bg-white px-3 py-1.5 text-left text-xs text-indigo-700 transition hover:border-indigo-300 hover:bg-indigo-50 focus-visible:outline-2 focus-visible:outline-indigo-600 disabled:opacity-60" disabled={sending} key={prompt} onClick={() => sendMessage(prompt)} type="button">{prompt}</button>)}
          </div></div>
        </div>}

        {messages.map((message) => <article className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`} key={message.id}>
          <div className={`max-w-[92%] space-y-2 ${message.role === 'user' ? 'rounded-2xl rounded-br-sm bg-indigo-600 px-3.5 py-2.5 text-white' : 'w-full'}`}>
            {message.role === 'assistant' && <div className="flex items-start gap-2">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700"><Bot size={15} /></span>
              <p className="rounded-2xl rounded-tl-sm bg-white px-3.5 py-2.5 text-sm leading-5 text-slate-700 shadow-sm">{message.assistant_message}</p>
            </div>}
            {message.role === 'user' && <p className="whitespace-pre-wrap text-sm leading-5">{message.content}</p>}

            {message.tasks?.length > 0 && <div className="ml-9 space-y-2">
              {message.tasks.map((task) => <Link className="block rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50/50" key={task.id} to={user?.role === 'admin' ? `/admin/tasks/${task.id}` : `/tasks/${task.id}`}>
                <span className="block font-semibold text-slate-900">#{task.id} · {task.title}</span>
                <span className="mt-1 block text-xs capitalize text-slate-500">{task.status.replace('_', ' ')} · {task.priority} priority{task.due_date ? ` · due ${new Date(task.due_date).toLocaleDateString()}` : ''}{task.owner_name ? ` · ${task.owner_name}` : ''}</span>
              </Link>)}
            </div>}

            {message.files?.length > 0 && <div className="ml-9 space-y-2">
              {message.files.map((file, index) => <Link className="block rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50/50" key={`${file.file_id}-${file.row_number}-${index}`} to={fileSearchUrl(file, message.search_query)}>
                <span className="flex items-center gap-2 font-semibold text-slate-900"><FileSpreadsheet className="shrink-0 text-emerald-600" size={15} />{file.original_filename}</span>
                <span className="mt-1 block text-xs text-slate-500">{file.worksheet_name || 'Filename match'}{file.row_number ? ` · Row ${file.row_number}` : ''}{file.column_name ? ` · ${file.column_name}` : ''}</span>
                <span className="mt-1 block break-words text-xs text-slate-600">{file.excerpt}</span>
              </Link>)}
            </div>}

            {message.pending_action && <div className="ml-9 rounded-xl border border-amber-200 bg-amber-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Review before confirming</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{message.pending_action.preview}</p>
              {message.pending_action.task && <div className="mt-2 rounded-lg bg-white/80 p-2 text-xs text-slate-700">
                <p><strong>Task #{message.pending_action.task.id}:</strong> {message.pending_action.task.title}</p>
                {message.pending_action.owner_name && <p><strong>Owner:</strong> {message.pending_action.owner_name}</p>}
                <p><strong>Current:</strong> {message.pending_action.task.status.replace('_', ' ')} · {message.pending_action.task.priority}</p>
                {Object.entries(message.pending_action.changes ?? {}).map(([key, value]) => <p className="capitalize" key={key}><strong>{key.replace('_', ' ')}:</strong> {String(value)}</p>)}
                {message.pending_action.task && <Link className="mt-1 inline-block text-indigo-700 underline" to={user?.role === 'admin' ? `/admin/tasks/${message.pending_action.task.id}` : `/tasks/${message.pending_action.task.id}`}>Open task details</Link>}
              </div>}
              {!message.pending_action.task && Object.entries(message.pending_action.changes ?? {}).length > 0 && <div className="mt-2 rounded-lg bg-white/80 p-2 text-xs text-slate-700">
                {Object.entries(message.pending_action.changes).map(([key, value]) => <p className="capitalize" key={key}><strong>{key.replace('_', ' ')}:</strong> {String(value)}</p>)}
              </div>}
              <p className="mt-2 text-[11px] text-amber-800">This confirmation expires {new Date(message.pending_action.expires_at).toLocaleTimeString()}.</p>
              <div className="mt-3 flex gap-2">
                <button className="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50" disabled={Boolean(actingOn)} onClick={() => confirmAction(message)} type="button"><Check size={14} />{actingOn === message.pending_action.challenge ? 'Working…' : 'Confirm'}</button>
                <button className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50" disabled={Boolean(actingOn)} onClick={() => cancelAction(message)} type="button"><X size={14} />Cancel</button>
              </div>
            </div>}
          </div>
        </article>)}
        {sending && <div className="flex items-center gap-2 pl-1 text-sm text-slate-500" role="status"><LoaderCircle className="animate-spin" size={16} />Checking your TaskFlow workspace…</div>}
        {error && <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800" role="alert">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <form className="border-t border-slate-200 bg-white p-3" onSubmit={(event) => { event.preventDefault(); sendMessage() }}>
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            aria-label="Message the TaskFlow assistant"
            className="max-h-28 min-h-11 flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            disabled={sending}
            maxLength={2000}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage() } }}
            placeholder="Ask about tasks or files…"
            rows={1}
            value={draft}
          />
          <button aria-label="Send message" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50" disabled={sending || !draft.trim()} type="submit"><Send size={17} /></button>
        </div>
        <p className="mt-1.5 px-1 text-[10px] text-slate-400">Task changes are never made until you review and confirm.</p>
      </form>
    </section>}
    <button
      aria-expanded={open}
      aria-label={open ? 'Close TaskFlow assistant' : 'Open TaskFlow assistant'}
      className="ml-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg shadow-indigo-600/25 transition hover:scale-105 hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
      onClick={() => setOpen((current) => !current)}
      type="button"
    >{open ? <X size={20} /> : <MessageCircle size={21} />}</button>
  </div>
}

export default ChatbotWidget
