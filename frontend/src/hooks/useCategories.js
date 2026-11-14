import { useCallback, useMemo } from 'react'
import { api } from '../api'
import useAsync from './useAsync'

const asList = (data) => (Array.isArray(data) ? data : (data?.results ?? []))

// Active categories (global defaults + the user's own) with an id → category lookup.
export default function useCategories() {
  const load = useCallback(async () => asList(await api('/categories/')), [])
  const { data, loading, error, reload } = useAsync(load)

  return useMemo(() => {
    const categories = (data ?? []).filter((c) => c.is_active).sort((a, b) => a.name.localeCompare(b.name))
    return { categories, byId: new Map(categories.map((c) => [c.id, c])), loading, error, reload }
  }, [data, loading, error, reload])
}

