import { useCallback, useEffect, useMemo, useState } from 'react'
import AuthContext from './auth-context.js'
import { authApi } from '../services/api.js'
import { getApiErrorMessage } from '../utils/auth-errors.js'

async function ensureCsrfToken() {
  await authApi.csrf()
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    await ensureCsrfToken()
    try {
      const response = await authApi.me()
      setUser(response.data)
      return response.data
    } catch (error) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        return null
      }
      throw error
    }
  }, [])

  useEffect(() => {
    let mounted = true
    // Initial session hydration is an asynchronous server-state synchronization.
    // oxlint-disable-next-line react/set-state-in-effect
    refreshUser()
      .catch(() => {
        return null
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
        }
      })

    const clearAuthentication = () => setUser(null)
    window.addEventListener('taskflow:unauthorized', clearAuthentication)
    return () => {
      mounted = false
      window.removeEventListener('taskflow:unauthorized', clearAuthentication)
    }
  }, [refreshUser])

  const login = useCallback(async (credentials) => {
    await ensureCsrfToken()
    const response = await authApi.login(credentials)
    setUser(response.data.user)
    return response.data.user
  }, [])

  const register = useCallback(async (details) => {
    await ensureCsrfToken()
    const response = await authApi.register(details)
    setUser(response.data.user)
    return response.data.user
  }, [])

  const logout = useCallback(async () => {
    await ensureCsrfToken()
    await authApi.logout()
    setUser(null)
  }, [])

  const changePassword = useCallback(async (passwords) => {
    await ensureCsrfToken()
    await authApi.changePassword(passwords)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      register,
      logout,
      changePassword,
      refreshUser,
      getApiErrorMessage,
    }),
    [user, loading, login, register, logout, changePassword, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
