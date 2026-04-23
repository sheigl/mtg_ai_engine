import { useQuery } from '@tanstack/react-query'

export interface MetagameDeck {
  name: string
  format: string
  card_count: number
  commander: string | null
}

interface MetagameDecksResponse {
  data: MetagameDeck[]
}

interface MetagameRefreshResponse {
  data: {
    format: string
    fetched: number
    decks: string[]
  }
}

interface MetagameDeckDetailResponse {
  data: {
    name: string
    format: string
    cards: { name: string; quantity: number }[]
    commander: string | null
  }
}

export function useMetagameDecks(format: string) {
  return useQuery<MetagameDeck[]>({
    queryKey: ['metagameDecks', format],
    queryFn: async () => {
      const res = await fetch(`/deck/metagame?format=${encodeURIComponent(format)}`)
      if (!res.ok) throw new Error('FETCH_ERROR')
      const json: MetagameDecksResponse = await res.json()
      return json.data
    },
    staleTime: 1000 * 60 * 5,
  })
}

export async function refreshMetagameDecks(format: string): Promise<string[]> {
  const res = await fetch(`/deck/metagame/refresh?format=${encodeURIComponent(format)}`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('REFRESH_ERROR')
  const json: MetagameRefreshResponse = await res.json()
  return json.data?.decks ?? []
}

export async function fetchCachedDeck(format: string, name: string): Promise<{ cards: string[]; commander?: string }> {
  const res = await fetch(`/deck/metagame/deck?format=${encodeURIComponent(format)}&name=${encodeURIComponent(name)}`)
  if (!res.ok) throw new Error('DECK_NOT_FOUND')
  const json: MetagameDeckDetailResponse = await res.json()
  return {
    cards: json.data.cards.flatMap(c => Array(c.quantity).fill(c.name)),
    commander: json.data.commander ?? undefined,
  }
}
