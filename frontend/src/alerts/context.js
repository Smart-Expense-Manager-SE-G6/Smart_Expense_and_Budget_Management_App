import { createContext, useContext } from 'react'

export const AlertsContext = createContext(null)

export function useAlerts() {
  const value = useContext(AlertsContext)
  if (!value) throw new Error('useAlerts must be used inside <AlertsProvider>')
  return value
}

