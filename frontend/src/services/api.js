import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
})

function readCsrfCookie() {
  const csrfCookieName = 'taskflow_csrf'
  const cookie = document.cookie
    .split('; ')
    .find((part) => part.startsWith(`${csrfCookieName}=`))

  return cookie ? decodeURIComponent(cookie.slice(csrfCookieName.length + 1)) : null
}

api.interceptors.request.use((config) => {
  if (!['get', 'head', 'options'].includes(config.method?.toLowerCase() ?? 'get')) {
    const csrfToken = readCsrfCookie()
    if (csrfToken) {
      config.headers.set('X-CSRF-Token', csrfToken)
    }
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url ?? ''
    if (
      (error.response?.status === 401 ||
        (error.response?.status === 403 && url === '/auth/me')) &&
      !['/auth/login', '/auth/register', '/auth/csrf'].includes(url)
    ) {
      window.dispatchEvent(new Event('taskflow:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export function getHealth() {
  return api.get('/health')
}

export const authApi = {
  csrf: () => api.get('/auth/csrf'),
  login: (payload) => api.post('/auth/login', payload),
  register: (payload) => api.post('/auth/register', payload),
  requestPasswordReset: (payload) => api.post('/auth/password-reset/request', payload),
  confirmPasswordReset: (payload) => api.post('/auth/password-reset/confirm', payload),
  logout: () => api.post('/auth/logout'),
  changePassword: (payload) => api.post('/auth/change-password', payload),
  me: () => api.get('/auth/me'),
}

export const usersApi = {
  profile: () => api.get('/users/me'),
  updateProfile: (payload) => api.patch('/users/me', payload),
}

export const taskApi = {
  list: (params, config = {}) => api.get('/tasks', { params, ...config }),
  get: (id) => api.get(`/tasks/${id}`),
  create: (payload) => api.post('/tasks', payload),
  update: (id, payload) => api.patch(`/tasks/${id}`, payload),
  remove: (id) => api.delete(`/tasks/${id}`),
  summary: () => api.get('/dashboard/summary'),
  adminList: (params, config = {}) => api.get('/admin/tasks', { params, ...config }),
  adminGet: (id) => api.get(`/admin/tasks/${id}`),
  adminCreate: (payload) => api.post('/admin/tasks', payload),
  adminUpdate: (id, payload) => api.patch(`/admin/tasks/${id}`, payload),
  adminRemove: (id) => api.delete(`/admin/tasks/${id}`),
  adminSummary: () => api.get('/admin/dashboard/summary'),
}

export const adminUserApi = {
  list: (params, config = {}) => api.get('/admin/users', { params, ...config }),
  get: (id) => api.get(`/admin/users/${id}`),
  create: (payload) => api.post('/admin/users', payload),
  update: (id, payload) => api.patch(`/admin/users/${id}`, payload),
  remove: (id) => api.delete(`/admin/users/${id}`),
}

export const fileApi = {
  list: (params, config = {}) => api.get('/files', { params, ...config }),
  search: (params, config = {}) => api.get('/files/search', { params, ...config }),
  upload: (file, onUploadProgress) => {
    const data = new FormData()
    data.append('upload', file)
    return api.post('/files/upload', data, { onUploadProgress })
  },
  download: (id) => api.get(`/files/${id}/download`, { responseType: 'blob' }),
  retry: (id) => api.post(`/files/${id}/retry`, {}),
  remove: (id) => api.delete(`/files/${id}`),
}

export const chatApi = {
  send: (payload) => api.post('/chat/messages', payload),
  history: (conversationId) => api.get(`/chat/conversations/${conversationId}/messages`),
  confirm: (challenge) => api.post(`/chat/actions/${encodeURIComponent(challenge)}/confirm`, {}),
  cancel: (challenge) => api.delete(`/chat/actions/${encodeURIComponent(challenge)}`),
}

export default api
