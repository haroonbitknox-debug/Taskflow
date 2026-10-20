import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CloudUpload,
  Download,
  FileSpreadsheet,
  LoaderCircle,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { fileApi } from '../services/api.js'
import { useToast } from '../hooks/useToast.js'
import { Button, EmptyState, Modal, Spinner } from '../components/Ui.jsx'

const PAGE_SIZE = 10
const ACCEPTED_FORMATS = ['.xlsx', '.xls', '.csv']

function formatBytes(size) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function FileStatus({ status }) {
  const styles = {
    ready: 'bg-emerald-50 text-emerald-700',
    processing: 'bg-sky-50 text-sky-700',
    pending: 'bg-amber-50 text-amber-700',
    failed: 'bg-rose-50 text-rose-700',
  }
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${styles[status] ?? 'bg-slate-100 text-slate-600'}`}>
    {status === 'ready' ? <CheckCircle2 size={13} /> : status === 'failed' ? <AlertCircle size={13} /> : <LoaderCircle className={status === 'processing' ? 'animate-spin' : ''} size={13} />}
    {status}
  </span>
}

function FilesPage() {
  const [searchParams] = useSearchParams()
  const notify = useToast()
  const pickerRef = useRef(null)
  const [fileData, setFileData] = useState(null)
  const [page, setPage] = useState(1)
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState(() => searchParams.get('search') ?? '')
  const [debouncedSearch, setDebouncedSearch] = useState(() => searchParams.get('search') ?? '')
  const [searchRefresh, setSearchRefresh] = useState(0)
  const [searchData, setSearchData] = useState(null)
  const [searching, setSearching] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [retrying, setRetrying] = useState(null)

  const linkedSearch = searchParams.get('search') ?? ''
  useEffect(() => {
    if (linkedSearch && linkedSearch !== search) {
      // oxlint-disable-next-line react/set-state-in-effect
      setSearch(linkedSearch)
    }
  }, [linkedSearch, search])

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [search])

  useEffect(() => {
    const controller = new AbortController()
    // oxlint-disable-next-line react/set-state-in-effect
    setLoading(true)
    // oxlint-disable-next-line react/set-state-in-effect
    setError('')
    fileApi.list({ page, page_size: PAGE_SIZE }, { signal: controller.signal })
      .then(({ data }) => setFileData(data))
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.response?.data?.detail || 'Unable to load your files. Please retry.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [page, refresh])

  useEffect(() => {
    if (!debouncedSearch) {
      // oxlint-disable-next-line react/set-state-in-effect
      setSearchData(null)
      // oxlint-disable-next-line react/set-state-in-effect
      setSearching(false)
      return undefined
    }
    const controller = new AbortController()
    // oxlint-disable-next-line react/set-state-in-effect
    setSearching(true)
    fileApi.search({
      q: debouncedSearch,
      page: 1,
      page_size: 20,
      file_id: searchParams.get('file_id') || undefined,
    }, { signal: controller.signal })
      .then(({ data }) => setSearchData(data))
      .catch((reason) => {
        if (!controller.signal.aborted) notify(reason.response?.data?.detail || 'Search failed. Please retry.', 'error')
      })
      .finally(() => { if (!controller.signal.aborted) setSearching(false) })
    return () => controller.abort()
  }, [debouncedSearch, notify, searchParams, searchRefresh])

  const refreshFiles = useCallback(() => setRefresh((value) => value + 1), [])

  async function uploadFiles(fileList) {
    const selected = Array.from(fileList ?? [])
    if (!selected.length || uploading) return
    const invalid = selected.find((file) => !ACCEPTED_FORMATS.includes(`.${file.name.split('.').pop()?.toLowerCase()}`))
    if (invalid) {
      notify(`${invalid.name}: choose an XLSX, XLS, or CSV file.`, 'error')
      return
    }
    setUploading(true)
    setUploadProgress(0)
    let succeeded = 0
    for (const file of selected) {
      try {
        const { data } = await fileApi.upload(file, (event) => {
          if (event.total) setUploadProgress(Math.round((event.loaded / event.total) * 100))
        })
        succeeded += 1
        notify(data.processing_status === 'ready' ? `${file.name} uploaded and indexed.` : `${file.name} uploaded; indexing needs a retry.`, data.processing_status === 'ready' ? 'success' : 'info')
      } catch (reason) {
        notify(reason.response?.data?.detail || `Could not upload ${file.name}.`, 'error')
      }
    }
    setUploading(false)
    setUploadProgress(0)
    if (succeeded) {
      refreshFiles()
      setSearchRefresh((value) => value + 1)
    }
    if (pickerRef.current) pickerRef.current.value = ''
  }

  async function downloadFile(file) {
    try {
      const { data } = await fileApi.download(file.id)
      const url = URL.createObjectURL(data)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = file.original_filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (reason) {
      notify(reason.response?.data?.detail || 'Could not download this file.', 'error')
    }
  }

  async function deleteFile() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await fileApi.remove(deleteTarget.id)
      notify(`${deleteTarget.original_filename} deleted.`)
      setDeleteTarget(null)
      if ((fileData?.items.length ?? 0) === 1 && page > 1) setPage((current) => current - 1)
      else refreshFiles()
      setSearchRefresh((value) => value + 1)
    } catch (reason) {
      notify(reason.response?.data?.detail || 'Could not delete this file.', 'error')
    } finally {
      setDeleting(false)
    }
  }

  async function retryIndexing(file) {
    setRetrying(file.id)
    try {
      await fileApi.retry(file.id)
      notify(`${file.original_filename} indexed successfully.`)
      refreshFiles()
    } catch (reason) {
      notify(reason.response?.data?.detail || 'Could not retry indexing.', 'error')
    } finally {
      setRetrying(null)
    }
  }

  const files = fileData?.items ?? []
  const pageCount = Math.max(1, Math.ceil((fileData?.total ?? 0) / PAGE_SIZE))
  const hits = searchData?.items ?? []

  return <div className="space-y-6">
    <header>
      <p className="text-sm font-semibold text-indigo-600">Workspace</p>
      <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">Files</h1>
      <p className="mt-2 text-sm text-slate-500">Upload spreadsheets, search their contents, and manage your private files.</p>
    </header>

    <section
      className={`rounded-2xl border-2 border-dashed p-6 text-center transition sm:p-9 ${dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-300 bg-white'}`}
      onDragEnter={(event) => { event.preventDefault(); setDragging(true) }}
      onDragLeave={(event) => { event.preventDefault(); if (event.currentTarget === event.target) setDragging(false) }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => { event.preventDefault(); setDragging(false); uploadFiles(event.dataTransfer.files) }}
    >
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"><CloudUpload size={24} /></div>
      <h2 className="mt-4 font-semibold text-slate-900">Drop files here to upload</h2>
      <p className="mt-1 text-sm text-slate-500">Excel and CSV spreadsheets · Processing limits are server-configured</p>
      <div className="mt-4">
        <Button disabled={uploading} onClick={() => pickerRef.current?.click()}><Upload size={16} /> Choose files</Button>
        <input
          ref={pickerRef}
          accept=".xlsx,.xls,.csv"
          aria-label="Choose spreadsheets to upload"
          className="sr-only"
          multiple
          onChange={(event) => uploadFiles(event.target.files)}
          type="file"
        />
      </div>
      {uploading && <div aria-live="polite" className="mx-auto mt-5 max-w-sm text-left" role="status">
        <div className="mb-1 flex justify-between text-xs text-slate-600"><span>Uploading files</span><span>{uploadProgress}%</span></div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-600 transition-[width]" style={{ width: `${uploadProgress}%` }} /></div>
      </div>}
      <p className="mt-4 text-xs text-slate-400">Supported: {ACCEPTED_FORMATS.join(', ')}. Files are private to your account.</p>
    </section>

    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h2 className="text-lg font-semibold text-slate-900">Search spreadsheet contents</h2><p className="mt-1 text-sm text-slate-500">Find matching filenames, worksheets, and indexed cells.</p></div>
        <label className="relative block w-full sm:max-w-md">
          <span className="sr-only">Search files</span>
          <Search aria-hidden="true" className="absolute left-3 top-3 text-slate-400" size={17} />
          <input className="field-input pl-9 pr-9" onChange={(event) => setSearch(event.target.value)} placeholder="Search file contents…" value={search} />
          {search && <button aria-label="Clear search" className="absolute right-2 top-2 rounded p-1 text-slate-400 hover:bg-slate-100" onClick={() => setSearch('')} type="button"><X size={16} /></button>}
        </label>
      </div>
      {searching && <p className="text-sm text-slate-500" role="status">Searching your indexed files…</p>}
      {debouncedSearch && !searching && searchData && (hits.length === 0
        ? <p className="rounded-xl bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">No matches found for “{debouncedSearch}”.</p>
        : <div className="divide-y divide-slate-100 rounded-xl border border-slate-100">
          {hits.map((hit, index) => <article className="flex flex-wrap items-start justify-between gap-3 p-4" key={`${hit.file_id}-${hit.worksheet_name}-${hit.row_number}-${hit.column_name}-${index}`}>
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-sm font-semibold text-slate-900"><FileSpreadsheet className="shrink-0 text-emerald-600" size={16} />{hit.original_filename}</p>
              <p className="mt-1 text-xs text-slate-500">
                {hit.match_type === 'filename' ? 'Filename match' : `${hit.worksheet_name ?? 'Worksheet'}${hit.row_number ? ` · Row ${hit.row_number}` : ''}${hit.column_name ? ` · ${hit.column_name}` : ''}`}
              </p>
              {hit.match_type !== 'filename' && <p className="mt-2 break-words text-sm text-slate-700">{hit.excerpt}</p>}
            </div>
            <span className="rounded bg-slate-100 px-2 py-1 text-xs uppercase text-slate-600">{hit.extension}</span>
          </article>)}
        </div>
      )}
    </section>

    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-lg font-semibold text-slate-900">Your files</h2><p className="text-sm text-slate-500">{fileData?.total ?? 0} files</p></div>
        <Button className="!min-h-9 !px-3" onClick={refreshFiles} variant="secondary"><RefreshCw size={15} /> Refresh</Button>
      </div>
      {error && <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')} type="button"><X size={16} /></button></div>}
      {loading ? <Spinner label="Loading files" /> : files.length === 0
        ? <EmptyState title="No files yet" description="Upload an XLSX, XLS, or CSV spreadsheet to index and search its contents." />
        : <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-4 py-3 font-semibold">File</th><th className="px-4 py-3 font-semibold">Size</th><th className="px-4 py-3 font-semibold">Uploaded</th><th className="px-4 py-3 font-semibold">Indexing</th><th className="px-4 py-3 text-right font-semibold">Actions</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {files.map((file) => <tr className="hover:bg-slate-50/70" key={file.id}>
                  <td className="px-4 py-3"><div className="flex items-center gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700"><FileSpreadsheet size={18} /></span><div className="min-w-0"><p className="max-w-[300px] truncate font-medium text-slate-900" title={file.original_filename}>{file.original_filename}</p><p className="mt-0.5 text-xs uppercase text-slate-500">{file.extension} · {file.indexed_entry_count} indexed cells</p>{file.processing_error && <p className="mt-1 text-xs text-rose-700">{file.processing_error}</p>}</div></div></td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-600">{formatBytes(file.file_size)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-600">{formatDate(file.created_at)}</td>
                  <td className="px-4 py-3"><FileStatus status={file.processing_status} /></td>
                  <td className="px-4 py-3"><div className="flex justify-end gap-1">
                    {file.processing_status === 'failed' && <button aria-label={`Retry indexing ${file.original_filename}`} className="rounded-lg p-2 text-amber-700 hover:bg-amber-50 disabled:opacity-50" disabled={retrying === file.id} onClick={() => retryIndexing(file)} title="Retry indexing" type="button"><RefreshCw className={retrying === file.id ? 'animate-spin' : ''} size={17} /></button>}
                    <button aria-label={`Download ${file.original_filename}`} className="rounded-lg p-2 text-indigo-700 hover:bg-indigo-50" onClick={() => downloadFile(file)} title="Download" type="button"><Download size={17} /></button>
                    <button aria-label={`Delete ${file.original_filename}`} className="rounded-lg p-2 text-rose-700 hover:bg-rose-50" onClick={() => setDeleteTarget(file)} title="Delete" type="button"><Trash2 size={17} /></button>
                  </div></td>
                </tr>)}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <span>Page {page} of {pageCount}</span>
            <div className="flex gap-2">
              <Button disabled={page <= 1} onClick={() => setPage((current) => current - 1)} variant="secondary"><ChevronLeft size={16} /> Previous</Button>
              <Button disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)} variant="secondary">Next <ChevronRight size={16} /></Button>
            </div>
          </div>
        </div>}
    </section>

    {deleteTarget && <Modal
      footer={<><Button disabled={deleting} onClick={() => setDeleteTarget(null)} variant="secondary">Cancel</Button><Button disabled={deleting} onClick={deleteFile} variant="danger">{deleting ? 'Deleting…' : 'Delete file'}</Button></>}
      onClose={() => { if (!deleting) setDeleteTarget(null) }}
      title="Delete this file?"
    ><p className="text-sm leading-6 text-slate-600">This permanently deletes <strong className="break-all text-slate-900">{deleteTarget.original_filename}</strong> and its indexed spreadsheet content.</p></Modal>}
  </div>
}

export default FilesPage
