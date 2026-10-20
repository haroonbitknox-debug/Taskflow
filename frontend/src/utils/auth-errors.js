export function getApiErrorMessage(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(' ')
  }
  return 'Something went wrong. Please try again.'
}
