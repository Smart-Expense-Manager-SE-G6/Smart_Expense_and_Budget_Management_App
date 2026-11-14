import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'se-theme'

function currentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
}

// Light/dark theme persisted in localStorage. index.html applies the stored/system
// theme before first paint; this hook keeps the attribute and storage in sync.
export default function useTheme() {
  const [theme, setThemeState] = useState(currentTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggle = useCallback(() => {
    setThemeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem(STORAGE_KEY, next)
      } catch {
        /* storage unavailable (private mode) - theme still applies for this session */
      }
      return next
    })
  }, [])

  return { theme, toggle }
}

