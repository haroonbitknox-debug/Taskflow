import { useState } from 'react'
import { Bell, CheckSquare, ChevronLeft, ChevronRight, Files, LayoutDashboard, ListTodo, LogOut, Menu, Moon, Shield, Sun, Users, X } from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import { useToast } from '../hooks/useToast.js'
import ChatbotWidget from './ChatbotWidget.jsx'

const navLinkClass = ({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'}`

function DashboardLayout() {
  const { user, logout } = useAuth()
  const notify = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dark, setDark] = useState(() => localStorage.getItem('taskflow-theme') === 'dark')
  const [menuOpen, setMenuOpen] = useState(false)
  const admin = user?.role === 'admin'
  const currentTitle = location.pathname.startsWith('/admin/users') ? 'User management'
    : location.pathname.startsWith('/admin/tasks') ? 'All tasks'
      : location.pathname.startsWith('/admin') ? 'Admin overview'
        : location.pathname.startsWith('/tasks/new') ? 'Create task'
          : location.pathname.includes('/edit') ? 'Edit task'
            : location.pathname.startsWith('/tasks/') ? 'Task details'
              : location.pathname.startsWith('/tasks') ? 'My tasks'
                : location.pathname.startsWith('/files') ? 'Files'
                  : location.pathname.startsWith('/profile') ? 'Settings'
                    : 'Dashboard'
  const initials = user?.full_name?.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() ?? 'TF'

  function toggleTheme() {
    const next = !dark
    setDark(next)
    localStorage.setItem('taskflow-theme', next ? 'dark' : 'light')
    document.documentElement.classList.toggle('dark', next)
  }

  async function handleLogout() {
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      notify('Sign out failed. Please try again.', 'error')
    }
  }

  const sidebar = (
    <div className={`flex h-full flex-col bg-white ${collapsed ? 'w-[4.5rem]' : 'w-64'} transition-[width] duration-200`}>
      <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white"><CheckSquare size={19} /></span>
        {!collapsed && <span className="text-lg font-bold tracking-tight text-slate-900">TaskFlow</span>}
        <button aria-label="Close navigation" className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={() => setMobileOpen(false)} type="button"><X size={18} /></button>
      </div>
      <nav aria-label="Main navigation" className="flex-1 space-y-1 overflow-y-auto p-3">
        <NavLink className={navLinkClass} end onClick={() => setMobileOpen(false)} to={admin ? '/admin' : '/app'} title={collapsed ? 'Dashboard' : undefined}><LayoutDashboard size={18} /><span className={collapsed ? 'sr-only' : ''}>Dashboard</span></NavLink>
        {!admin && <NavLink className={navLinkClass} onClick={() => setMobileOpen(false)} to="/tasks" title={collapsed ? 'My tasks' : undefined}><ListTodo size={18} /><span className={collapsed ? 'sr-only' : ''}>My tasks</span></NavLink>}
        {admin && <>
          <NavLink className={navLinkClass} onClick={() => setMobileOpen(false)} to="/admin/users" title={collapsed ? 'Users' : undefined}><Users size={18} /><span className={collapsed ? 'sr-only' : ''}>Users</span></NavLink>
          <NavLink className={navLinkClass} onClick={() => setMobileOpen(false)} to="/admin/tasks" title={collapsed ? 'All tasks' : undefined}><ListTodo size={18} /><span className={collapsed ? 'sr-only' : ''}>All tasks</span></NavLink>
        </>}
        <NavLink className={navLinkClass} onClick={() => setMobileOpen(false)} to="/files" title={collapsed ? 'Files' : undefined}><Files size={18} /><span className={collapsed ? 'sr-only' : ''}>Files</span></NavLink>
        {admin && <div className="mt-6 flex items-center gap-2 px-3 text-[11px] font-bold uppercase tracking-widest text-slate-400"><Shield size={14} /><span className={collapsed ? 'sr-only' : ''}>Administration</span></div>}
      </nav>
      <button aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} className="hidden items-center justify-center border-t border-slate-100 p-4 text-slate-500 hover:bg-slate-50 lg:flex" onClick={() => setCollapsed(!collapsed)} type="button">{collapsed ? <ChevronRight size={17} /> : <><ChevronLeft size={17} /><span className="ml-2 text-sm">Collapse</span></>}</button>
    </div>
  )

  return (
    <div className={dark ? 'dark' : ''}>
      <div className="min-h-screen bg-slate-50 text-slate-800 transition-colors dark:bg-slate-950 dark:text-slate-100">
        <aside className={`fixed inset-y-0 left-0 z-30 hidden border-r border-slate-200 lg:block ${collapsed ? 'w-[4.5rem]' : 'w-64'}`}>{sidebar}</aside>
        {mobileOpen && <div className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"><aside className="h-full w-72 shadow-xl">{sidebar}</aside></div>}
        <div className={collapsed ? 'lg:pl-[4.5rem]' : 'lg:pl-64'}>
          <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-7">
            <div className="flex min-w-0 items-center gap-3">
              <button aria-label="Open navigation" className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setMobileOpen(true)} type="button"><Menu size={19} /></button>
              <div className="truncate text-sm text-slate-500"><span className="hidden sm:inline">Workspace / </span><span className="font-semibold text-slate-900">{currentTitle}</span></div>
            </div>
            <div className="flex items-center gap-1 sm:gap-3">
              <button aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'} className="rounded-lg p-2.5 text-slate-500 hover:bg-slate-100" onClick={toggleTheme} type="button">{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
              <button aria-label="Reminders" className="relative rounded-lg p-2.5 text-slate-500 hover:bg-slate-100" onClick={() => notify('Reminders will appear here when tasks have upcoming deadlines.', 'info')} type="button"><Bell size={18} /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-indigo-500" /></button>
              <div className="relative">
                <button aria-expanded={menuOpen} aria-haspopup="menu" className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-slate-100" onClick={() => setMenuOpen(!menuOpen)} type="button">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">{initials}</span>
                  <span className="hidden max-w-32 truncate text-sm font-medium text-slate-700 sm:block">{user?.full_name}</span>
                </button>
                {menuOpen && <div className="absolute right-0 top-12 z-30 w-52 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg" role="menu">
                  <NavLink className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => setMenuOpen(false)} role="menuitem" to="/profile">Profile & settings</NavLink>
                  <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-rose-700 hover:bg-rose-50" onClick={handleLogout} role="menuitem" type="button"><LogOut size={15} />Sign out</button>
                </div>}
              </div>
            </div>
          </header>
          <main className="mx-auto max-w-[1440px] px-4 py-7 sm:px-7 lg:px-9">
            <Outlet />
          </main>
          <ChatbotWidget />
        </div>
      </div>
    </div>
  )
}

export default DashboardLayout
