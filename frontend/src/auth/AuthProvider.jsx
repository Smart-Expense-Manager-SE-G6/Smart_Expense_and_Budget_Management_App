import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { AuthContext } from './context'

export default function AuthProvider({ children }) {
  // undefined = still checking the session, null = signed out
  const [user, setUser] = useState(undefined)

  useEffect(() => {
    let cancelled = false
    api('/auth/csrf/')
      .then(() => api('/me/'))
      .then((me) => !cancelled && setUser(me))
      .catch(() => !cancelled && setUser(null))
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email, password) => {
    setUser(await api('/auth/login/', { method: 'POST', body: { email, password } }))
  }, [])

  const register = useCallback(async (fields) => {
    setUser(await api('/auth/register/', { method: 'POST', body: fields }))
  }, [])

  const logout = useCallback(async () => {
    await api('/auth/logout/', { method: 'POST' })
    setUser(null)
  }, [])

  const updateProfile = useCallback(async (fields) => {
    setUser(await api('/me/', { method: 'PATCH', body: fields }))
  }, [])

  const value = useMemo(
    () => ({ user, login, register, logout, updateProfile }),
    [user, login, register, logout, updateProfile],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
