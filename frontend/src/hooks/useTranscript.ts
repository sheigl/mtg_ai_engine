import { useQuery } from '@tanstack/react-query'
import { useRef, useMemo } from 'react'
import type { TranscriptEntry } from '../types/game'

export function useTranscript(gameId: string | undefined) {
  const allEntriesRef = useRef<TranscriptEntry[]>([])
  const lastSeqRef = useRef(0)

  const query = useQuery<TranscriptEntry[]>({
    queryKey: ['transcript', gameId],
    queryFn: async () => {
      const res = await fetch(`/export/${gameId}/transcript`)
      if (!res.ok) throw new Error('FETCH_ERROR')
      const json: TranscriptEntry[] = await res.json()
      return json
    },
    enabled: !!gameId,
    refetchInterval: 2000,
    refetchIntervalInBackground: false,
  })

  const entries = useMemo(() => {
    if (!query.data) return allEntriesRef.current

    const newEntries = query.data.filter(e => e.seq > lastSeqRef.current)
    if (newEntries.length > 0) {
      allEntriesRef.current = [...allEntriesRef.current, ...newEntries]
      lastSeqRef.current = Math.max(...newEntries.map(e => e.seq))
    }

    return allEntriesRef.current
  }, [query.data])

  return { entries, isLoading: query.isLoading, isError: query.isError }
}
