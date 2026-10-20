import { Link } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'

function UnauthorizedPage() {
  return (
    <AuthLayout
      title="Access denied"
      description="Your account does not have permission to open this page."
      footer={
        <Link className="font-medium text-indigo-700 hover:text-indigo-900" to="/app">
          Return to your workspace
        </Link>
      }
    >
      <Link
        className="inline-flex rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
        to="/app"
      >
        Go to workspace
      </Link>
    </AuthLayout>
  )
}

export default UnauthorizedPage
