import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

function RoleRoute({ role, children }) {
  const { user } = useAuth()
  if (user?.role !== role) {
    return <Navigate to="/unauthorized" replace />
  }
  return children
}

export default RoleRoute
