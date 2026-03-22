import { useQuery } from '@tanstack/react-query'
import type { GameSummary } from '../types/game'

interface GameListResponse {
  data: GameSummary[]
}

export function useGameList() {
  return useQuery<GameSummary[]>({
    queryKey: ['gameList'],
    queryFn: async () => {
      const res = await fetch('/game')
      if (!res.ok) throw new Error('FETCH_ERROR')
      const json: GameListResponse = await res.json()
      return json.data
    },
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  })
}
