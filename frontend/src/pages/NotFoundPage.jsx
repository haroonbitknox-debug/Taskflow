import { Link } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'

function NotFoundPage() {
  return (
    <AuthLayout
      title="Page not found"
      description="That TaskFlow page does not exist."
      footer={
        <Link className="font-medium text-indigo-700 hover:text-indigo-900" to="/">
          Return home
        </Link>
      }
    >
      <Link className="font-medium text-indigo-700 hover:text-indigo-900" to="/">
        Go to TaskFlow home
      </Link>
    </AuthLayout>
  )
}

export default NotFoundPage
