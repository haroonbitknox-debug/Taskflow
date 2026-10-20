function FormError({ children }) {
  if (!children) {
    return null
  }
  return (
    <p
      className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
      role="alert"
    >
      {children}
    </p>
  )
}

export default FormError
