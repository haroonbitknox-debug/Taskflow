import { lazy, Suspense } from 'react'
import { LoaderCircle } from 'lucide-react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './hooks/useAuth.js'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import UnauthorizedPage from './pages/UnauthorizedPage.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import RoleRoute from './components/RoleRoute.jsx'
import DashboardLayout from './components/DashboardLayout.jsx'
const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage.jsx'))
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage.jsx'))
const TaskListPage = lazy(() => import('./pages/TaskListPage.jsx'))
const TaskFormPage = lazy(() => import('./pages/TaskFormPage.jsx'))
const TaskDetailPage = lazy(() => import('./pages/TaskDetailPage.jsx'))
const FilesPage = lazy(() => import('./pages/FilesPage.jsx'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage.jsx'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage.jsx'))

function App() {
  const { user } = useAuth()

  return (
    <Suspense fallback={<div className="flex min-h-64 items-center justify-center text-indigo-600"><LoaderCircle aria-label="Loading page" className="animate-spin" size={26} /></div>}>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/login"
        element={user ? <Navigate to="/app" replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={user ? <Navigate to="/app" replace /> : <RegisterPage />}
      />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/app" element={user?.role === 'admin' ? <Navigate to="/admin" replace /> : <DashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/files" element={<FilesPage />} />
          <Route path="/tasks" element={<TaskListPage />} />
          <Route path="/tasks/new" element={<TaskFormPage />} />
          <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
          <Route path="/tasks/:taskId/edit" element={<TaskFormPage />} />
          <Route path="/admin" element={<RoleRoute role="admin"><AdminDashboardPage /></RoleRoute>} />
          <Route path="/admin/users" element={<RoleRoute role="admin"><AdminUsersPage /></RoleRoute>} />
          <Route path="/admin/tasks" element={<RoleRoute role="admin"><TaskListPage /></RoleRoute>} />
          <Route path="/admin/tasks/new" element={<RoleRoute role="admin"><TaskFormPage /></RoleRoute>} />
          <Route path="/admin/tasks/:taskId" element={<RoleRoute role="admin"><TaskDetailPage /></RoleRoute>} />
          <Route path="/admin/tasks/:taskId/edit" element={<RoleRoute role="admin"><TaskFormPage /></RoleRoute>} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
    </Suspense>
  )
}

export default App
