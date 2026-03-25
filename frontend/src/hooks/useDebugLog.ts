import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { DebugEntry } from '../types/debug'

/**
 * Returns debug entries for a game.
 *
 * - When enabled=false: returns empty entries immediately.
 * - When enabled=true and game is live: subscribes to SSE stream at
 *   GET /game/{gameId}/debug/stream, upserting entries by entry_id.
 *   On game_over event, switches to a one-time static fetch.
 * - When enabled=true and game is already over (isGameOver=true on mount):
 *   skips SSE and fetches the static log directly.
 */
export function useDebugLog(
  gameId: string | undefined,
  enabled: boolean,
  isGameOver: boolean,
) {
  const [liveEntries, setLiveEntries] = useState<DebugEntry[]>([])
  const [sseDone, setSseDone] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  // Static fetch (for completed games or after SSE closes).
  // Polls every 2s while any entry is still streaming (background observer threads
  // may still be patching after the game ends and SSE closes).
  const staticQuery = useQuery<DebugEntry[]>({
    queryKey: ['debug-log', gameId],
    queryFn: async () => {
      const res = await fetch(`/game/${gameId}/debug`)
      if (!res.ok) throw new Error('FETCH_ERROR')
      const json: { data: { game_id: string; entries: DebugEntry[] } } = await res.json()
      return json.data.entries
    },
    enabled: !!gameId && enabled && (isGameOver || sseDone),
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 2000
      return data.some(e => !e.is_complete) ? 2000 : false
    },
  })

  useEffect(() => {
    if (!enabled || !gameId) {
      // Close any open SSE connection
      esRef.current?.close()
      esRef.current = null
      setLiveEntries([])
      return
    }

    if (isGameOver) {
      // Game already over — static fetch is handled by staticQuery above
      return
    }

    // Open SSE stream for live games
    const es = new EventSource(`/game/${gameId}/debug/stream`)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const entry: DebugEntry = JSON.parse(event.data)
        setLiveEntries(prev => {
          const idx = prev.findIndex(e => e.entry_id === entry.entry_id)
          if (idx === -1) return [...prev, entry]
          // Merge streaming patch: update existing entry
          const next = [...prev]
          next[idx] = { ...next[idx], ...entry }
          return next
        })
      } catch {
        // ignore parse errors
      }
    }

    es.addEventListener('game_over', () => {
      es.close()
      esRef.current = null
      setSseDone(true)
    })

    es.onerror = () => {
      es.close()
      esRef.current = null
      setSseDone(true)
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [enabled, gameId, isGameOver])

  if (!enabled) {
    return { entries: [] as DebugEntry[], isLoading: false, isError: false }
  }

  if (isGameOver || sseDone) {
    const sorted = [...(staticQuery.data ?? [])].sort((a, b) => a.timestamp - b.timestamp)
    return { entries: sorted, isLoading: staticQuery.isLoading, isError: staticQuery.isError }
  }

  // Live SSE entries sorted by timestamp
  const sorted = [...liveEntries].sort((a, b) => a.timestamp - b.timestamp)
  return { entries: sorted, isLoading: false, isError: false }
}
