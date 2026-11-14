import { useCallback, useMemo } from 'react'
import { api } from '../api'
import { toISODate, toNumber } from '../lib/format'
import useAsync from './useAsync'

const asList = (data) => (Array.isArray(data) ? data : (data?.results ?? []))
const MAX_BUDGETS = 60

// Budgets enriched with live utilisation (FR11): { ...budget, util: { spent, limit, remaining, percent } }.
export default function useBudgets() {
  const load = useCallback(async () => {
    const budgets = asList(await api('/budgets/')).slice(0, MAX_BUDGETS)
    const utilisations = await Promise.all(
      budgets.map((b) => api(`/budgets/${b.id}/utilization/`).catch(() => null)),
    )
    return budgets.map((budget, i) => {
      const u = utilisations[i]
      const limit = toNumber(u?.budget_limit ?? budget.limit_amount)
      const spent = toNumber(u?.amount_spent)
      return {
        ...budget,
        util: {
          spent,
          limit,
          remaining: toNumber(u?.remaining_amount ?? limit - spent),
          percent: u ? toNumber(u.percentage_used) : 0,
        },
      }
    })
  }, [])

  const { data, loading, error, reload } = useAsync(load)

  return useMemo(() => {
    const today = toISODate(new Date())
    const all = [...(data ?? [])].sort((a, b) => b.start_date.localeCompare(a.start_date))
    const isActive = (b) => b.start_date <= today && b.end_date >= today
    return {
      all,
      active: all.filter(isActive),
      past: all.filter((b) => !isActive(b)),
      loading,
      error,
      reload,
    }
  }, [data, loading, error, reload])
}

