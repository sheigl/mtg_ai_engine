import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

interface UseHumanActionResult {
  submitAction: (actionType: string, payload: Record<string, unknown>) => Promise<void>
  isPending: boolean
  lastError: string | null
  clearError: () => void
}

const ENDPOINT_MAP: Record<string, string> = {
  pass: 'pass',
  play_land: 'play-land',
  cast: 'cast',
  activate: 'activate',
  declare_attackers: 'declare-attackers',
  declare_blockers: 'declare-blockers',
  order_blockers: 'order-blockers',
  assign_combat_damage: 'assign-combat-damage',
  mulligan: 'mulligan',
  'activate-loyalty': 'activate-loyalty',
  'cascade-choice': 'cascade-choice',
  choice: 'choice',
  scry_choice: 'choice',
  surveil_choice: 'choice',
  discard: 'discard',
}

export function useHumanAction(gameId: string | undefined): UseHumanActionResult {
  const queryClient = useQueryClient()
  const [isPending, setIsPending] = useState(false)
  const [lastError, setLastError] = useState<string | null>(null)

  const submitAction = useCallback(
    async (actionType: string, payload: Record<string, unknown>) => {
      if (!gameId || isPending) return

      const endpoint = ENDPOINT_MAP[actionType] ?? actionType
      setIsPending(true)
      setLastError(null)

      try {
        const res = await fetch(`/game/${gameId}/${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })

        if (!res.ok) {
          const json = await res.json().catch(() => null)
          const detail = json?.detail
          const msg = Array.isArray(detail)
            ? detail.map((e: Record<string, unknown>) => `${e.loc}: ${e.msg}`).join('; ')
            : typeof detail === 'object' ? (detail?.error ?? JSON.stringify(detail)) : String(detail ?? `Action failed (${res.status})`)
          setLastError(msg)
          return
        }

        // Invalidate caches so board and legal actions refresh immediately
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['game', gameId] }),
          queryClient.invalidateQueries({ queryKey: ['legalActions', gameId] }),
        ])
      } catch {
        setLastError('Could not reach the engine. Is it running?')
      } finally {
        setIsPending(false)
      }
    },
    [gameId, isPending, queryClient],
  )

  const clearError = useCallback(() => setLastError(null), [])

  return { submitAction, isPending, lastError, clearError }
}
