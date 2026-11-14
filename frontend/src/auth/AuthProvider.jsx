import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, SESSION_EXPIRED_EVENT } from '../api'
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

  // A 401 from any request means the server-side session is gone: sign out locally
  // so the route guards send the user back to the sign-in page.
  useEffect(() => {
    const signOutLocally = () => setUser(null)
    window.addEventListener(SESSION_EXPIRED_EVENT, signOutLocally)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, signOutLocally)
  }, [])

  const login = useCallback(async (email, password) => {
    setUser(await api('/auth/login/', { method: 'POST', body: { email, password } }))
  }, [])

  const register = useCallback(async (fields) => {
    setUser(await api('/auth/register/', { method: 'POST', body: fields }))
  }, [])

  const logout = useCallback(async () => {
    try {
      await api('/auth/logout/', { method: 'POST' })
    } catch (err) {
      // 401: the session had already expired on the server, which is what logout wants anyway.
      if (err.status !== 401) throw err
    } finally {
      setUser(null)
    }
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
