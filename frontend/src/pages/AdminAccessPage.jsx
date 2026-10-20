import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import FormError from '../components/FormError.jsx'
import PageLayout from '../components/PageLayout.jsx'
import api from '../services/api.js'

function AdminAccessPage() {
  const [error, setError] = useState('')
  const [verified, setVerified] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/users/admin/access')
      .then(() => setVerified(true))
      .catch((requestError) => {
        if (requestError.response?.status === 403) {
          navigate('/unauthorized', { replace: true })
        } else {
          setError('Could not verify administrator access. Please try again.')
        }
      })
  }, [navigate])

  return (
    <PageLayout title="Administrator access">
      <div className="rounded-2xl border border-slate-200 bg-white p-7">
        <FormError>{error}</FormError>
        {verified
          ? 'Administrator access has been verified by the API. Administration features are outside this phase.'
          : 'Verifying administrator access…'}
      </div>
    </PageLayout>
  )
}

export default AdminAccessPage
