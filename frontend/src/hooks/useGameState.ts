import { useQuery } from '@tanstack/react-query'
import type { GameState } from '../types/game'

interface GameStateResponse {
  data: GameState
}

export function useGameState(gameId: string | undefined) {
  return useQuery<GameState>({
    queryKey: ['game', gameId],
    queryFn: async () => {
      const res = await fetch(`/game/${gameId}`)
      if (!res.ok) {
        throw new Error(res.status === 404 ? 'GAME_NOT_FOUND' : 'FETCH_ERROR')
      }
      const json: GameStateResponse = await res.json()
      return json.data
    },
    enabled: !!gameId,
    refetchInterval: 1500,
    refetchIntervalInBackground: false,
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message === 'GAME_NOT_FOUND') return false
      return failureCount < 3
    },
  })
}
